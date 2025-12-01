"""
Google Sheets Agent API - Pure CRUD Operations
Focused solely on Google Sheets operations (no parsing or mapping logic)
Works with pre-transformed data from the Mapping Agent
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import os
import uvicorn
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
from dotenv import load_dotenv
import time
from functools import wraps
from datetime import datetime
import requests

MONITORING_URL = os.getenv("MONITORING_SERVICE_URL", "http://localhost:8009")

# Load environment variables from .env file
load_dotenv()

# FastAPI app
app = FastAPI(title="Google Sheets Agent API", version="2.0.0")


# ============================================================
# MONITORING UTILITIES
# ============================================================


def calculate_accuracy(result: Any, task_type: str) -> float:
    """Calculate task-specific accuracy score"""
    if not isinstance(result, dict):
        return 100.0

    if not result.get("success"):
        return 0.0

    # Task-specific accuracy calculation
    if task_type == "update_by_date_match":
        rows_updated = result.get("rows_updated", 0)
        return 100.0 if rows_updated > 0 else 0

    elif task_type == "check_dates_and_columns_have_data":
        # ✅ FIX: Check if the result structure contains the expected data
        # Success = function returned proper conflict analysis
        if "result" in result and isinstance(result["result"], dict):
            inner_result = result["result"]
            # Check if we got the expected fields
            has_conflict_data = (
                "dates_with_data" in inner_result
                and "dates_without_data" in inner_result
                and "conflicting_cells" in inner_result
            )
            return 100.0 if has_conflict_data else 50.0
        return 100.0  # ✅ If no nested result, but success=True, still 100%

    elif task_type == "append_data":
        rows_appended = result.get("rows_appended", 0)
        return 100.0 if rows_appended > 0 else 0

    else:
        # Default: if task succeeded, assume 100% accuracy
        return 100.0


def monitor_task(agent_name: str, task_type: str):
    """
    Decorator to monitor agent tasks
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            task_id = f"{agent_name}_{int(time.time() * 1000)}"
            start_time = time.time()

            try:
                # Execute the function
                result = func(*args, **kwargs)

                # Calculate metrics
                latency = time.time() - start_time
                success = (
                    result.get("success", False) if isinstance(result, dict) else True
                )

                # Calculate accuracy
                accuracy = calculate_accuracy(result, task_type)

                # Report to monitoring
                try:
                    requests.post(
                        f"{MONITORING_URL}/metrics/record",
                        json={
                            "agent_name": agent_name,
                            "task_id": task_id,
                            "timestamp": datetime.now().isoformat(),
                            "accuracy_score": accuracy,
                            "latency_seconds": latency,
                            "success": success,
                            "error_message": (
                                result.get("error")
                                if isinstance(result, dict)
                                else None
                            ),
                            "task_type": task_type,
                            "input_size": len(str(kwargs)) if kwargs else 0,
                            "output_size": len(str(result)) if result else 0,
                        },
                        timeout=2,
                    )
                    print(
                        f"   📊 Monitoring: {task_type} | Success: {success} | Accuracy: {accuracy:.1f}%"
                    )
                except Exception as e:
                    print(f"   ⚠️ Monitoring report failed: {str(e)}")

                return result

            except Exception as e:
                latency = time.time() - start_time

                # Report failure
                try:
                    requests.post(
                        f"{MONITORING_URL}/metrics/record",
                        json={
                            "agent_name": agent_name,
                            "task_id": task_id,
                            "timestamp": datetime.now().isoformat(),
                            "accuracy_score": 0,
                            "latency_seconds": latency,
                            "success": False,
                            "error_message": str(e),
                            "task_type": task_type,
                        },
                        timeout=2,
                    )
                except:
                    pass

                raise

        return wrapper

    return decorator


# Pydantic Models
class CredentialsDict(BaseModel):
    """Google OAuth credentials"""

    access_token: str
    refresh_token: str
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


class ToolRequest(BaseModel):
    """Generic tool execution request"""

    tool: str
    inputs: Dict[str, Any]
    credentials_dict: CredentialsDict


class ToolResponse(BaseModel):
    """Generic tool execution response"""

    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ============================================================
# HELPER FUNCTIONS


def create_sheet(
    title: str,
    sheet_names: list = None,
    initial_data: list = None,
    credentials_dict: CredentialsDict = None,
):
    """Create a new Google Spreadsheet with optional initial data."""
    try:
        if not credentials_dict:
            return {"success": False, "error": "Credentials required"}
        service = create_sheets_service(credentials_dict)
        sheets = []
        if sheet_names:
            for name in sheet_names:
                sheets.append({"properties": {"title": name}})
        else:
            sheets.append({"properties": {"title": "Sheet1"}})
        spreadsheet = {"properties": {"title": title}, "sheets": sheets}
        result = service.spreadsheets().create(body=spreadsheet).execute()
        sheet_id = result.get("spreadsheetId")
        sheet_url = result.get("spreadsheetUrl")
        if initial_data and len(initial_data) > 0:
            first_sheet_name = sheet_names[0] if sheet_names else "Sheet1"
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=f"{first_sheet_name}!A1",
                valueInputOption="RAW",
                body={"values": initial_data},
            ).execute()
        return {
            "success": True,
            "sheet_id": sheet_id,
            "sheet_url": sheet_url,
            "title": title,
            "message": f"Created spreadsheet: {title}",
        }
    except HttpError as e:
        return {"success": False, "error": f"Google Sheets API error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Failed to create sheet: {str(e)}"}


def create_sheets_service(credentials_dict: CredentialsDict):
    """Create authenticated Google Sheets service"""
    try:
        creds = Credentials(
            token=credentials_dict.access_token or os.getenv("GOOGLE_ACCESS_TOKEN"),
            refresh_token=credentials_dict.refresh_token
            or os.getenv("GOOGLE_REFRESH_TOKEN"),
            client_id=credentials_dict.client_id or os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=credentials_dict.client_secret
            or os.getenv("GOOGLE_CLIENT_SECRET"),
            token_uri="https://oauth2.googleapis.com/token",
        )
        return build("sheets", "v4", credentials=creds)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


def read_sheet(
    sheet_id: str,
    range_name: str = "Sheet1",
    credentials_dict: Optional[CredentialsDict] = None,
) -> Dict[str, Any]:
    """
    Read data from a Google Sheet

    Args:
        sheet_id: Google Sheets ID
        range_name: Range to read (e.g., 'Sheet1' or 'Sheet1!A1:D10')
        credentials_dict: Google OAuth credentials

    Returns:
        Dictionary with sheet data
    """
    try:
        if not credentials_dict:
            return {"success": False, "error": "Credentials required"}

        service = create_sheets_service(credentials_dict)

        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range=range_name)
            .execute()
        )

        values = result.get("values", [])

        if not values:
            return {
                "success": True,
                "data": [],
                "row_count": 0,
                "column_count": 0,
                "range": range_name,
                "message": "No data found in range",
            }

        return {
            "success": True,
            "data": values,
            "row_count": len(values),
            "column_count": len(values[0]) if values else 0,
            "range": range_name,
        }

    except HttpError as e:
        return {"success": False, "error": f"Google Sheets API error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Failed to read sheet: {str(e)}"}


def update_sheet(
    sheet_id: str,
    range_name: str,
    data: List[List[Any]],
    credentials_dict: Optional[CredentialsDict] = None,
) -> Dict[str, Any]:
    """
    Update data in a specific range of a Google Sheet

    Args:
        sheet_id: Google Sheets ID
        range_name: Range to update (e.g., 'Sheet1!A1:D10')
        data: 2D list of values to write
        credentials_dict: Google OAuth credentials

    Returns:
        Dictionary with update results
    """
    try:
        if not credentials_dict:
            return {"success": False, "error": "Credentials required"}

        service = create_sheets_service(credentials_dict)

        result = (
            service.spreadsheets()
            .values()
            .update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": data},
            )
            .execute()
        )

        return {
            "success": True,
            "updated_cells": result.get("updatedCells", 0),
            "updated_rows": result.get("updatedRows", 0),
            "updated_columns": result.get("updatedColumns", 0),
            "range": range_name,
            "message": f"Updated {result.get('updatedCells', 0)} cells in {range_name}",
        }

    except HttpError as e:
        return {"success": False, "error": f"Google Sheets API error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Failed to update sheet: {str(e)}"}


def append_rows(
    sheet_id: str,
    data: List[List[Any]],
    sheet_name: str = "Sheet1",
    credentials_dict: Optional[CredentialsDict] = None,
) -> Dict[str, Any]:
    """
    Append rows to the end of a sheet

    Args:
        sheet_id: Google Sheets ID
        data: 2D list of rows to append
        sheet_name: Name of the sheet tab (default: "Sheet1")
        credentials_dict: Google OAuth credentials

    Returns:
        Dictionary with append results
    """
    try:
        if not credentials_dict:
            return {"success": False, "error": "Credentials required"}

        service = create_sheets_service(credentials_dict)

        # Find the next empty row
        range_name = f"{sheet_name}!A:A"
        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": data},
            )
            .execute()
        )

        return {
            "success": True,
            "rows_added": len(data),
            "range_updated": result.get("updates", {}).get("updatedRange"),
            "updated_cells": result.get("updates", {}).get("updatedCells", 0),
            "message": f"Appended {len(data)} rows to {sheet_name}",
        }

    except HttpError as e:
        return {"success": False, "error": f"Google Sheets API error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Failed to append rows: {str(e)}"}


