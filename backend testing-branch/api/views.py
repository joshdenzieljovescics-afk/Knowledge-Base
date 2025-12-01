from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from allauth.socialaccount.models import SocialToken, SocialAccount
from .serializers import UserSerializer
import json
import os
import requests
import re
from django.utils import timezone
from datetime import datetime, timedelta
from api.mysql_db import SafexpressMySQLDB
from django.conf import settings
from api.permissions import IsAdminUser

mysql_db = SafexpressMySQLDB(
    host="localhost",
    database="safexpressops_local",
    user="root",
    password="",
)

User = get_user_model()


class UserCreate(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]


class UserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@login_required
def google_login_callback(request):
    user = request.user
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    social_accounts = SocialAccount.objects.filter(user=user)
    print("Social Account for user:", social_accounts)
    social_account = social_accounts.first()

    if not social_account:
        print("No social account for user:", user)
        return redirect(f"{FRONTEND_URL}/login/callback/?error=NoSocialAccount")

    token = SocialToken.objects.filter(
        account=social_account, account__provider="google"
    ).first()

    if token:
        print("Google token found", token.token)
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        return redirect(f"{FRONTEND_URL}/login/callback/?access_token={access_token}")
    else:
        print("No google token found for user", user)
        return redirect(f"{FRONTEND_URL}/login/callback/?error=NoGoogleToken")