def upload_mapped_data(
    sheet_id: str,
    transformed_data: str,
    sheet_name: str = "Sheet1",
    append_mode: bool = True,
    credentials_dict: Optional[CredentialsDict] = None,
) -> Dict[str, Any]:
    """
    Upload pre-transformed data to Google Sheets

    SUPPORTS:
    - OPR workflow: Data from mapping_agent (after transform_data)
    - ABC workflow: Data from abc_analysis_agent (after export_for_sheets)
    - Any future workflow: Generic JSON → Sheets upload

    FIXES:
    - Converts numpy types to Python native types
    - Handles datetime objects
    - Ensures Google Sheets API compatibility
    """
    try:
        # Use provided credentials or fall back to environment variables
        if not credentials_dict:
            credentials_dict = CredentialsDict(
                access_token=os.getenv("GOOGLE_ACCESS_TOKEN"),
                refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            )

        service = create_sheets_service(credentials_dict)

        try:
            print(f"🔍 Checking if sheet '{sheet_name}' exists...")
            print(f"   Sheet ID: {sheet_id}")
            print(f"   Service object: {type(service).__name__}")
            # Test basic authentication first
            print(f"   🧪 Testing basic API access...")
            spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            print(f"   ✅ Successfully accessed spreadsheet!")
            print(
                f"   Title: {spreadsheet.get('properties', {}).get('title', 'Unknown')}"
            )
            existing_sheets = [
                sheet["properties"]["title"] for sheet in spreadsheet["sheets"]
            ]
            print(f"   📋 Existing sheets: {existing_sheets}")
        except HttpError as e:
            print(f"❌ Google Sheets API HttpError details:")
            print(f"   Status Code: {e.resp.status}")
            print(f"   Reason: {e.resp.reason}")
            print(f"   URL: {e.uri}")
            print(f"   Content: {e.content.decode() if e.content else 'No content'}")
            # Check if it's a permissions issue
            if e.resp.status == 404:
                print(f"   🔍 404 Analysis:")
                print(f"      - Sheet ID might be incorrect")
                print(f"      - Sheet might not exist")
                print(f"      - No access permissions to this sheet")
                print(f"      - OAuth token might not have spreadsheets scope")
            return {
                "success": False,
                "error": f"Cannot access sheet (404): Check sheet ID and permissions",
            }
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            print(f"   Error type: {type(e).__name__}")
            import traceback

            traceback.print_exc()
            return {"success": False, "error": f"Failed to access sheet: {str(e)}"}

        if sheet_name not in existing_sheets:
            print(f"   📝 Creating sheet '{sheet_name}'...")
            requests = [{"addSheet": {"properties": {"title": sheet_name}}}]
            body = {"requests": requests}
            service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id, body=body
            ).execute()
            print(f"   ✅ Created sheet '{sheet_name}'")
        else:
            print(f"   ✓ Sheet '{sheet_name}' already exists")

        # Parse transformed data
        import pandas as pd

        df = pd.read_json(transformed_data)

        if df.empty:
            return {"success": False, "error": "Transformed data is empty"}

        # ============================================================
        # ✅ CRITICAL FIX: Universal Data Type Conversion
        # Handles data from ANY source (mapping_agent, abc_agent, etc.)
        # ============================================================
        import numpy as np
        from datetime import datetime

        print(f"🔄 Converting data types for Google Sheets API...")
        print(f"   Input: {len(df)} rows, {len(df.columns)} columns")

        # Step 1: Convert datetime columns to strings
        datetime_cols = []
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
                datetime_cols.append(col)

        if datetime_cols:
            print(f"   ✓ Converted {len(datetime_cols)} datetime column(s)")

        # Step 2: Convert numpy types to Python native types
        def to_native_type(val):
            """Convert any value to JSON-serializable Python type"""
            # Handle null/missing values
            if val is None or pd.isna(val) or val is pd.NA or val is pd.NaT:
                return ""

            # Handle numpy integers
            if isinstance(
                val,
                (
                    np.integer,
                    np.int64,
                    np.int32,
                    np.int16,
                    np.int8,
                    np.uint64,
                    np.uint32,
                    np.uint16,
                    np.uint8,
                ),
            ):
                return int(val)

            # Handle numpy floats
            if isinstance(val, (np.floating, np.float64, np.float32, np.float16)):
                float_val = float(val)
                if float_val.is_integer():
                    return int(float_val)
                return round(float_val, 2)

            # Handle numpy booleans
            if isinstance(val, (np.bool_, bool)):
                return bool(val)

            # Handle datetime objects
            if isinstance(val, (pd.Timestamp, datetime)):
                return val.strftime("%Y-%m-%d %H:%M:%S")

            # ✅ NumPy 2.0 fix: Just convert everything else to string
            # No need to check for np.unicode_ which doesn't exist anymore
            return str(val)

        # Apply conversion to all cells
        conversion_count = 0
        for col in df.columns:
            original_dtype = df[col].dtype
            df[col] = df[col].apply(to_native_type)

            # Check if conversion happened
            if str(original_dtype).startswith("int") or str(original_dtype).startswith(
                "float"
            ):
                conversion_count += 1

        print(f"   ✓ Converted {conversion_count} numeric column(s) to native types")
        print(f"   ✅ All data types converted to Google Sheets-compatible format")

        # Convert DataFrame to 2D list
        headers = [df.columns.tolist()]
        data_rows = df.values.tolist()
        all_data = headers + data_rows

        print(f"   📊 Final data: {len(data_rows)} rows × {len(headers[0])} columns")

        if append_mode:
            # Append to existing data
            print(f"   📤 Appending to sheet '{sheet_name}'...")
            result = (
                service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=sheet_id,
                    range=f"{sheet_name}!A:A",
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body={"values": all_data},
                )
                .execute()
            )

            print(f"   ✅ Successfully appended {len(data_rows)} rows")

            return {
                "success": True,
                "rows_added": len(all_data),
                "data_rows": len(data_rows),
                "range_updated": result.get("updates", {}).get("updatedRange"),
                "mode": "append",
                "message": f"Appended {len(data_rows)} data rows to {sheet_name}",
            }
        else:
            # Overwrite from A1
            print(f"   📤 Writing to sheet '{sheet_name}' (overwrite mode)...")
            result = (
                service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=sheet_id,
                    range=f"{sheet_name}!A1",
                    valueInputOption="RAW",
                    body={"values": all_data},
                )
                .execute()
            )

            print(f"   ✅ Successfully wrote {len(data_rows)} rows")

            return {
                "success": True,
                "rows_written": len(all_data),
                "data_rows": len(data_rows),
                "updated_cells": result.get("updatedCells", 0),
                "mode": "overwrite",
                "message": f"Wrote {len(data_rows)} data rows to {sheet_name}",
            }

    except HttpError as e:
        print(f"❌ Google Sheets API error: {str(e)}")
        return {"success": False, "error": f"Google Sheets API error: {str(e)}"}
    except Exception as e:
        print(f"❌ Error in upload_mapped_data: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": f"Failed to upload data: {str(e)}"}


def get_sheet_metadata(
    sheet_id: str,
    credentials_dict: Optional[CredentialsDict] = None,
) -> Dict[str, Any]:
    """
    Get metadata about a spreadsheet (sheet names, row counts, etc.)

    Args:
        sheet_id: Google Sheets ID
        credentials_dict: Google OAuth credentials

    Returns:
        Dictionary with spreadsheet metadata
    """
    try:
        if not credentials_dict:
            return {"success": False, "error": "Credentials required"}

        service = create_sheets_service(credentials_dict)

        spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()

        sheets_info = []
        for sheet in spreadsheet.get("sheets", []):
            props = sheet.get("properties", {})
            grid_props = props.get("gridProperties", {})

            sheets_info.append(
                {
                    "sheet_id": props.get("sheetId"),
                    "title": props.get("title"),
                    "index": props.get("index"),
                    "row_count": grid_props.get("rowCount", 0),
                    "column_count": grid_props.get("columnCount", 0),
                }
            )

        return {
            "success": True,
            "spreadsheet_id": sheet_id,
            "title": spreadsheet.get("properties", {}).get("title"),
            "sheets": sheets_info,
            "sheet_count": len(sheets_info),
        }

    except HttpError as e:
        return {"success": False, "error": f"Google Sheets API error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Failed to get metadata: {str(e)}"}


def clear_sheet(
    sheet_id: str,
    range_name: str = "Sheet1",
    credentials_dict: Optional[CredentialsDict] = None,
) -> Dict[str, Any]:
    """
    Clear data from a sheet range

    Args:
        sheet_id: Google Sheets ID
        range_name: Range to clear (e.g., 'Sheet1' or 'Sheet1!A1:D10')
        credentials_dict: Google OAuth credentials

    Returns:
        Dictionary with clear results
    """
    try:
        if not credentials_dict:
            return {"success": False, "error": "Credentials required"}

        service = create_sheets_service(credentials_dict)

        result = (
            service.spreadsheets()
            .values()
            .clear(spreadsheetId=sheet_id, range=range_name, body={})
            .execute()
        )

        return {
            "success": True,
            "cleared_range": result.get("clearedRange"),
            "message": f"Cleared data from {range_name}",
        }

    except HttpError as e:
        return {"success": False, "error": f"Google Sheets API error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Failed to clear sheet: {str(e)}"}


def check_sheet_has_data(
    sheet_id: str,
    sheet_name: str = "DATA ENTRY",
    credentials_dict: Optional[CredentialsDict] = None,
) -> Dict[str, Any]:
    try:
        if not credentials_dict:
            return {"success": False, "error": "Credentials required"}

        service = create_sheets_service(credentials_dict)

        # Read the entire sheet - EXPLICITLY specify A:Z or wider range
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=sheet_id, range=f"{sheet_name}!A:DZ"
            )  # <-- FIX: Explicit wide range
            .execute()
        )

        values = result.get("values", [])

        # Check if there's data beyond the header row
        has_data = False
        data_row_count = 0

        if len(values) > 1:  # Has more than just header
            # Check if any row has actual data (not just dates)
            for row_idx, row in enumerate(values[1:], start=1):
                # Check if row has data in columns beyond just the date column
                non_empty_cells = sum(
                    1 for cell in row[1:] if cell and str(cell).strip()
                )
                if non_empty_cells > 0:
                    has_data = True
                    data_row_count += 1

        # Get sample of existing dates if data exists
        existing_dates = []
        if has_data and len(values) > 1:
            for row in values[1:6]:  # Get first 5 data rows
                if row and len(row) > 0:
                    existing_dates.append(row[0])

        return {
            "success": True,
            "has_data": has_data,
            "total_rows": len(values),
            "data_row_count": data_row_count,
            "header_row": values[0] if values else [],
            "existing_dates": existing_dates,
            "message": (
                f"Sheet has {data_row_count} rows with operational data"
                if has_data
                else "Sheet is empty (only headers or dates without data)"
            ),
        }

    except HttpError as e:
        return {"success": False, "error": f"Google Sheets API error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Failed to check sheet: {str(e)}"}