@csrf_exempt
def validate_google_token(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            google_access_token = data.get("access_token")
            print(google_access_token)

            if not google_access_token:
                return JsonResponse({"detail": "Access token is missing."}, status=400)
            return JsonResponse({"valid": True})
        except json.JSONDecodeError:
            return JsonResponse({"detail": "Invalid JSON."}, status=400)
    return JsonResponse({"detail": "Method not allowed"}, status=405)


@csrf_exempt
def google_auth_dynamodb(request):
    """Handle Google OAuth authentication"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            auth_code = data.get("code")

            if not auth_code:
                return JsonResponse(
                    {"error": "Authorization code is missing."}, status=400
                )

            print(f"Received auth code: {auth_code[:20]}...")

            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": auth_code,
                "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
                "redirect_uri": "postmessage",
                "grant_type": "authorization_code",
            }

            token_response = requests.post(token_url, data=token_data)
            token_response_data = token_response.json()

            print(f"Token exchange response: {token_response_data}")

            if "error" in token_response_data:
                return JsonResponse(
                    {
                        "error": token_response_data.get(
                            "error_description", token_response_data["error"]
                        )
                    },
                    status=400,
                )

            access_token = token_response_data.get("access_token")

            if not access_token:
                return JsonResponse(
                    {"error": "No access token received from Google"}, status=400
                )

            userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {"Authorization": f"Bearer {access_token}"}
            userinfo_response = requests.get(userinfo_url, headers=headers)
            userinfo = userinfo_response.json()

            print(f"User info: {userinfo}")

            email = userinfo.get("email")
            name = userinfo.get("name", "")
            google_id = userinfo.get("id")
            picture = userinfo.get("picture", "")

            if not email:
                return JsonResponse(
                    {"error": "Email not provided by Google"}, status=400
                )

            print(f"👤 Getting/creating user for: {email}")

            # Try to get existing user by email first
            try:
                user = User.objects.get(email=email)
                print(f"✅ Found existing user: {user.email}")
            except User.DoesNotExist:
                # Create new user with unique username handling
                base_username = email.split("@")[0]
                username = base_username
                counter = 1

                # Keep trying until we find a unique username
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1

                print(f"Creating new user with username: {username}")

                user = User.objects.create(
                    email=email,
                    username=username,
                    first_name=name.split()[0] if name else "",
                    last_name=(
                        " ".join(name.split()[1:])
                        if name and len(name.split()) > 1
                        else ""
                    ),
                )
                print(
                    f"✅ Created new user: {user.email} with username: {user.username}"
                )

            from allauth.socialaccount.models import (
                SocialAccount,
                SocialToken,
                SocialApp,
            )

            social_app, created = SocialApp.objects.get_or_create(
                provider="google",
                defaults={
                    "name": "Google",
                    "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
                    "secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
                },
            )

            social_account, created = SocialAccount.objects.get_or_create(
                user=user,
                provider="google",
                defaults={
                    "uid": google_id,
                    "extra_data": userinfo,
                },
            )

            refresh_token = token_response_data.get("refresh_token", "")
            try:
                social_token = SocialToken.objects.get(
                    account=social_account,
                    app=social_app,
                )
                # Update existing token
                social_token.token = access_token
                social_token.expires_at = timezone.now() + timedelta(
                    seconds=token_response_data.get("expires_in", 3600)
                )
                # Only update refresh_token if we got a new one
                if refresh_token:
                    social_token.token_secret = refresh_token
                social_token.save()
                print(f"✅ Updated existing SocialToken for {user.email}")
            except SocialToken.DoesNotExist:
                # Create new token
                social_token = SocialToken.objects.create(
                    account=social_account,
                    app=social_app,
                    token=access_token,
                    token_secret=refresh_token,
                    expires_at=timezone.now()
                    + timedelta(seconds=token_response_data.get("expires_in", 3600)),
                )
                print(f"✅ Created new SocialToken for {user.email}")

            print(f"✅ Created/updated SocialAccount and SocialToken for {user.email}")
            print(f"   Access token: {access_token[:20]}...")
            print(
                f"   Refresh token: {token_response_data.get('refresh_token', 'None')[:20]}..."
            )

            refresh = RefreshToken.for_user(user)
            access_token_jwt = str(refresh.access_token)

            return JsonResponse(
                {
                    "access": access_token_jwt,
                    "refresh": str(refresh),
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "name": name,
                        "picture": picture,
                    },
                },
                status=200,
            )

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON."}, status=400)
        except Exception as e:
            import traceback

            print(f"Error in google_auth_dynamodb: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse(
                {"error": f"Authentication failed: {str(e)}"}, status=500
            )

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def dynamic_mapping_workflow(request):
    """
    Complete workflow with human-in-the-loop check for existing data
    """
    try:
        file = request.FILES.get("file")
        sheet_id = request.data.get("target_url")
        force_upload = request.data.get("force_upload", "false").lower() == "true"

        if not file:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        if not sheet_id:
            return JsonResponse({"error": "Sheet ID is required"}, status=400)

        sheet_id = sheet_id.strip()
        print(f"🔍 Received Sheet ID: {sheet_id}")

        if len(sheet_id) != 44:
            return JsonResponse(
                {
                    "error": f"Invalid sheet ID format (expected 44 characters, got {len(sheet_id)})"
                },
                status=400,
            )

        # ============================================
        # GET USER CREDENTIALS FIRST
        # ============================================
        from allauth.socialaccount.models import SocialToken, SocialAccount

        social_account = SocialAccount.objects.filter(
            user=request.user, provider="google"
        ).first()

        if not social_account:
            return JsonResponse(
                {
                    "error": "No Google account linked. Please connect your Google account first"
                },
                status=400,
            )

        google_token = SocialToken.objects.filter(account=social_account).first()

        if not google_token:
            return JsonResponse(
                {"error": "No Google token found. Please re-authenticate"},
                status=400,
            )

        user_google_credentials = {
            "access_token": google_token.token or "",
            "refresh_token": google_token.token_secret or "",
            "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
        }

        # ============================================
        # STEP 1: Parse file
        # ============================================
        file_type = "xlsx" if file.name.endswith(".xlsx") else "csv"

        if file_type == "xlsx":
            import base64

            file_content = base64.b64encode(file.read()).decode("utf-8")
        else:
            file_content = file.read().decode("utf-8")

        print(f"Processing file: {file.name} ({file_type})")
        print("Step 1: Parsing file...")

        parse_response = requests.post(
            "http://localhost:8004/execute_task",
            json={
                "tool": "parse_file",
                "inputs": {"file_content": file_content, "file_type": file_type},
            },
        )

        if parse_response.status_code != 200:
            return JsonResponse({"error": "File parsing failed"}, status=500)

        parse_result = parse_response.json()
        if not parse_result.get("success"):
            return JsonResponse(
                {"error": parse_result.get("error", "Parse failed")}, status=500
            )

        columns = parse_result["result"]["columns"]
        full_data = parse_result["result"]["full_data"]

        print(
            f"   ✅ Parsed {len(columns)} columns, {parse_result['result']['row_count']} rows"
        )

        # Extract dates from parsed data
        parsed_data = json.loads(full_data)
        upload_dates = [row.get("Date") for row in parsed_data if row.get("Date")]

        # ============================================
        # STEP 2: Smart column mapping
        # ============================================
        print("Step 2: Smart column mapping...")
        map_response = requests.post(
            "http://localhost:8004/execute_task",
            json={
                "tool": "smart_column_mapping",
                "inputs": {"source_columns": columns, "skip_calculated": True},
            },
        )

        if map_response.status_code != 200:
            return JsonResponse({"error": "Column mapping failed"}, status=500)

        map_result = map_response.json()
        if not map_result.get("success"):
            return JsonResponse(
                {"error": map_result.get("error", "Mapping failed")}, status=500
            )

        mappings = map_result["result"]["mappings"]
        print(f"   ✅ Mapped {map_result['result']['high_confidence_count']} columns")

        # ============================================
        # STEP 3: Check for existing data
        # ============================================

        # Extract mapped columns and pairs FIRST (before any checking)
        mapped_columns = [target_col for target_col in mappings.values() if target_col]

        # Extract mapped column pairs for display
        mapped_pairs = []
        for source_col, target_col in mappings.items():
            if target_col:  # Only show actual mappings
                mapped_pairs.append(f"{source_col} → {target_col}")

        # NOW do the checking
        if not force_upload and upload_dates:
            print(f"Step 3: Checking for existing data...")

            try:
                # ============================================
                # PHASE 1: Quick check - Does sheet have ANY data?
                # ============================================
                print(f"   Phase 1: Quick check if sheet has any data...")
                quick_check = requests.post(
                    "http://localhost:8003/execute_task",
                    json={
                        "tool": "check_sheet_has_data",
                        "inputs": {
                            "sheet_id": sheet_id,
                            "sheet_name": "DATA ENTRY",
                        },
                        "credentials_dict": user_google_credentials,
                    },
                )

                if quick_check.status_code == 200:
                    quick_result = quick_check.json()
                    if quick_result.get("success"):
                        has_any_data = quick_result.get("result", {}).get(
                            "has_data", False
                        )

                        if not has_any_data:
                            # ✅ Sheet is empty, safe to proceed - SHOW MAPPED COLUMNS
                            print(
                                f"   ✅ Sheet is empty (only headers), safe to proceed"
                            )
                            return JsonResponse(
                                {
                                    "requires_confirmation": True,
                                    "confirmation_type": "safe",
                                    "conflict_data": {
                                        "total_conflicts": 0,
                                        "total_safe": len(upload_dates),
                                        "safe_dates": upload_dates[:10],
                                        "mapped_columns": mapped_columns[:10],
                                        "mapped_pairs": mapped_pairs[
                                            :10
                                        ],  # Add mapped pairs
                                    },
                                    "message": (
                                        f"📋 Upload Confirmation\n\n"
                                        f"You are uploading {len(upload_dates)} dates of data.\n"
                                        f"Date range: {upload_dates[0] if upload_dates else ''} to {upload_dates[-1] if upload_dates else ''}\n\n"
                                        f"✅ Sheet is empty - safe to upload.\n\n"
                                        f"Will map {len(mapped_pairs)} columns:\n"
                                        f"{chr(10).join(mapped_pairs[:5])}"
                                        f"{(chr(10) + '... and ' + str(len(mapped_pairs) - 5) + ' more') if len(mapped_pairs) > 5 else ''}\n\n"
                                        f"Proceed with upload?"
                                    ),
                                },
                                status=200,
                            )
                        else:
                            # ⚠️ Sheet has data - check which dates AND columns conflict
                            print(
                                f"   ⚠️ Sheet has operational data, checking conflicts..."
                            )

                            # ============================================
                            # TWO-STEP CONFLICT CHECK:
                            # Step 1: Find which rows have these dates
                            # Step 2: Check specific cells in those rows
                            # ============================================
                            print(f"   Phase 1: Finding rows by date...")
                            find_dates_response = requests.post(
                                "http://localhost:8003/execute_task",
                                json={
                                    "tool": "find_rows_by_dates",
                                    "inputs": {
                                        "sheet_id": sheet_id,
                                        "dates_to_find": upload_dates,
                                        "sheet_name": "DATA ENTRY",
                                    },
                                    "credentials_dict": user_google_credentials,
                                },
                            )

                            if find_dates_response.status_code != 200:
                                print(f"   ⚠️  Could not check dates, proceeding...")
                                # Fallback to original method if this fails
                                check_response = requests.post(
                                    "http://localhost:8003/execute_task",
                                    json={
                                        "tool": "check_dates_and_columns_have_data",
                                        "inputs": {
                                            "sheet_id": sheet_id,
                                            "dates_to_check": upload_dates,
                                            "columns_to_check": mapped_columns,
                                            "sheet_name": "DATA ENTRY",
                                        },
                                        "credentials_dict": user_google_credentials,
                                    },
                                )
                            else:
                                find_result = find_dates_response.json()

                                if find_result.get("success"):
                                    dates_found = find_result["result"]["dates_found"]
                                    dates_not_found = find_result["result"][
                                        "dates_not_found"
                                    ]
                                    date_to_row = find_result["result"]["date_to_row"]

                                    print(
                                        f"   ✓ Found {len(dates_found)} dates in sheet"
                                    )

                                    if len(dates_found) == 0:
                                        # No dates exist - safe to upload
                                        return JsonResponse(
                                            {
                                                "requires_confirmation": True,
                                                "confirmation_type": "safe",
                                                "conflict_data": {
                                                    "total_conflicts": 0,
                                                    "total_safe": len(upload_dates),
                                                    "safe_dates": upload_dates[:10],
                                                    "mapped_columns": mapped_columns[
                                                        :10
                                                    ],
                                                    "mapped_pairs": mapped_pairs[:10],
                                                },
                                                "message": (
                                                    f"📋 Upload Confirmation\n\n"
                                                    f"These dates don't exist in the sheet yet.\n"
                                                    f"Safe to upload {len(upload_dates)} new dates.\n\n"
                                                    f"Will map {len(mapped_pairs)} columns."
                                                ),
                                            },
                                            status=200,
                                        )

                                    # ============================================
                                    # STEP 2: Check specific cells in those rows
                                    # ============================================
                                    print(
                                        f"   Phase 2: Checking cells in {len(dates_found)} rows..."
                                    )

                                    # Get row numbers for found dates
                                    row_numbers = []
                                    for date in dates_found:
                                        # Normalize date to match date_to_row keys
                                        from datetime import datetime

                                        for fmt in ["%Y-%m-%d", "%d-%b-%y"]:
                                            try:
                                                parsed = datetime.strptime(
                                                    str(date), fmt
                                                )
                                                normalized = parsed.strftime("%Y-%m-%d")
                                                if normalized in date_to_row:
                                                    row_numbers.append(
                                                        date_to_row[normalized]
                                                    )
                                                break
                                            except:
                                                continue

                                    check_cells_response = requests.post(
                                        "http://localhost:8003/execute_task",
                                        json={
                                            "tool": "check_specific_cells_have_data",
                                            "inputs": {
                                                "sheet_id": sheet_id,
                                                "row_numbers": row_numbers,
                                                "column_names": mapped_columns,
                                                "sheet_name": "DATA ENTRY",
                                            },
                                            "credentials_dict": user_google_credentials,
                                        },
                                    )

                                    if check_cells_response.status_code != 200:
                                        # Fallback to original method
                                        print(
                                            f"   ⚠️  Cell check failed, using fallback..."
                                        )
                                        check_response = requests.post(
                                            "http://localhost:8003/execute_task",
                                            json={
                                                "tool": "check_dates_and_columns_have_data",
                                                "inputs": {
                                                    "sheet_id": sheet_id,
                                                    "dates_to_check": upload_dates,
                                                    "columns_to_check": mapped_columns,
                                                    "sheet_name": "DATA ENTRY",
                                                },
                                                "credentials_dict": user_google_credentials,
                                            },
                                        )
                                    else:
                                        cells_result = check_cells_response.json()

                                        if cells_result.get("success"):
                                            result_data = cells_result.get("result", {})
                                            rows_with_data = result_data.get(
                                                "rows_with_data", []
                                            )
                                            rows_without_data = result_data.get(
                                                "rows_without_data", []
                                            )

                                            if len(rows_with_data) > 0:
                                                # CONFLICTS FOUND
                                                print(
                                                    f"      ⚠️  {len(rows_with_data)} rows have data in mapped columns!"
                                                )

                                                # Build detailed conflict message
                                                conflict_details = []
                                                for row_info in rows_with_data[:3]:
                                                    cells = row_info.get(
                                                        "cells_with_data", []
                                                    )
                                                    conflict_details.append(
                                                        f"• Row {row_info['row_number']}: "
                                                        f"{len(cells)} cells have data"
                                                    )

                                                return JsonResponse(
                                                    {
                                                        "requires_confirmation": True,
                                                        "confirmation_type": "overwrite",
                                                        "conflict_data": {
                                                            "total_conflicts": len(
                                                                rows_with_data
                                                            ),
                                                            "total_safe": len(
                                                                rows_without_data
                                                            ),
                                                            "conflicting_rows": rows_with_data[
                                                                :10
                                                            ],
                                                            "mapped_columns": mapped_columns[
                                                                :10
                                                            ],
                                                            "mapped_pairs": mapped_pairs[
                                                                :10
                                                            ],
                                                        },
                                                        "message": (
                                                            f"⚠️ DATA CONFLICT WARNING\n\n"
                                                            f"{len(rows_with_data)} of {len(dates_found)} dates have data "
                                                            f"in the columns you're mapping!\n\n"
                                                            f"Conflicts:\n"
                                                            f"{chr(10).join(conflict_details)}\n\n"
                                                            f"Your upload will OVERWRITE these columns:\n"
                                                            f"{chr(10).join(mapped_pairs[:5])}\n\n"
                                                            f"⚠️ This will replace existing data.\n\n"
                                                            f"Proceed with overwrite?"
                                                        ),
                                                    },
                                                    status=200,
                                                )
                                            else:
                                                # NO CONFLICTS - Dates exist but cells are empty
                                                print(
                                                    f"      ✅ Dates exist but mapped columns are empty!"
                                                )

                                                return JsonResponse(
                                                    {
                                                        "requires_confirmation": True,
                                                        "confirmation_type": "safe",
                                                        "conflict_data": {
                                                            "total_conflicts": 0,
                                                            "total_safe": len(
                                                                dates_found
                                                            ),
                                                            "safe_dates": dates_found[
                                                                :10
                                                            ],
                                                            "mapped_columns": mapped_columns[
                                                                :10
                                                            ],
                                                            "mapped_pairs": mapped_pairs[
                                                                :10
                                                            ],
                                                        },
                                                        "message": (
                                                            f"📋 Upload Confirmation\n\n"
                                                            f"These dates exist but the columns you're mapping are empty.\n\n"
                                                            f"Will add data to:\n"
                                                            f"{chr(10).join(mapped_pairs[:5])}\n\n"
                                                            f"Proceed with upload?"
                                                        ),
                                                    },
                                                    status=200,
                                                )
                                        else:
                                            # cells_result not successful, use fallback
                                            check_response = requests.post(
                                                "http://localhost:8003/execute_task",
                                                json={
                                                    "tool": "check_dates_and_columns_have_data",
                                                    "inputs": {
                                                        "sheet_id": sheet_id,
                                                        "dates_to_check": upload_dates,
                                                        "columns_to_check": mapped_columns,
                                                        "sheet_name": "DATA ENTRY",
                                                    },
                                                    "credentials_dict": user_google_credentials,
                                                },
                                            )
                                else:
                                    # find_result not successful, use fallback
                                    check_response = requests.post(
                                        "http://localhost:8003/execute_task",
                                        json={
                                            "tool": "check_dates_and_columns_have_data",
                                            "inputs": {
                                                "sheet_id": sheet_id,
                                                "dates_to_check": upload_dates,
                                                "columns_to_check": mapped_columns,
                                                "sheet_name": "DATA ENTRY",
                                            },
                                            "credentials_dict": user_google_credentials,
                                        },
                                    )

                            # Only process check_response if it was set (fallback cases)
                            if (
                                "check_response" in locals()
                                and check_response is not None
                            ):
                                print(
                                    f"   ℹ️  Using fallback conflict detection method..."
                                )

                            if (
                                "check_response" in locals()
                                and check_response is not None
                                and check_response.status_code == 200
                            ):
                                check_result = check_response.json()
                                if check_result.get("success"):
                                    result_data = check_result.get("result", {})
                                    conflicting_cells = result_data.get(
                                        "conflicting_cells", []
                                    )
                                    dates_with_data = result_data.get(
                                        "dates_with_data", []
                                    )
                                    dates_without_data = result_data.get(
                                        "dates_without_data", []
                                    )

                                    if len(conflicting_cells) > 0:
                                        # CONFLICTS FOUND - Show details
                                        print(
                                            f"      ⚠️ {len(conflicting_cells)} dates have conflicting data!"
                                        )

                                        # Build detailed conflict message
                                        conflict_details = []
                                        for conflict in conflicting_cells[
                                            :3
                                        ]:  # Show first 3
                                            affected_cols = conflict.get(
                                                "affected_columns", []
                                            )
                                            conflict_details.append(
                                                f"• {conflict['date']} (Row {conflict['row_number']}): "
                                                f"{', '.join(affected_cols[:3])}"
                                            )

                                        return JsonResponse(
                                            {
                                                "requires_confirmation": True,
                                                "confirmation_type": "overwrite",
                                                "conflict_data": {
                                                    "total_conflicts": len(
                                                        conflicting_cells
                                                    ),
                                                    "total_safe": len(
                                                        dates_without_data
                                                    ),
                                                    "conflicting_dates": dates_with_data[
                                                        :10
                                                    ],
                                                    "safe_dates": dates_without_data[
                                                        :5
                                                    ],
                                                    "sample_conflicts": conflicting_cells[
                                                        :5
                                                    ],
                                                    "mapped_columns": mapped_columns[
                                                        :10
                                                    ],
                                                    "mapped_pairs": mapped_pairs[:10],
                                                },
                                                "message": (
                                                    f"⚠️ DATA CONFLICT WARNING\n\n"
                                                    f"{len(conflicting_cells)} of {len(upload_dates)} dates have existing data "
                                                    f"in columns you're trying to map!\n\n"
                                                    f"Conflicts found:\n"
                                                    f"{chr(10).join(conflict_details)}"
                                                    f"{(chr(10) + '... and ' + str(len(conflicting_cells) - 3) + ' more') if len(conflicting_cells) > 3 else ''}\n\n"
                                                    f"Your upload will OVERWRITE these columns:\n"
                                                    f"{chr(10).join(mapped_pairs[:3])}"
                                                    f"{(chr(10) + '... and ' + str(len(mapped_pairs) - 3) + ' more') if len(mapped_pairs) > 3 else ''}\n\n"
                                                    f"⚠️ This will replace existing operational data.\n\n"
                                                    f"Proceed with overwrite?"
                                                ),
                                            },
                                            status=200,
                                        )
                                    else:
                                        # NO CONFLICTS - Dates exist but mapped columns are empty
                                        print(
                                            f"      ✅ Dates exist but mapped columns are empty - safe!"
                                        )
                                        return JsonResponse(
                                            {
                                                "requires_confirmation": True,
                                                "confirmation_type": "safe",
                                                "conflict_data": {
                                                    "total_conflicts": 0,
                                                    "total_safe": len(upload_dates),
                                                    "safe_dates": upload_dates[:10],
                                                    "mapped_columns": mapped_columns[
                                                        :10
                                                    ],
                                                    "mapped_pairs": mapped_pairs[:10],
                                                },
                                                "message": (
                                                    f"📋 Upload Confirmation\n\n"
                                                    f"You are uploading {len(upload_dates)} dates of data.\n\n"
                                                    f"✅ These dates exist but the columns you're mapping are empty.\n\n"
                                                    f"Will add data to these columns:\n"
                                                    f"{chr(10).join(mapped_pairs[:5])}"
                                                    f"{(chr(10) + '... and ' + str(len(mapped_pairs) - 5) + ' more') if len(mapped_pairs) > 5 else ''}\n\n"
                                                    f"Proceed with upload?"
                                                ),
                                            },
                                            status=200,
                                        )
            except Exception as e:
                print(f"⚠️  Could not check for existing data: {str(e)}")
                import traceback

                traceback.print_exc()
                # Continue with upload if check fails

        # ============================================
        # STEP 4: Transform data
        # ============================================
        print("Step 4: Transforming data...")
        transform_response = requests.post(
            "http://localhost:8004/execute_task",
            json={
                "tool": "transform_data",
                "inputs": {"source_data": full_data, "mappings": mappings},
            },
        )

        if transform_response.status_code != 200:
            return JsonResponse({"error": "Data transformation failed"}, status=500)

        transform_result = transform_response.json()
        if not transform_result.get("success"):
            return JsonResponse(
                {"error": transform_result.get("error", "Transform failed")}, status=500
            )

        transformed_data = transform_result["result"]["transformed_data"]
        print(f"   ✅ Transformed {transform_result['result']['row_count']} rows")

        # Build rows_with_dates
        rows_with_dates = [
            {"date": row.get("Date"), "row_index": i}
            for i, row in enumerate(parsed_data)
            if row.get("Date")
        ]

        # ============================================
        # STEP 5: Upload to Sheets
        # ============================================
        print("Step 5: Uploading to Google Sheets...")

        upload_response = requests.post(
            "http://localhost:8003/execute_task",
            json={
                "tool": "update_by_date_match",
                "inputs": {
                    "sheet_id": sheet_id,
                    "transformed_data": transformed_data,
                    "rows_with_dates": rows_with_dates,
                    "sheet_name": "DATA ENTRY",
                    "date_column": "Date",
                },
                "credentials_dict": user_google_credentials,
            },
        )

        if upload_response.status_code != 200:
            return JsonResponse(
                {"error": f"Sheets upload failed: {upload_response.text}"}, status=500
            )

        upload_result = upload_response.json()

        if not upload_result.get("success"):
            return JsonResponse(
                {"error": upload_result.get("error", "Upload failed")}, status=500
            )

        result_data = upload_result.get("result", {})
        rows_updated = result_data.get("rows_updated", 0)

        print(f"   ✅ Updated {rows_updated} rows in Google Sheets")

        return JsonResponse(
            {
                "success": True,
                "message": f"Successfully updated {rows_updated} rows",
                "details": {
                    "file_name": file.name,
                    "rows_uploaded": rows_updated,
                    "columns_mapped": len([m for m in mappings.values() if m]),
                    "high_confidence_mappings": map_result["result"][
                        "high_confidence_count"
                    ],
                    "sheet_id": sheet_id,
                },
            },
            status=200,
        )

    except Exception as e:
        import traceback

        print(f"❌ Error in dynamic_mapping_workflow: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({"error": f"Workflow failed: {str(e)}"}, status=500)


@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def abc_analysis_workflow(request):
    """
    Monthly ABC Analysis workflow - Direct integration like mapping agent
    Analyzes transaction data by month and uploads to Google Sheets
    """
    try:
        file = request.FILES.get("file")

        if not file:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        # ============================================
        # GET USER CREDENTIALS
        # ============================================
        from allauth.socialaccount.models import SocialToken, SocialAccount

        social_account = SocialAccount.objects.filter(
            user=request.user, provider="google"
        ).first()

        if not social_account:
            return JsonResponse(
                {
                    "error": "No Google account linked. Please connect your Google account first"
                },
                status=400,
            )

        google_token = SocialToken.objects.filter(account=social_account).first()

        if not google_token:
            return JsonResponse(
                {"error": "No Google token found. Please re-authenticate"},
                status=400,
            )

        user_google_credentials = {
            "access_token": google_token.token or "",
            "refresh_token": google_token.token_secret or "",
            "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
        }

        # ============================================
        # CALL ABC ANALYSIS AGENT
        # ============================================
        print(f"📊 Processing ABC Analysis for file: {file.name}")

        # Prepare file for upload to ABC agent
        files = {"file": (file.name, file.read(), file.content_type)}
        data = {"credentials": json.dumps(user_google_credentials)}

        # Call ABC Analysis Agent
        abc_response = requests.post(
            f"{settings.ABC_AGENT_URL}/analyze",
            files=files,
            data=data,
            timeout=120,  # Allow up to 2 minutes for processing
        )

        if abc_response.status_code != 200:
            error_detail = abc_response.text
            print(f"❌ ABC Agent Error: {error_detail}")
            return JsonResponse(
                {"error": f"ABC Analysis failed: {error_detail}"}, status=500
            )

        result = abc_response.json()

        if not result.get("success"):
            return JsonResponse(
                {"error": result.get("error", "Analysis failed")}, status=500
            )

        # Extract results
        analysis_data = result.get("result", {})
        sheet_url = analysis_data.get("sheet_url")
        monthly_summary = analysis_data.get("monthly_summary", {})
        months_analyzed = analysis_data.get("months_analyzed", [])

        print(f"   ✅ Analysis complete: {len(months_analyzed)} months analyzed")
        print(f"   📊 Sheet URL: {sheet_url}")

        return JsonResponse(
            {
                "success": True,
                "sheet_url": sheet_url,
                "sheet_id": analysis_data.get("sheet_id"),
                "total_transactions": analysis_data.get("total_transactions"),
                "months_analyzed": months_analyzed,
                "monthly_summary": monthly_summary,
                "message": f"Successfully analyzed {len(months_analyzed)} months of data",
            },
            status=200,
        )

    except requests.exceptions.Timeout:
        print("❌ ABC Analysis timeout")
        return JsonResponse(
            {"error": "Analysis took too long. Please try with a smaller file."},
            status=504,
        )
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to ABC Agent")
        return JsonResponse(
            {"error": "ABC Analysis service is not available. Please contact support."},
            status=503,
        )
    except Exception as e:
        import traceback

        print(f"❌ Error in abc_analysis_workflow: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({"error": f"Analysis failed: {str(e)}"}, status=500)


@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def workload_analysis_workflow(request):
    """
    Workload Analysis workflow - Analyzes TIME & MOTION STUDY data
    Calculates staffing requirements, productivity, and identifies bottlenecks
    """
    try:
        file = request.FILES.get("file")

        if not file:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        # Validate file type
        if not file.name.endswith((".xlsx", ".xlsm")):
            return JsonResponse(
                {"error": "File must be Excel (.xlsx or .xlsm)"}, status=400
            )

        # ============================================
        # GET USER CREDENTIALS
        # ============================================
        from allauth.socialaccount.models import SocialToken, SocialAccount

        social_account = SocialAccount.objects.filter(
            user=request.user, provider="google"
        ).first()

        if not social_account:
            return JsonResponse(
                {
                    "error": "No Google account linked. Please connect your Google account first"
                },
                status=400,
            )

        google_token = SocialToken.objects.filter(account=social_account).first()

        if not google_token:
            return JsonResponse(
                {"error": "No Google token found. Please re-authenticate"},
                status=400,
            )

        user_google_credentials = {
            "access_token": google_token.token or "",
            "refresh_token": google_token.token_secret or "",
            "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
        }

        # ============================================
        # CALL WORKLOAD ANALYSIS AGENT
        # ============================================
        print(f"📊 Processing Workload Analysis for file: {file.name}")

        # Prepare file for upload to workload agent
        files = {"file": (file.name, file.read(), file.content_type)}

        # Call Workload Analysis Agent
        workload_response = requests.post(
            f"{settings.WORKLOAD_AGENT_URL}/analyze/upload",
            files=files,
            timeout=120,  # Allow up to 2 minutes for processing
        )

        if workload_response.status_code != 200:
            error_detail = workload_response.text
            print(f"❌ Workload Agent Error: {error_detail}")

            # Try to parse error detail
            try:
                error_json = workload_response.json()
                error_message = error_json.get("detail", error_detail)
            except:
                error_message = error_detail

            return JsonResponse(
                {"error": f"Workload Analysis failed: {error_message}"}, status=500
            )

        result = workload_response.json()

        if not result.get("status") == "success":
            return JsonResponse(
                {"error": result.get("error", "Analysis failed")}, status=500
            )

        # Extract results
        summary = result.get("summary", {})
        processes = result.get("processes", [])
        bottleneck = result.get("bottleneck", {})
        ranking = result.get("ranking", [])

        print(
            f"   ✅ Analysis complete: {summary.get('total_processes')} processes analyzed"
        )
        print(f"   🎯 Bottleneck: {bottleneck.get('process_name')}")

        return JsonResponse(
            {
                "success": True,
                "filename": file.name,
                "upload_timestamp": result.get("upload_timestamp"),
                "summary": summary,
                "processes": processes,
                "bottleneck": bottleneck,
                "ranking": ranking,
                "message": f"Successfully analyzed {summary.get('total_processes')} processes",
            },
            status=200,
        )

    except requests.exceptions.Timeout:
        print("❌ Workload Analysis timeout")
        return JsonResponse(
            {"error": "Analysis took too long. Please try with a smaller file."},
            status=504,
        )
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Workload Agent")
        return JsonResponse(
            {
                "error": "Workload Analysis service is not available. Please ensure the agent is running on port 8008."
            },
            status=503,
        )
    except Exception as e:
        import traceback

        print(f"❌ Error in workload_analysis_workflow: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({"error": f"Analysis failed: {str(e)}"}, status=500)


@csrf_exempt
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def agent_monitoring_summary(request):
    """Get monitoring summary for all agents"""
    try:
        response = requests.get("http://localhost:8009/metrics/all", timeout=5)

        if response.status_code == 200:
            return JsonResponse(response.json(), status=200)
        else:
            return JsonResponse(
                {"error": "Failed to fetch monitoring data"}, status=500
            )

    except requests.exceptions.ConnectionError:
        return JsonResponse({"error": "Monitoring service unavailable"}, status=503)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_agent_feedback(request):
    """Submit user feedback for an agent task"""
    try:
        task_id = request.data.get("task_id")
        agent_name = request.data.get("agent_name")
        rating = request.data.get("rating")
        comment = request.data.get("comment", "")

        response = requests.post(
            "http://localhost:8009/metrics/feedback",
            json={
                "task_id": task_id,
                "agent_name": agent_name,
                "rating": rating,
                "comment": comment,
                "timestamp": datetime.now().isoformat(),
            },
            timeout=5,
        )

        return JsonResponse(response.json(), status=response.status_code)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def create_user_account(request):
    """
    Admin endpoint to create new user accounts
    """
    try:
        data = request.data

        # Required fields
        email = data.get("email")
        name = data.get("name")
        role = data.get("role", "User")
        department = data.get("department")
        warehouse = data.get("warehouse")
        position = data.get("position")

        # Validate required fields
        if not email or not name:
            return JsonResponse({"error": "Email and name are required"}, status=400)

        # Validate role
        if role not in ["Admin", "User"]:
            return JsonResponse(
                {"error": "Role must be either 'Admin' or 'User'"}, status=400
            )

        # Get current admin user
        from rest_framework_simplejwt.tokens import AccessToken

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(" ")[1]
        access_token = AccessToken(token)
        admin_email = access_token.get("email")

        # Create user in MySQL
        user = mysql_db.create_user(
            email=email,
            name=name,
            role=role,
            department=department,
            warehouse=warehouse,
            position=position,
            created_by=admin_email,
        )

        if user:
            # Log activity
            mysql_db.log_activity(
                user_id=user["user_id"],
                user_email=admin_email,
                user_name=name,
                user_role="Admin",
                action="create_user",
                details=f"Admin {admin_email} created new user {email} with role {role}",
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT"),
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": f"User {email} created successfully",
                    "user": {
                        "user_id": user["user_id"],
                        "email": user["email"],
                        "name": user["name"],
                        "role": user["role"],
                        "department": user["department"],
                        "warehouse": user["warehouse"],
                    },
                },
                status=201,
            )
        else:
            return JsonResponse({"error": "Failed to create user"}, status=500)

    except Exception as e:
        import traceback

        print(f"❌ Error in create_user_account: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_all_users(request):
    """
    Admin endpoint to get all users
    Only accessible by users with Admin role in JWT token
    """
    try:
        # ✅ Get user email from JWT token
        from rest_framework_simplejwt.tokens import AccessToken

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "Invalid authorization header"}, status=401)

        token = auth_header.split(" ")[1]
        access_token = AccessToken(token)

        current_user_email = access_token.get("email")

        # Optional: Get full user data from MySQL if needed
        # current_user = mysql_db.get_user_by_email(current_user_email)

        # Get role filter from query params
        role_filter = request.GET.get("role")
        users = mysql_db.get_all_users(role=role_filter)

        # Remove sensitive fields
        for user in users:
            user.pop("google_access_token", None)
            user.pop("google_refresh_token", None)

        return JsonResponse(
            {"success": True, "users": users, "count": len(users)}, status=200
        )

    except Exception as e:
        import traceback

        print(f"❌ Error in get_all_users: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def google_auth_mysql(request):
    """
    Handle Google OAuth authentication with MySQL
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            auth_code = data.get("code")

            if not auth_code:
                return JsonResponse(
                    {"error": "Authorization code is missing."}, status=400
                )

            print(f"Received auth code: {auth_code[:20]}...")

            # Exchange code for tokens
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": auth_code,
                "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
                "redirect_uri": "postmessage",
                "grant_type": "authorization_code",
            }

            token_response = requests.post(token_url, data=token_data)
            token_response_data = token_response.json()

            if "error" in token_response_data:
                return JsonResponse(
                    {
                        "error": token_response_data.get(
                            "error_description", token_response_data["error"]
                        )
                    },
                    status=400,
                )

            access_token = token_response_data.get("access_token")
            refresh_token = token_response_data.get("refresh_token", "")

            # Get user info from Google
            userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {"Authorization": f"Bearer {access_token}"}
            userinfo_response = requests.get(userinfo_url, headers=headers)
            userinfo = userinfo_response.json()

            email = userinfo.get("email")
            name = userinfo.get("name", "")
            google_id = userinfo.get("id")
            picture = userinfo.get("picture", "")

            if not email:
                return JsonResponse(
                    {"error": "Email not provided by Google"}, status=400
                )

            print(f"👤 Authenticating user: {email}")

            # Check if user exists in MySQL
            user = mysql_db.get_user_by_email(email)

            if not user:
                return JsonResponse(
                    {
                        "error": "User not found. Please contact your administrator to create an account."
                    },
                    status=404,
                )

            if not user["is_active"]:
                return JsonResponse(
                    {
                        "error": "Your account has been deactivated. Please contact your administrator."
                    },
                    status=403,
                )

            # Update Google tokens in MySQL
            from datetime import datetime, timedelta

            token_expiry = datetime.now() + timedelta(
                seconds=token_response_data.get("expires_in", 3600)
            )

            mysql_db.update_user_google_tokens(
                user_id=user["user_id"],
                google_id=google_id,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expiry=token_expiry,
            )

            # Log activity
            mysql_db.log_activity(
                user_id=user["user_id"],
                user_email=user["email"],
                user_name=user["name"],
                user_role=user["role"],
                action="login",
                details=f"User logged in via Google OAuth",
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT"),
            )

            # Create Django user for JWT
            try:
                django_user = User.objects.get(email=email)
            except User.DoesNotExist:
                username = email.split("@")[0]
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{email.split('@')[0]}{counter}"
                    counter += 1

                django_user = User.objects.create(
                    email=email,
                    username=username,
                    first_name=name.split()[0] if name else "",
                    last_name=(
                        " ".join(name.split()[1:])
                        if name and len(name.split()) > 1
                        else ""
                    ),
                )

            # ✅ Generate JWT tokens with custom claims (role, department, etc.)
            from rest_framework_simplejwt.tokens import RefreshToken

            refresh = RefreshToken.for_user(django_user)

            # Add custom claims to the token payload
            refresh["role"] = user["role"]
            refresh["department"] = user["department"]
            refresh["warehouse"] = user["warehouse"]
            refresh["mysql_user_id"] = user["user_id"]
            refresh["email"] = user["email"]
            refresh["name"] = user["name"]

            access_token_jwt = str(refresh.access_token)

            print(
                f"✅ User {email} authenticated successfully with role: {user['role']}"
            )

            return JsonResponse(
                {
                    "access": access_token_jwt,
                    "refresh": str(refresh),
                    "user": {
                        "email": user["email"],
                        "name": user["name"],
                        "picture": picture,
                        # ⚠️ Don't send role here - it's in the JWT token now
                    },
                },
                status=200,
            )

        except Exception as e:
            import traceback

            print(f"Error in google_auth_mysql: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse(
                {"error": f"Authentication failed: {str(e)}"}, status=500
            )

    return JsonResponse({"error": "Method not allowed"}, status=405)