def column_index_to_letter(idx: int) -> str:
    """Convert column index (0-based) to column letter (A, B, ..., Z, AA, AB, ...)"""
    letter = ""
    idx += 1  # Convert to 1-based
    while idx > 0:
        idx -= 1
        letter = chr(idx % 26 + ord("A")) + letter
        idx //= 26
    return letter


def normalize_column_name(name: str) -> str:
    """
    Normalize column names for matching

    Handles:
    - Literal \\n (backslash-n from file)
    - Actual newline characters
    - Extra whitespace
    """
    if not name:
        return ""

    # Replace literal backslash-n with space
    name = name.replace("\\n", " ")

    # Replace actual newline character with space
    name = name.replace("\n", " ")

    # Remove parentheses and normalize spacing
    name = name.replace("(", " ").replace(")", " ")

    # Remove extra whitespace
    name = " ".join(name.split())

    return name.strip()


@monitor_task("sheets_agent", "update_by_date_match")
def update_by_date_match(
    sheet_id: str,
    transformed_data: str,
    rows_with_dates: Any,
    sheet_name: str = "DATA ENTRY",
    date_column: str = "Date",
    credentials_dict: Optional[CredentialsDict] = None,
) -> Dict[str, Any]:
    """
    FIXED: Update Google Sheets rows by matching dates AND column names
    """
    try:
        print(f"\n📊 Update by Date Match (FIXED VERSION)")
        print(f"   Sheet: {sheet_id}/{sheet_name}")
        print(f"   Date column: {date_column}")

        if not credentials_dict:
            return {"success": False, "error": "Credentials required"}

        # ===== FIX #1: Parse rows_with_dates =====
        print(f"\n🔍 Parsing rows_with_dates...")
        if isinstance(rows_with_dates, str):
            import ast
            import json

            try:
                rows_with_dates = json.loads(rows_with_dates)
            except:
                try:
                    rows_with_dates = json.loads(rows_with_dates.replace("'", '"'))
                except:
                    rows_with_dates = ast.literal_eval(rows_with_dates)
        elif isinstance(rows_with_dates, dict):
            if "rows_with_dates" in rows_with_dates:
                rows_with_dates = rows_with_dates["rows_with_dates"]

        if not isinstance(rows_with_dates, list) or len(rows_with_dates) == 0:
            return {"success": False, "error": "Invalid or empty rows_with_dates"}

        print(f"   ✅ Parsed: {len(rows_with_dates)} rows")

        # ===== FIX #2: Parse transformed data =====
        import pandas as pd

        transformed_df = pd.read_json(transformed_data)
        print(
            f"   Transformed: {len(transformed_df)} rows, {len(transformed_df.columns)} columns"
        )
        print(f"   Columns: {list(transformed_df.columns)}")

        # Get Google Sheets service
        service = create_sheets_service(credentials_dict)

        # Read header row from Google Sheets
        header_result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range=f"{sheet_name}!1:1")
            .execute()
        )

        if not header_result.get("values"):
            return {"success": False, "error": "Could not read header row"}

        header_row = header_result["values"][0]
        print(f"\n📋 Google Sheets Headers ({len(header_row)} columns)")

        # Build column name → column index map WITH NORMALIZATION
        column_map = {}
        column_map_original = {}

        for idx, col_name in enumerate(header_row):
            normalized = normalize_column_name(col_name)
            column_map[normalized] = idx
            column_map_original[normalized] = col_name

        print(f"\n🗺️  Column Name → Index Mapping (normalized):")

        # Verify all transformed columns
        missing_columns = []
        for col_name in transformed_df.columns:
            normalized = normalize_column_name(col_name)

            if normalized in column_map:
                col_idx = column_map[normalized]
                col_letter = column_index_to_letter(col_idx)
                print(f"   ✓ {col_name[:35]:35} → Column {col_letter}")
            else:
                print(f"   ✗ {col_name[:35]:35} → NOT FOUND!")
                missing_columns.append(col_name)

        if missing_columns:
            print(f"\n⚠️  WARNING: {len(missing_columns)} columns not found")

        # Find date column
        date_col_normalized = normalize_column_name(date_column)
        if date_col_normalized not in column_map:
            return {"success": False, "error": f"Date column '{date_column}' not found"}

        date_col_idx = column_map[date_col_normalized]
        print(f"\n📅 Date column '{date_column}' at index {date_col_idx}")

        # ===== FIX #3: Build date → row mapping =====
        data_result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range=f"{sheet_name}")  # Reads ALL columns
            .execute()
        )
        sheet_data = data_result.get("values", [])

        from datetime import datetime

        date_to_row = {}

        for row_idx, row_data in enumerate(sheet_data[1:], start=2):  # Skip header
            if len(row_data) > date_col_idx:
                date_value = str(row_data[date_col_idx]).strip()

                for fmt in ["%d-%b-%y", "%d-%b-%Y", "%Y-%m-%d", "%m/%d/%Y"]:
                    try:
                        parsed = datetime.strptime(date_value, fmt)
                        normalized = parsed.strftime("%Y-%m-%d")
                        date_to_row[normalized] = row_idx
                        break
                    except:
                        continue

        print(f"   Found {len(date_to_row)} dates in Google Sheets")

        # ===== FIX #4: Match dates and update cells =====
        print(f"\n🔄 Matching dates and updating cells...")

        updates = []
        rows_updated = 0
        rows_not_found = []

        for row_info in rows_with_dates:
            excel_date = row_info.get("date")
            row_idx = row_info.get("row_index", 0)

            if not excel_date:
                continue

            # Normalize Excel date
            excel_date_normalized = None
            for fmt in ["%Y-%m-%d", "%d-%b-%y", "%d-%b-%Y"]:
                try:
                    parsed = datetime.strptime(str(excel_date), fmt)
                    excel_date_normalized = parsed.strftime("%Y-%m-%d")
                    break
                except:
                    continue

            if not excel_date_normalized or excel_date_normalized not in date_to_row:
                rows_not_found.append(excel_date)
                continue

            # Found matching row!
            sheet_row_num = date_to_row[excel_date_normalized]

            if row_idx >= len(transformed_df):
                continue

            transformed_row = transformed_df.iloc[row_idx]

            # Update each column BY NORMALIZED NAME
            for col_name in transformed_df.columns:
                normalized = normalize_column_name(col_name)

                if normalized not in column_map:
                    continue

                col_idx = column_map[normalized]
                col_letter = column_index_to_letter(col_idx)

                value = transformed_row[col_name]
                value_str = str(value) if pd.notna(value) else ""

                cell_range = f"{sheet_name}!{col_letter}{sheet_row_num}"
                updates.append({"range": cell_range, "values": [[value_str]]})

            rows_updated += 1
            if rows_updated <= 3:
                print(f"   ✓ Row {sheet_row_num}: {excel_date}")

        if rows_updated > 3:
            print(f"   ... and {rows_updated - 3} more rows")

        # Batch update all cells
        if updates:
            print(f"\n📤 Executing batch update of {len(updates)} cells...")
            body = {"valueInputOption": "USER_ENTERED", "data": updates}

            result = (
                service.spreadsheets()
                .values()
                .batchUpdate(spreadsheetId=sheet_id, body=body)
                .execute()
            )

            print(f"   ✅ Updated {rows_updated} rows successfully!")

        return {
            "success": True,
            "rows_updated": rows_updated,
            "total_rows_processed": len(rows_with_dates),
            "rows_not_found": rows_not_found,
            "message": f"Successfully updated {rows_updated} rows by date matching",
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


def upload_multi_sheet_data(
    sheet_id: str,
    sheets_data: Any,
    credentials_dict: Optional[CredentialsDict] = None,
) -> Dict[str, Any]:
    """
    Upload data to multiple sheets at once

    Args:
        sheet_id: Google Sheets ID
        sheets_data: Dict (or JSON string) mapping sheet names to 2D data arrays
        credentials_dict: Google OAuth credentials

    Returns:
        Upload results for all sheets
    """
    try:
        print(f"\n📊 Upload Multi-Sheet Data")
        print(f"   Sheet ID: {sheet_id}")
        print(f"   sheets_data type: {type(sheets_data).__name__}")

        # ============================================
        # STEP 0: Debug - Show what we received
        # ============================================
        if isinstance(sheets_data, str):
            print(f"   sheets_data length: {len(sheets_data)} chars")
            if len(sheets_data) > 0:
                print(f"   First 200 chars: {repr(sheets_data[:200])}")

            # Check if empty or whitespace
            if not sheets_data or not sheets_data.strip():
                return {
                    "success": False,
                    "error": "sheets_data is empty or whitespace only",
                    "debug_info": {
                        "received_type": type(sheets_data).__name__,
                        "received_length": len(sheets_data),
                        "is_empty": not sheets_data,
                        "is_whitespace": (
                            sheets_data.isspace() if sheets_data else False
                        ),
                    },
                }

        # ============================================
        # STEP 1: Parse sheets_data if it's a string
        # ============================================
        if isinstance(sheets_data, str):
            print(f"   Attempting to parse string...")

            # Try json.loads first
            try:
                sheets_data = json.loads(sheets_data)
                print(f"   ✓ Parsed with json.loads()")
            except json.JSONDecodeError as json_err:
                print(f"   ✗ json.loads() failed: {str(json_err)}")

                # Try ast.literal_eval as backup
                try:
                    import ast

                    sheets_data = ast.literal_eval(sheets_data)
                    print(f"   ✓ Parsed with ast.literal_eval()")
                except (ValueError, SyntaxError) as ast_err:
                    print(f"   ✗ ast.literal_eval() failed: {str(ast_err)}")

                    return {
                        "success": False,
                        "error": "Failed to parse sheets_data",
                        "debug_info": {
                            "json_error": str(json_err),
                            "ast_error": str(ast_err),
                            "received_length": len(sheets_data) if sheets_data else 0,
                            "preview": sheets_data[:300] if sheets_data else "EMPTY",
                            "suggestion": "Ensure the data is valid JSON or Python dict string",
                        },
                    }

        # Validate it's now a dict
        if not isinstance(sheets_data, dict):
            return {
                "success": False,
                "error": f"sheets_data must be a dict after parsing, got {type(sheets_data).__name__}",
                "debug_info": {
                    "type_received": type(sheets_data).__name__,
                    "value": str(sheets_data)[:200],
                },
            }

        # Validate dict is not empty
        if not sheets_data:
            return {
                "success": False,
                "error": "sheets_data dict is empty",
                "debug_info": {"keys_count": len(sheets_data)},
            }

        print(f"   ✓ Sheet names to upload: {list(sheets_data.keys())}")
        print(f"   ✓ Total sheets: {len(sheets_data)}")

        # ============================================
        # STEP 2: Get credentials
        # ============================================
        if not credentials_dict:
            credentials_dict = CredentialsDict(
                access_token=os.getenv("GOOGLE_ACCESS_TOKEN"),
                refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
            )

        service = create_sheets_service(credentials_dict)

        # ============================================
        # STEP 3: Upload to each sheet
        # ============================================
        results = {}
        for sheet_name, data in sheets_data.items():
            print(f"\n   📤 Uploading to '{sheet_name}'...")

            # Validate data is a list
            if not isinstance(data, list):
                print(f"      ✗ Invalid data type: {type(data).__name__}")
                results[sheet_name] = {
                    "error": f"Data must be a list, got {type(data).__name__}",
                    "rows": 0,
                    "cells_updated": 0,
                }
                continue

            if not data:
                print(f"      ⚠️  Empty data, skipping")
                results[sheet_name] = {
                    "rows": 0,
                    "cells_updated": 0,
                    "warning": "No data to upload",
                }
                continue

            print(f"      Rows to upload: {len(data)}")
            print(f"      Columns: {len(data[0]) if data else 0}")

            try:
                result = (
                    service.spreadsheets()
                    .values()
                    .update(
                        spreadsheetId=sheet_id,
                        range=f"'{sheet_name}'!A1",
                        valueInputOption="RAW",
                        body={"values": data},
                    )
                    .execute()
                )

                results[sheet_name] = {
                    "rows": len(data),
                    "cells_updated": result.get("updatedCells", 0),
                    "success": True,
                }

                print(f"      ✅ {result.get('updatedCells', 0)} cells updated")

            except HttpError as e:
                print(f"      ✗ Google Sheets API error: {str(e)}")
                results[sheet_name] = {
                    "error": f"API error: {str(e)}",
                    "rows": len(data),
                    "cells_updated": 0,
                }

        print(f"\n   ✅ Upload complete!")
        print(f"   Sheets processed: {len(results)}")
        print(
            f"   Successful uploads: {sum(1 for r in results.values() if r.get('success'))}"
        )

        # ============================================
        # STEP 4: Auto-apply formatting for ABC Analysis
        # ============================================
        # Detect if this is an ABC analysis upload by checking sheet names
        abc_sheet_names = {
            "Executive Summary",
            "Complete ABC Analysis",
            "Class A Items",
            "Class B Items",
            "Class C Items",
        }
        uploaded_names = set(results.keys())

        # If 3+ ABC sheets detected, auto-apply formatting
        if len(abc_sheet_names.intersection(uploaded_names)) >= 3:
            print(f"\n🎨 Detected ABC Analysis - Auto-applying formatting...")
            try:
                format_result = apply_sheet_formatting(sheet_id, credentials_dict)
                if format_result.get("success"):
                    print(
                        f"   ✅ Formatting applied to {len(format_result.get('sheets_formatted', []))} sheets"
                    )
                else:
                    print(f"   ⚠️ Formatting failed: {format_result.get('error')}")
            except Exception as e:
                print(f"   ⚠️ Formatting error (non-critical): {str(e)}")

        return {
            "success": True,
            "sheets_updated": list(results.keys()),
            "results": results,
            "message": f"Uploaded data to {len(results)} sheets",
            "summary": {
                "total_sheets": len(results),
                "successful": sum(1 for r in results.values() if r.get("success")),
                "failed": sum(1 for r in results.values() if "error" in r),
            },
        }

    except Exception as e:
        print(f"❌ Unexpected error in upload_multi_sheet_data: {str(e)}")
        import traceback

        traceback.print_exc()
        return {
            "success": False,
            "error": f"Multi-sheet upload failed: {str(e)}",
            "traceback": traceback.format_exc(),
        }


def apply_sheet_formatting(
    sheet_id: str, credentials_dict: Optional[CredentialsDict] = None
) -> Dict[str, Any]:
    """
    Apply exact formatting from ABC_Analysis_Complete.xlsx to Google Sheets

    Colors:
    - Dark Blue Header: #1F4E78
    - Blue Headers: #4472C4
    - Class A Green: #C6EFCE (light), #70AD47 (dark)
    - Class B Yellow: #FFEB9C (light), #FFC000 (dark)
    - Class C Red: #FFC7CE
    """
    try:
        if not credentials_dict:
            credentials_dict = CredentialsDict(
                access_token=os.getenv("GOOGLE_ACCESS_TOKEN"),
                refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
            )

        service = create_sheets_service(credentials_dict)

        requests = []

        # Get sheet properties to get sheet IDs
        spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets_info = {
            sheet["properties"]["title"]: sheet["properties"]["sheetId"]
            for sheet in spreadsheet["sheets"]
        }

        # ============================================
        # 1. EXECUTIVE SUMMARY FORMATTING
        # ============================================
        if "Executive Summary" in sheets_info:
            exec_sheet_id = sheets_info["Executive Summary"]

            # Title row (A1:F1) - Dark blue with white text
            requests.append(
                {
                    "mergeCells": {
                        "range": {
                            "sheetId": exec_sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 6,
                        },
                        "mergeType": "MERGE_ALL",
                    }
                }
            )
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": exec_sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 6,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.12,
                                    "green": 0.31,
                                    "blue": 0.47,
                                },
                                "textFormat": {
                                    "bold": True,
                                    "foregroundColor": {
                                        "red": 1,
                                        "green": 1,
                                        "blue": 1,
                                    },
                                    "fontSize": 14,
                                },
                                "horizontalAlignment": "CENTER",
                                "verticalAlignment": "MIDDLE",
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)",
                    }
                }
            )

            # Data labels (A3:A5) - Bold
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": exec_sheet_id,
                            "startRowIndex": 2,
                            "endRowIndex": 5,
                            "startColumnIndex": 0,
                            "endColumnIndex": 1,
                        },
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                        "fields": "userEnteredFormat.textFormat.bold",
                    }
                }
            )

            # "ABC CLASSIFICATION SUMMARY" header (A7)
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": exec_sheet_id,
                            "startRowIndex": 6,
                            "endRowIndex": 7,
                            "startColumnIndex": 0,
                            "endColumnIndex": 1,
                        },
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                        "fields": "userEnteredFormat.textFormat.bold",
                    }
                }
            )

            # Table headers (A8:F8) - Blue with white text
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": exec_sheet_id,
                            "startRowIndex": 7,
                            "endRowIndex": 8,
                            "startColumnIndex": 0,
                            "endColumnIndex": 6,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.27,
                                    "green": 0.45,
                                    "blue": 0.77,
                                },
                                "textFormat": {
                                    "bold": True,
                                    "foregroundColor": {
                                        "red": 1,
                                        "green": 1,
                                        "blue": 1,
                                    },
                                },
                                "horizontalAlignment": "CENTER",
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
                    }
                }
            )

            # Class A row (A9:F9) - Light green
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": exec_sheet_id,
                            "startRowIndex": 8,
                            "endRowIndex": 9,
                            "startColumnIndex": 0,
                            "endColumnIndex": 6,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.78,
                                    "green": 0.94,
                                    "blue": 0.81,
                                },
                                "horizontalAlignment": "CENTER",
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,horizontalAlignment)",
                    }
                }
            )

            # Class B row (A10:F10) - Light yellow
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": exec_sheet_id,
                            "startRowIndex": 9,
                            "endRowIndex": 10,
                            "startColumnIndex": 0,
                            "endColumnIndex": 6,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 1,
                                    "green": 0.92,
                                    "blue": 0.61,
                                },
                                "horizontalAlignment": "CENTER",
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,horizontalAlignment)",
                    }
                }
            )

            # Class C row (A11:F11) - Light red
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": exec_sheet_id,
                            "startRowIndex": 10,
                            "endRowIndex": 11,
                            "startColumnIndex": 0,
                            "endColumnIndex": 6,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 1,
                                    "green": 0.78,
                                    "blue": 0.81,
                                },
                                "horizontalAlignment": "CENTER",
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,horizontalAlignment)",
                    }
                }
            )

            # KEY INSIGHTS header (A13:F13) - Dark blue merged
            requests.append(
                {
                    "mergeCells": {
                        "range": {
                            "sheetId": exec_sheet_id,
                            "startRowIndex": 12,
                            "endRowIndex": 13,
                            "startColumnIndex": 0,
                            "endColumnIndex": 6,
                        },
                        "mergeType": "MERGE_ALL",
                    }
                }
            )
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": exec_sheet_id,
                            "startRowIndex": 12,
                            "endRowIndex": 13,
                            "startColumnIndex": 0,
                            "endColumnIndex": 6,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.12,
                                    "green": 0.31,
                                    "blue": 0.47,
                                },
                                "textFormat": {
                                    "bold": True,
                                    "foregroundColor": {
                                        "red": 1,
                                        "green": 1,
                                        "blue": 1,
                                    },
                                },
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat)",
                    }
                }
            )

            # Insights rows (A14:F17) - Merged
            for row_idx in range(13, 17):
                requests.append(
                    {
                        "mergeCells": {
                            "range": {
                                "sheetId": exec_sheet_id,
                                "startRowIndex": row_idx,
                                "endRowIndex": row_idx + 1,
                                "startColumnIndex": 0,
                                "endColumnIndex": 6,
                            },
                            "mergeType": "MERGE_ALL",
                        }
                    }
                )

            # Column widths
            requests.extend(
                [
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": exec_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 0,
                                "endIndex": 1,
                            },
                            "properties": {"pixelSize": 150},
                            "fields": "pixelSize",
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": exec_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 1,
                                "endIndex": 2,
                            },
                            "properties": {"pixelSize": 115},
                            "fields": "pixelSize",
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": exec_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 2,
                                "endIndex": 6,
                            },
                            "properties": {"pixelSize": 115},
                            "fields": "pixelSize",
                        }
                    },
                ]
            )

        # ============================================
        # 2. COMPLETE ABC ANALYSIS FORMATTING
        # ============================================
        if "Complete ABC Analysis" in sheets_info:
            complete_sheet_id = sheets_info["Complete ABC Analysis"]

            # Header row - Blue with white text
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": complete_sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 10,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.27,
                                    "green": 0.45,
                                    "blue": 0.77,
                                },
                                "textFormat": {
                                    "bold": True,
                                    "foregroundColor": {
                                        "red": 1,
                                        "green": 1,
                                        "blue": 1,
                                    },
                                },
                                "horizontalAlignment": "CENTER",
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
                    }
                }
            )

            # Column widths
            requests.extend(
                [
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": complete_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 0,
                                "endIndex": 1,
                            },
                            "properties": {"pixelSize": 60},
                            "fields": "pixelSize",
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": complete_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 1,
                                "endIndex": 2,
                            },
                            "properties": {"pixelSize": 90},
                            "fields": "pixelSize",
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": complete_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 2,
                                "endIndex": 3,
                            },
                            "properties": {"pixelSize": 380},
                            "fields": "pixelSize",
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": complete_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 3,
                                "endIndex": 10,
                            },
                            "properties": {"pixelSize": 90},
                            "fields": "pixelSize",
                        }
                    },
                ]
            )

        # ============================================
        # 3. CLASS A ITEMS FORMATTING
        # ============================================
        if "Class A Items" in sheets_info:
            class_a_sheet_id = sheets_info["Class A Items"]

            # Title row - Dark green merged
            requests.append(
                {
                    "mergeCells": {
                        "range": {
                            "sheetId": class_a_sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 10,
                        },
                        "mergeType": "MERGE_ALL",
                    }
                }
            )
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": class_a_sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 10,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.44,
                                    "green": 0.68,
                                    "blue": 0.28,
                                },
                                "textFormat": {
                                    "bold": True,
                                    "foregroundColor": {
                                        "red": 1,
                                        "green": 1,
                                        "blue": 1,
                                    },
                                    "fontSize": 12,
                                },
                                "horizontalAlignment": "CENTER",
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
                    }
                }
            )

            # Header row - Light green
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": class_a_sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": 2,
                            "startColumnIndex": 0,
                            "endColumnIndex": 10,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.78,
                                    "green": 0.94,
                                    "blue": 0.81,
                                },
                                "textFormat": {"bold": True},
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat)",
                    }
                }
            )

            # Column widths (same as Complete)
            requests.extend(
                [
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": class_a_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 0,
                                "endIndex": 1,
                            },
                            "properties": {"pixelSize": 60},
                            "fields": "pixelSize",
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": class_a_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 1,
                                "endIndex": 2,
                            },
                            "properties": {"pixelSize": 90},
                            "fields": "pixelSize",
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": class_a_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 2,
                                "endIndex": 3,
                            },
                            "properties": {"pixelSize": 380},
                            "fields": "pixelSize",
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": class_a_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 3,
                                "endIndex": 10,
                            },
                            "properties": {"pixelSize": 90},
                            "fields": "pixelSize",
                        }
                    },
                ]
            )

        # ============================================
        # 4. CLASS B ITEMS FORMATTING
        # ============================================
        if "Class B Items" in sheets_info:
            class_b_sheet_id = sheets_info["Class B Items"]

            # Title row - Orange merged
            requests.append(
                {
                    "mergeCells": {
                        "range": {
                            "sheetId": class_b_sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 10,
                        },
                        "mergeType": "MERGE_ALL",
                    }
                }
            )
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": class_b_sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 10,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": 1, "green": 0.75, "blue": 0},
                                "textFormat": {"bold": True, "fontSize": 12},
                                "horizontalAlignment": "CENTER",
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
                    }
                }
            )

            # Header row - Light yellow
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": class_b_sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": 2,
                            "startColumnIndex": 0,
                            "endColumnIndex": 10,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 1,
                                    "green": 0.92,
                                    "blue": 0.61,
                                },
                                "textFormat": {"bold": True},
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat)",
                    }
                }
            )

            # Column widths
            requests.extend(
                [
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": class_b_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 0,
                                "endIndex": 1,
                            },
                            "properties": {"pixelSize": 60},
                            "fields": "pixelSize",
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": class_b_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 1,
                                "endIndex": 2,
                            },
                            "properties": {"pixelSize": 90},
                            "fields": "pixelSize",
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": class_b_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 2,
                                "endIndex": 3,
                            },
                            "properties": {"pixelSize": 380},
                            "fields": "pixelSize",
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": class_b_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 3,
                                "endIndex": 10,
                            },
                            "properties": {"pixelSize": 90},
                            "fields": "pixelSize",
                        }
                    },
                ]
            )

        # ============================================
        # 5. CLASS C ITEMS FORMATTING (if exists)
        # ============================================
        if "Class C Items" in sheets_info:
            class_c_sheet_id = sheets_info["Class C Items"]

            # Title row - Red merged
            requests.append(
                {
                    "mergeCells": {
                        "range": {
                            "sheetId": class_c_sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 10,
                        },
                        "mergeType": "MERGE_ALL",
                    }
                }
            )
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": class_c_sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 10,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 1,
                                    "green": 0.78,
                                    "blue": 0.81,
                                },
                                "textFormat": {"bold": True, "fontSize": 12},
                                "horizontalAlignment": "CENTER",
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
                    }
                }
            )

            # Header row - Light red
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": class_c_sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": 2,
                            "startColumnIndex": 0,
                            "endColumnIndex": 10,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 1,
                                    "green": 0.78,
                                    "blue": 0.81,
                                },
                                "textFormat": {"bold": True},
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat)",
                    }
                }
            )

            # Column widths
            requests.extend(
                [
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": class_c_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 0,
                                "endIndex": 1,
                            },
                            "properties": {"pixelSize": 60},
                            "fields": "pixelSize",
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": class_c_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 1,
                                "endIndex": 2,
                            },
                            "properties": {"pixelSize": 90},
                            "fields": "pixelSize",
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": class_c_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 2,
                                "endIndex": 3,
                            },
                            "properties": {"pixelSize": 380},
                            "fields": "pixelSize",
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": class_c_sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 3,
                                "endIndex": 10,
                            },
                            "properties": {"pixelSize": 90},
                            "fields": "pixelSize",
                        }
                    },
                ]
            )

        # Execute all formatting requests
        body = {"requests": requests}
        service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=body).execute()

        print(f"✅ Applied formatting to {len(sheets_info)} sheets")

        return {
            "success": True,
            "sheets_formatted": list(sheets_info.keys()),
            "total_requests": len(requests),
        }

    except Exception as e:
        print(f"❌ Formatting error: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


def check_dates_have_data(
    sheet_id: str,
    dates_to_check: List[str],
    sheet_name: str = "DATA ENTRY",
    credentials_dict: Optional[CredentialsDict] = None,
) -> Dict[str, Any]:
    """
    Check if specific dates already have data in the sheet

    Args:
        sheet_id: Google Sheets ID
        dates_to_check: List of dates to check (format: 'dd-MMM-yy' or 'YYYY-MM-DD')
        sheet_name: Name of the sheet (default: "DATA ENTRY")
        credentials_dict: Google OAuth credentials

    Returns:
        Dictionary with:
        - has_data: bool (any dates have data)
        - dates_with_data: list of dates that have data
        - dates_without_data: list of dates that don't have data
        - conflicting_rows: list of row details that will be overwritten
    """
    try:
        if not credentials_dict:
            return {"success": False, "error": "Credentials required"}

        service = create_sheets_service(credentials_dict)

        print(f"\n🔍 Checking dates in sheet '{sheet_name}'...")
        print(f"   Dates to check: {len(dates_to_check)}")

        # Read the entire sheet
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range=f"{sheet_name}")  # ✅ Reads ALL columns
            .execute()
        )

        values = result.get("values", [])

        if len(values) <= 1:
            # Only header or empty
            return {
                "success": True,
                "result": {
                    "has_data": False,
                    "dates_with_data": [],
                    "dates_without_data": dates_to_check,
                    "conflicting_rows": [],
                    "total_conflicts": 0,
                    "total_safe": len(dates_to_check),
                    "message": "Sheet is empty, no conflicts",
                },
            }

        # Build map of dates in sheet
        from datetime import datetime

        existing_dates = {}

        print(f"   Scanning {len(values) - 1} rows in sheet...")

        for row_idx, row in enumerate(
            values[1:], start=2
        ):  # Start from row 2 (skip header)
            if not row or len(row) == 0:
                continue

            date_value = str(row[0]).strip()
            if not date_value:
                continue

            # Try to parse the date
            date_normalized = None
            for fmt in ["%d-%b-%y", "%d-%b-%Y", "%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    parsed_date = datetime.strptime(date_value, fmt)
                    date_normalized = parsed_date.strftime("%d-%b-%y")
                    break
                except ValueError:
                    continue

            if not date_normalized:
                continue

            # Check if row has any data (not just date)
            has_data_in_row = any(str(cell).strip() for cell in row[1:] if cell)
            non_empty_cells = sum(1 for cell in row[1:] if cell and str(cell).strip())

            existing_dates[date_normalized] = {
                "row_number": row_idx,
                "has_data": has_data_in_row,
                "non_empty_cells": non_empty_cells,
                "row_data_sample": [
                    str(cell)[:30] for cell in row[1:6] if cell
                ],  # First 5 data columns
            }

        print(f"   ✓ Found {len(existing_dates)} dates with valid data in sheet")

        # Check which dates from upload exist in sheet
        dates_with_data = []
        dates_without_data = []
        conflicting_rows = []

        for upload_date in dates_to_check:
            # Normalize upload date
            upload_date_normalized = None
            for fmt in ["%Y-%m-%d", "%d-%b-%y", "%d-%b-%Y", "%m/%d/%Y"]:
                try:
                    parsed = datetime.strptime(str(upload_date), fmt)
                    upload_date_normalized = parsed.strftime("%d-%b-%y")
                    break
                except ValueError:
                    continue

            if not upload_date_normalized:
                # Can't parse date, treat as safe
                dates_without_data.append(upload_date)
                continue

            if upload_date_normalized in existing_dates:
                date_info = existing_dates[upload_date_normalized]

                if date_info["has_data"]:
                    # This date has actual data, will be overwritten
                    dates_with_data.append(upload_date)
                    conflicting_rows.append(
                        {
                            "date": upload_date,
                            "row_number": date_info["row_number"],
                            "non_empty_cells": date_info["non_empty_cells"],
                            "sample_data": date_info["row_data_sample"],
                        }
                    )
                else:
                    # Date exists but row is empty (only date cell filled)
                    dates_without_data.append(upload_date)
            else:
                # Date doesn't exist at all
                dates_without_data.append(upload_date)

        has_conflicts = len(dates_with_data) > 0

        print(f"   Conflicts: {len(dates_with_data)}")
        print(f"   Safe dates: {len(dates_without_data)}")

        return {
            "success": True,
            "result": {
                "has_data": has_conflicts,
                "dates_with_data": dates_with_data,
                "dates_without_data": dates_without_data,
                "conflicting_rows": conflicting_rows,
                "total_conflicts": len(conflicting_rows),
                "total_safe": len(dates_without_data),
                "message": f"Found {len(conflicting_rows)} dates with existing data, {len(dates_without_data)} dates are safe to upload",
            },
        }

    except HttpError as e:
        return {"success": False, "error": f"Google Sheets API error: {str(e)}"}
    except Exception as e:
        print(f"❌ Error checking dates: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": f"Failed to check dates: {str(e)}"}


@monitor_task("sheets_agent", "check_dates_and_columns_have_data")
def check_dates_and_columns_have_data(
    sheet_id: str,
    dates_to_check: List[str],
    columns_to_check: List[str],
    sheet_name: str = "DATA ENTRY",
    credentials_dict: Optional[CredentialsDict] = None,
) -> Dict[str, Any]:
    """
    ✅ FIXED: Check if specific dates AND specific columns already have data

    This version properly handles:
    - Wide column ranges (yellow CH-CU, purple CW-DJ, etc.)
    - Correctly maps column names to indices
    - Reads the FULL row width to avoid truncation
    """
    try:
        if not credentials_dict:
            return {"success": False, "error": "Credentials required"}

        service = create_sheets_service(credentials_dict)

        print(f"\n🔍 FIXED: Checking dates AND columns in sheet '{sheet_name}'...")
        print(f"   Dates to check: {len(dates_to_check)}")
        print(f"   Columns to check: {len(columns_to_check)}")
        if columns_to_check:
            print(f"   First 3 columns: {columns_to_check[:3]}")
            print(f"   Last 3 columns: {columns_to_check[-3:]}")

        # ============================================================
        # FIX #1: Read with EXPLICIT wide range to avoid truncation
        # ============================================================
        # Instead of just f"{sheet_name}", use A:DZ to force reading all columns
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=sheet_id,
                range=f"{sheet_name}!A:DZ",  # ✅ FIXED: Explicit wide range
            )
            .execute()
        )

        values = result.get("values", [])

        if len(values) <= 1:
            return {
                "success": True,
                "result": {
                    "has_data": False,
                    "dates_with_data": [],
                    "dates_without_data": dates_to_check,
                    "conflicting_cells": [],
                    "total_conflicts": 0,
                    "total_safe": len(dates_to_check),
                    "message": "Sheet is empty, no conflicts",
                },
            }

        # ============================================================
        # FIX #2: Build column name → index map WITH normalization
        # ============================================================
        header_row = values[0]
        column_map = {}  # normalized_name → index
        column_map_original = {}  # normalized_name → original_name

        print(f"\n📋 Sheet has {len(header_row)} columns")

        for idx, col_name in enumerate(header_row):
            normalized = normalize_column_name(col_name)
            column_map[normalized] = idx
            column_map_original[normalized] = col_name

        # ============================================================
        # FIX #3: Map the columns we're checking to sheet indices
        # ============================================================
        mapped_column_indices = []
        mapped_column_info = []  # For detailed reporting
        missing_columns = []

        print(f"\n🗺️ Mapping {len(columns_to_check)} columns to sheet:")

        for col_name in columns_to_check:
            normalized = normalize_column_name(col_name)

            if normalized in column_map:
                col_idx = column_map[normalized]
                col_letter = column_index_to_letter(col_idx)
                mapped_column_indices.append(col_idx)
                mapped_column_info.append(
                    {
                        "name": col_name,
                        "index": col_idx,
                        "letter": col_letter,
                    }
                )

                # Show first 10 mappings
                if len(mapped_column_indices) <= 10:
                    print(f"   ✓ [{col_letter:3}] {col_name[:50]}")
            else:
                missing_columns.append(col_name)
                if len(missing_columns) <= 5:
                    print(f"   ✗ NOT FOUND: {col_name[:50]}")

        if len(mapped_column_indices) > 10:
            print(f"   ... and {len(mapped_column_indices) - 10} more columns")

        if missing_columns:
            print(f"\n⚠️ {len(missing_columns)} columns not found in sheet")

        if not mapped_column_indices:
            return {
                "success": False,
                "error": f"None of the mapped columns found. Missing: {missing_columns[:5]}",
            }

        print(f"\n✅ Successfully mapped {len(mapped_column_indices)} columns")
        print(
            f"   Column range: {mapped_column_info[0]['letter']} to {mapped_column_info[-1]['letter']}"
        )

        # ============================================================
        # FIX #4: Find date column index
        # ============================================================
        date_col_normalized = normalize_column_name("Date")
        if date_col_normalized not in column_map:
            return {"success": False, "error": "Date column not found"}

        date_col_idx = column_map[date_col_normalized]
        print(f"   Date column: Index {date_col_idx}")

        # ============================================================
        # FIX #5: Scan sheet rows - Check ONLY mapped columns for data
        # ============================================================
        from datetime import datetime

        date_to_row_data = {}

        print(f"\n🔄 Scanning {len(values) - 1} rows for conflicts...")

        for row_idx, row_data in enumerate(values[1:], start=2):  # Start from row 2
            if not row_data or len(row_data) == 0:
                continue

            # Get date value
            date_value = (
                str(row_data[date_col_idx]).strip()
                if date_col_idx < len(row_data)
                else ""
            )
            if not date_value:
                continue

            # Parse and normalize date
            date_normalized = None
            for fmt in [
                "%d-%b-%y",
                "%d-%b-%Y",
                "%m/%d/%Y",
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%Y-%m-%d %H:%M:%S",
            ]:
                try:
                    parsed_date = datetime.strptime(date_value, fmt)
                    date_normalized = parsed_date.strftime("%d-%b-%y")
                    break
                except ValueError:
                    continue

            if not date_normalized:
                continue

            # ============================================================
            # ✅ CRITICAL FIX: Check ONLY the mapped columns
            # Handle cases where row is shorter than expected
            # ============================================================
            mapped_cells_with_data = []

            for col_info in mapped_column_info:
                col_idx = col_info["index"]

                # ✅ CRITICAL: Handle rows shorter than expected
                if col_idx >= len(row_data):
                    continue  # This cell doesn't exist in this row

                cell_value = str(row_data[col_idx]).strip()

                # Filter out empty/null values
                if cell_value and cell_value.lower() not in [
                    "",
                    "nan",
                    "none",
                    "null",
                    "#n/a",
                ]:
                    # Special handling for numeric zeros
                    try:
                        if float(cell_value) == 0.0:
                            continue  # Treat 0 as empty
                    except:
                        pass

                    mapped_cells_with_data.append(
                        {
                            "column": col_info["name"],
                            "value": cell_value[:50],  # Truncate long values
                            "col_letter": col_info["letter"],
                            "col_index": col_idx,
                        }
                    )

            # Debug: Show first 3 rows with conflicts
            if len([d for d in date_to_row_data.values() if d["has_mapped_data"]]) < 3:
                if len(mapped_cells_with_data) > 0:
                    print(f"\n   ⚠️ Conflict Row {row_idx} ({date_normalized}):")
                    print(f"      {len(mapped_cells_with_data)} cells have data:")
                    for cell in mapped_cells_with_data[:5]:
                        print(
                            f"         • {cell['col_letter']}{row_idx}: {cell['column'][:40]} = '{cell['value']}'"
                        )
                    if len(mapped_cells_with_data) > 5:
                        print(
                            f"         ... and {len(mapped_cells_with_data) - 5} more"
                        )

            # Store row data
            date_to_row_data[date_normalized] = {
                "row_number": row_idx,
                "has_mapped_data": len(mapped_cells_with_data) > 0,
                "cells_with_data": mapped_cells_with_data,
                "total_mapped_cells": len(mapped_cells_with_data),
            }

        total_dates_in_sheet = len(date_to_row_data)
        dates_with_conflicts = sum(
            1 for d in date_to_row_data.values() if d["has_mapped_data"]
        )

        print(f"\n   ✓ Scanned {total_dates_in_sheet} dates in sheet")
        print(f"   ✓ {dates_with_conflicts} dates have data in mapped columns")
        print(
            f"   ✓ {total_dates_in_sheet - dates_with_conflicts} dates have empty mapped columns"
        )

        # ============================================================
        # FIX #6: Check which upload dates conflict
        # ============================================================
        dates_with_data = []
        dates_without_data = []
        conflicting_cells = []

        print(f"\n🔍 Checking {len(dates_to_check)} upload dates...")

        for upload_date in dates_to_check:
            # Normalize upload date
            upload_date_normalized = None
            for fmt in [
                "%Y-%m-%d",
                "%d-%b-%y",
                "%d-%b-%Y",
                "%m/%d/%Y",
                "%Y-%m-%d %H:%M:%S",
            ]:
                try:
                    parsed = datetime.strptime(str(upload_date), fmt)
                    upload_date_normalized = parsed.strftime("%d-%b-%y")
                    break
                except ValueError:
                    continue

            if not upload_date_normalized:
                # Can't parse date, treat as safe
                dates_without_data.append(upload_date)
                continue

            if upload_date_normalized in date_to_row_data:
                row_data = date_to_row_data[upload_date_normalized]

                if row_data["has_mapped_data"]:
                    # CONFLICT! Mapped columns have data
                    dates_with_data.append(upload_date)
                    conflicting_cells.append(
                        {
                            "date": upload_date,
                            "row_number": row_data["row_number"],
                            "affected_columns": [
                                cell["column"] for cell in row_data["cells_with_data"]
                            ],
                            "sample_values": row_data["cells_with_data"][
                                :3
                            ],  # Show first 3
                            "total_cells": row_data["total_mapped_cells"],
                        }
                    )
                else:
                    # Date exists but mapped columns empty - SAFE
                    dates_without_data.append(upload_date)
            else:
                # Date doesn't exist - SAFE
                dates_without_data.append(upload_date)

        has_conflicts = len(dates_with_data) > 0

        print(f"\n📊 RESULTS:")
        print(f"   ⚠️ Conflicts: {len(dates_with_data)}")
        print(f"   ✅ Safe: {len(dates_without_data)}")

        # Show sample conflicts
        if conflicting_cells:
            print(f"\n   Sample conflicts:")
            for conflict in conflicting_cells[:3]:
                affected = conflict["affected_columns"]
                print(
                    f"      • {conflict['date']} (Row {conflict['row_number']}): {len(affected)} cells"
                )
                print(f"        {', '.join(affected[:3])}")
                if len(affected) > 3:
                    print(f"        ... and {len(affected) - 3} more")

        return {
            "success": True,
            "result": {
                "has_data": has_conflicts,
                "dates_with_data": dates_with_data,
                "dates_without_data": dates_without_data,
                "conflicting_cells": conflicting_cells,
                "total_conflicts": len(conflicting_cells),
                "total_safe": len(dates_without_data),
                "mapped_columns_checked": [info["name"] for info in mapped_column_info],
                "column_range": (
                    f"{mapped_column_info[0]['letter']} to {mapped_column_info[-1]['letter']}"
                    if mapped_column_info
                    else "N/A"
                ),
                "message": (
                    f"Found {len(conflicting_cells)} dates where mapped columns have data, "
                    f"{len(dates_without_data)} dates are safe to upload"
                ),
            },
        }

    except HttpError as e:
        print(f"❌ Google Sheets API error: {str(e)}")
        return {"success": False, "error": f"Google Sheets API error: {str(e)}"}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return {
            "success": False,
            "error": f"Failed to check dates and columns: {str(e)}",
        }


def find_rows_by_dates(
    sheet_id: str,
    dates_to_find: List[str],
    sheet_name: str = "DATA ENTRY",
    date_column: str = "Date",
    credentials_dict: Optional[CredentialsDict] = None,
) -> Dict[str, Any]:
    try:
        if not credentials_dict:
            return {"success": False, "error": "Credentials required"}

        service = create_sheets_service(credentials_dict)

        print(f"\n📅 Finding rows for {len(dates_to_find)} dates...")
        print(f"   Sheet: '{sheet_name}'")
        print(f"   Looking for column: '{date_column}'")

        # ✅ FIX: Read the HEADER first to find the Date column
        header_result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=sheet_id,
                range=f"{sheet_name}!1:1",
                valueRenderOption="FORMATTED_VALUE",
            )
            .execute()
        )

        header_row = header_result.get("values", [[]])[0]

        print(f"   📋 Sheet has {len(header_row)} columns in header")
        print(f"   First 5 headers: {header_row[:5]}")

        # Find Date column index
        date_col_idx = None
        for idx, col_name in enumerate(header_row):
            normalized = normalize_column_name(col_name)
            if normalized == normalize_column_name(date_column):
                date_col_idx = idx
                date_col_letter = column_index_to_letter(idx)
                break

        if date_col_idx is None:
            print(f"   ❌ Date column '{date_column}' not found!")
            print(f"   Available columns: {header_row}")
            return {"success": False, "error": f"Date column '{date_column}' not found"}

        print(
            f"   ✓ Found Date column at index {date_col_idx} (Column {date_col_letter})"
        )

        # ✅ FIX: Read the CORRECT date column
        print(f"   📖 Reading column {date_col_letter}...")
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=sheet_id,
                range=f"{sheet_name}!{date_col_letter}:{date_col_letter}",
                valueRenderOption="FORMATTED_VALUE",
            )
            .execute()
        )

        values = result.get("values", [])

        print(f"   📊 Read {len(values)} rows from column {date_col_letter}")

        if len(values) <= 1:
            print(f"   ⚠️ Only header row found, no data")
            return {
                "success": True,
                "date_to_row": {},
                "dates_found": [],
                "dates_not_found": dates_to_find,
                "message": "Sheet is empty",
            }

        # Build date → row mapping
        from datetime import datetime

        date_to_row = {}

        # Parse all dates in sheet (skip header)
        print(f"   🔍 Parsing dates from rows 2 to {len(values)}...")

        dates_parsed = 0
        dates_failed = 0

        for row_idx, row in enumerate(values[1:], start=2):
            if not row or len(row) == 0:
                continue

            date_value = row[0]
            if not date_value or (
                isinstance(date_value, str) and not date_value.strip()
            ):
                continue

            # Show first 5 dates for debugging
            if row_idx <= 6:
                print(
                    f"      Row {row_idx}: '{date_value}' (type: {type(date_value).__name__})",
                    end="",
                )

            # Normalize date from Google Sheets
            date_normalized = None

            # Handle different date formats from Google Sheets
            if isinstance(date_value, datetime):
                # Already a datetime object
                date_normalized = date_value.strftime("%Y-%m-%d")
                if row_idx <= 6:
                    print(f" → {date_normalized} (datetime object)")
            else:
                # Try string parsing
                date_value_str = str(date_value).strip()
                for fmt in [
                    "%d-%b-%y",  # 01-Jul-25
                    "%d-%b-%Y",  # 01-Jul-2025
                    "%m/%d/%Y",  # 07/01/2025
                    "%Y-%m-%d",  # 2025-07-01
                    "%d/%m/%Y",  # 01/07/2025
                    "%Y-%m-%d %H:%M:%S",  # 2025-07-01 00:00:00
                ]:
                    try:
                        parsed = datetime.strptime(date_value_str, fmt)
                        date_normalized = parsed.strftime("%Y-%m-%d")
                        if row_idx <= 6:
                            print(f" → {date_normalized} (parsed with {fmt})")
                        break
                    except:
                        continue

            if date_normalized:
                date_to_row[date_normalized] = row_idx
                dates_parsed += 1
            else:
                dates_failed += 1
                if row_idx <= 6:
                    print(f" → FAILED TO PARSE")

        print(f"   ✓ Successfully parsed {dates_parsed} dates")
        if dates_failed > 0:
            print(f"   ✗ Failed to parse {dates_failed} dates")

        # Show sample of parsed dates
        if date_to_row:
            sample_dates = list(date_to_row.keys())[:5]
            print(f"   Sample dates: {sample_dates}")

        # Check which dates from upload exist
        print(f"\n   🔎 Checking which upload dates exist...")
        dates_found = []
        dates_not_found = []

        for upload_date in dates_to_find:
            # Normalize upload date
            upload_normalized = None
            for fmt in ["%Y-%m-%d", "%d-%b-%y", "%d-%b-%Y"]:
                try:
                    parsed = datetime.strptime(str(upload_date), fmt)
                    upload_normalized = parsed.strftime("%Y-%m-%d")
                    break
                except:
                    continue

            if upload_normalized and upload_normalized in date_to_row:
                dates_found.append(upload_date)
            else:
                dates_not_found.append(upload_date)

        print(f"   ✓ Matched: {len(dates_found)} dates")
        print(f"   ✗ Not found: {len(dates_not_found)} dates")

        if dates_not_found:
            print(f"   First 3 missing: {dates_not_found[:3]}")

        return {
            "success": True,
            "date_to_row": date_to_row,
            "dates_found": dates_found,
            "dates_not_found": dates_not_found,
            "total_dates_in_sheet": len(date_to_row),
            "message": f"Found {len(dates_found)} of {len(dates_to_find)} dates",
        }

    except Exception as e:
        print(f"❌ Error finding dates: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


def check_specific_cells_have_data(
    sheet_id: str,
    row_numbers: List[int],
    column_names: List[str],
    sheet_name: str = "DATA ENTRY",
    credentials_dict: Optional[CredentialsDict] = None,
) -> Dict[str, Any]:
    """
    STEP 2: Check if specific cells (row + column combinations) have data

    This is FOCUSED on just checking cells - no date logic!

    Args:
        sheet_id: Google Sheets ID
        row_numbers: List of row numbers to check (e.g., [2, 5, 10])
        column_names: List of column names to check in those rows
        sheet_name: Sheet name
        credentials_dict: Google OAuth credentials

    Returns:
        Detailed report of which cells have data
    """
    try:
        if not credentials_dict:
            return {"success": False, "error": "Credentials required"}

        service = create_sheets_service(credentials_dict)

        print(f"\n🔍 Checking {len(row_numbers)} rows × {len(column_names)} columns...")

        # Read header to map column names
        header_result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range=f"{sheet_name}!1:1")
            .execute()
        )

        header_row = header_result.get("values", [[]])[0]

        # Build column map with normalization
        column_map = {}
        for idx, col_name in enumerate(header_row):
            normalized = normalize_column_name(col_name)
            column_map[normalized] = {
                "index": idx,
                "letter": column_index_to_letter(idx),
                "original_name": col_name,
            }

        # Map requested columns to indices
        columns_to_check = []
        missing_columns = []

        for col_name in column_names:
            normalized = normalize_column_name(col_name)
            if normalized in column_map:
                columns_to_check.append({"name": col_name, **column_map[normalized]})
            else:
                missing_columns.append(col_name)

        if missing_columns:
            print(f"   ⚠️  {len(missing_columns)} columns not found")

        if not columns_to_check:
            return {
                "success": False,
                "error": f"None of the columns found. Missing: {missing_columns[:5]}",
            }

        print(f"   ✓ Mapped {len(columns_to_check)} columns")
        print(
            f"   ✓ Column range: {columns_to_check[0]['letter']} to {columns_to_check[-1]['letter']}"
        )

        # Read the full sheet data (with wide range)
        data_result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=sheet_id,
                range=f"{sheet_name}!A:DZ",
                valueRenderOption="FORMATTED_VALUE",  # ✅ Get evaluated formula results
            )
            .execute()
        )

        all_rows = data_result.get("values", [])

        # Check each row + column combination
        rows_with_data = []
        rows_without_data = []

        for row_num in row_numbers:
            if row_num > len(all_rows):
                rows_without_data.append(
                    {"row_number": row_num, "reason": "Row doesn't exist in sheet"}
                )
                continue

            row_data = all_rows[row_num - 1]  # Convert to 0-indexed

            # Check cells in this row
            cells_with_data = []

            for col_info in columns_to_check:
                col_idx = col_info["index"]

                # Get cell value
                if col_idx >= len(row_data):
                    cell_value = None
                else:
                    cell_value = row_data[col_idx]

                # ✅ FIXED LOGIC: Check if cell has data
                has_data = False

                if cell_value is not None and cell_value != "":
                    cell_str = str(cell_value).strip()
                    # Only skip these specific error values
                    if cell_str.lower() not in [
                        "nan",
                        "none",
                        "null",
                        "#n/a",
                        "#value!",
                        "#ref!",
                        "#div/0!",
                    ]:
                        has_data = True
                        # ✅ ZEROS ARE VALID DATA!

                if has_data:
                    cells_with_data.append(
                        {
                            "column": col_info["name"],
                            "column_letter": col_info["letter"],
                            "value": str(cell_value)[:50],
                            "cell_address": f"{col_info['letter']}{row_num}",
                        }
                    )

            # Classify this row
            if len(cells_with_data) > 0:
                rows_with_data.append(
                    {
                        "row_number": row_num,
                        "cells_with_data": cells_with_data,
                        "total_cells": len(cells_with_data),
                    }
                )
            else:
                rows_without_data.append(
                    {"row_number": row_num, "reason": "All mapped columns are empty"}
                )

        # Summary
        has_conflicts = len(rows_with_data) > 0

        print(f"\n   📊 Results:")
        print(f"      Rows WITH data:    {len(rows_with_data)}")
        print(f"      Rows WITHOUT data: {len(rows_without_data)}")

        # Show sample conflicts
        if rows_with_data:
            print(f"\n   Sample rows with data:")
            for row in rows_with_data[:3]:
                print(
                    f"      Row {row['row_number']}: {row['total_cells']} cells have data"
                )
                for cell in row["cells_with_data"][:3]:
                    print(
                        f"         • {cell['cell_address']}: {cell['column'][:30]} = '{cell['value']}'"
                    )

        return {
            "success": True,
            "has_data": has_conflicts,
            "rows_with_data": rows_with_data,
            "rows_without_data": rows_without_data,
            "total_conflicts": len(rows_with_data),
            "total_safe": len(rows_without_data),
            "columns_checked": [col["name"] for col in columns_to_check],
            "message": f"Found {len(rows_with_data)} rows with data in mapped columns",
        }

    except Exception as e:
        print(f"❌ Error checking cells: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


# ============================================================
# TOOL REGISTRY
# ============================================================
TOOL_REGISTRY = {
    "create_sheet": {
        "func": create_sheet,
        "description": "Create a new Google Spreadsheet",
    },
    "read_sheet": {"func": read_sheet, "description": "Read data from a Google Sheet"},
    "update_sheet": {
        "func": update_sheet,
        "description": "Update data in a specific range",
    },
    "append_rows": {
        "func": append_rows,
        "description": "Append rows to the end of a sheet",
    },
    "upload_mapped_data": {
        "func": upload_mapped_data,
        "description": "Upload pre-transformed data from mapping agent",
    },
    "get_sheet_metadata": {
        "func": get_sheet_metadata,
        "description": "Get spreadsheet metadata (sheets, row counts)",
    },
    "clear_sheet": {
        "func": clear_sheet,
        "description": "Clear data from a sheet range",
    },
    "check_sheet_has_data": {
        "func": check_sheet_has_data,
        "description": "Check if sheet has existing data before upload",
    },
    "check_dates_have_data": {
        "func": check_dates_have_data,
        "description": "Check if specific dates already have data in the sheet",
    },
    "check_dates_and_columns_have_data": {  # ✅ FIXED: Properly structured now
        "func": check_dates_and_columns_have_data,
        "description": "Check if specific dates AND columns already have data in the sheet",
    },
    "update_by_date_match": {
        "func": update_by_date_match,
        "description": "Update Google Sheets rows by matching dates (no append, only update)",
    },
    "upload_multi_sheet_data": {  # ✅ FIXED: Moved out of nested structure
        "func": upload_multi_sheet_data,
        "description": "Upload data to multiple sheets at once",
    },
    "apply_sheet_formatting": {
        "func": apply_sheet_formatting,
        "description": "Apply ABC Analysis formatting (colors, fonts, merged cells) to sheets",
    },
    "find_rows_by_dates": {
        "func": find_rows_by_dates,
        "description": "Find which row numbers contain specific dates",
    },
    "check_specific_cells_have_data": {
        "func": check_specific_cells_have_data,
        "description": "Check if specific cells (row + column combinations) have data",
    },
}


# ============================================================
# API ENDPOINTS
# ============================================================


@app.post("/execute_task", response_model=ToolResponse)
async def execute_tool(request: ToolRequest):
    """
    Execute a Google Sheets tool

    Request body:
        - tool: Name of the tool to execute
        - inputs: Dictionary of tool inputs
        - credentials_dict: Google OAuth credentials

    Returns:
        ToolResponse with success status and result/error
    """
    try:
        print(f"\n📊 Sheets Agent - Tool: {request.tool}")
        print(f"   Inputs: {list(request.inputs.keys())}")

        # Get tool from registry
        tool_info = TOOL_REGISTRY.get(request.tool)
        if not tool_info:
            available_tools = list(TOOL_REGISTRY.keys())
            return ToolResponse(
                success=False,
                error=f"Unknown tool: {request.tool}. Available: {available_tools}",
            )

        # Add credentials to inputs
        request.inputs["credentials_dict"] = request.credentials_dict

        # Execute tool
        result = tool_info["func"](**request.inputs)

        print(
            f"   {'✅' if result.get('success') else '❌'} Result: {result.get('success', False)}"
        )

        return ToolResponse(
            success=result.get("success", False),
            result=result if result.get("success") else None,
            error=result.get("error") if not result.get("success") else None,
        )

    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return ToolResponse(
            success=False,
            error=f"Tool execution failed: {str(e)}",
        )


@app.get("/tools")
async def list_tools():
    """List all available tools"""
    return {
        "tools": [
            {"name": name, "description": info["description"]}
            for name, info in TOOL_REGISTRY.items()
        ],
        "count": len(TOOL_REGISTRY),
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "google-sheets-agent",
        "version": "2.0.0",
        "description": "Pure CRUD operations for Google Sheets",
    }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Google Sheets Agent API",
        "version": "2.0.0",
        "description": "Pure CRUD operations for Google Sheets (no parsing/mapping)",
        "features": [
            "Create spreadsheets",
            "Read sheet data",
            "Update ranges",
            "Append rows",
            "Upload pre-mapped data",
            "Get metadata",
            "Clear sheets",
        ],
        "endpoints": {
            "execute": "/execute (POST) - Execute a sheets tool",
            "tools": "/tools (GET) - List available tools",
            "health": "/health (GET) - Health check",
            "docs": "/docs (GET) - Swagger documentation",
        },
        "note": "Works with pre-transformed data from Mapping Agent",
    }


# Run the server
if __name__ == "__main__":
    port = int(os.getenv("SHEETS_AGENT_PORT", "8003"))
    print(f"🚀 Starting Google Sheets Agent (v2.0 - Pure CRUD) on port {port}")
    print(f"📚 API Documentation: http://localhost:{port}/docs")
    print(f"🔧 Available tools: {list(TOOL_REGISTRY.keys())}")
    print(f"📝 Note: This agent works with pre-transformed data from Mapping Agent")
    uvicorn.run(app, host="0.0.0.0", port=port)
