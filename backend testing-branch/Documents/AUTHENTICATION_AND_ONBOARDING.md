# Google OAuth Authentication & User Onboarding System

## Overview

This document explains the complete authentication flow, user creation process, and how social accounts are linked and stored in the system. The system uses **three databases** for different purposes.

---

## 1. Database Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              THREE-DATABASE ARCHITECTURE                                 │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                     DATABASE 1: Django Default (MySQL)                           │    │
│  │                     safexpressops_local                                          │    │
│  │                                                                                  │    │
│  │  Purpose: Django's built-in authentication & AllAuth social accounts            │    │
│  │                                                                                  │    │
│  │  Tables:                                                                         │    │
│  │  ┌──────────────────────────────────────────────────────────────────────────┐   │    │
│  │  │  auth_user (Django's User model)                                         │   │    │
│  │  │  ├── id (PK)                                                              │   │    │
│  │  │  ├── username (unique)                                                    │   │    │
│  │  │  ├── email                                                                │   │    │
│  │  │  ├── first_name                                                           │   │    │
│  │  │  ├── last_name                                                            │   │    │
│  │  │  ├── password (hashed)                                                    │   │    │
│  │  │  ├── is_active                                                            │   │    │
│  │  │  ├── is_staff                                                             │   │    │
│  │  │  ├── is_superuser                                                         │   │    │
│  │  │  ├── date_joined                                                          │   │    │
│  │  │  └── last_login                                                           │   │    │
│  │  └──────────────────────────────────────────────────────────────────────────┘   │    │
│  │                                                                                  │    │
│  │  ┌──────────────────────────────────────────────────────────────────────────┐   │    │
│  │  │  socialaccount_socialapp (Google App Credentials)                        │   │    │
│  │  │  ├── id (PK)                                                              │   │    │
│  │  │  ├── provider = "google"                                                  │   │    │
│  │  │  ├── name = "Google"                                                      │   │    │
│  │  │  ├── client_id (from Google Cloud Console)                               │   │    │
│  │  │  └── secret (from Google Cloud Console)                                  │   │    │
│  │  └──────────────────────────────────────────────────────────────────────────┘   │    │
│  │                                                                                  │    │
│  │  ┌──────────────────────────────────────────────────────────────────────────┐   │    │
│  │  │  socialaccount_socialaccount (Links user to Google account)              │   │    │
│  │  │  ├── id (PK)                                                              │   │    │
│  │  │  ├── user_id (FK → auth_user.id)                                         │   │    │
│  │  │  ├── provider = "google"                                                  │   │    │
│  │  │  ├── uid (Google's unique user ID)                                       │   │    │
│  │  │  ├── extra_data (JSON: email, name, picture, etc.)                       │   │    │
│  │  │  ├── last_login                                                           │   │    │
│  │  │  └── date_joined                                                          │   │    │
│  │  └──────────────────────────────────────────────────────────────────────────┘   │    │
│  │                                                                                  │    │
│  │  ┌──────────────────────────────────────────────────────────────────────────┐   │    │
│  │  │  socialaccount_socialtoken (Stores Google OAuth tokens)                  │   │    │
│  │  │  ├── id (PK)                                                              │   │    │
│  │  │  ├── account_id (FK → socialaccount_socialaccount.id)                    │   │    │
│  │  │  ├── app_id (FK → socialaccount_socialapp.id)                            │   │    │
│  │  │  ├── token (Google access_token)                                         │   │    │
│  │  │  ├── token_secret (Google refresh_token)                                 │   │    │
│  │  │  └── expires_at (token expiration timestamp)                             │   │    │
│  │  └──────────────────────────────────────────────────────────────────────────┘   │    │
│  │                                                                                  │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                     DATABASE 2: Application Users (MySQL)                        │    │
│  │                     safexpressops_local.users                                    │    │
│  │                                                                                  │    │
│  │  Purpose: Business-specific user data (roles, departments, quotas)              │    │
│  │                                                                                  │    │
│  │  ┌──────────────────────────────────────────────────────────────────────────┐   │    │
│  │  │  users (Custom business table)                                           │   │    │
│  │  │  ├── user_id (PK, UUID)                                                   │   │    │
│  │  │  ├── email (unique)                                                       │   │    │
│  │  │  ├── name                                                                 │   │    │
│  │  │  ├── role ("admin", "manager", "user")                                   │   │    │
│  │  │  ├── department                                                           │   │    │
│  │  │  ├── warehouse                                                            │   │    │
│  │  │  ├── position                                                             │   │    │
│  │  │  ├── google_id                                                            │   │    │
│  │  │  ├── google_access_token                                                  │   │    │
│  │  │  ├── google_refresh_token                                                 │   │    │
│  │  │  ├── token_expiry                                                         │   │    │
│  │  │  ├── daily_token_limit                                                    │   │    │
│  │  │  ├── daily_request_limit                                                  │   │    │
│  │  │  ├── is_active                                                            │   │    │
│  │  │  ├── created_by                                                           │   │    │
│  │  │  └── created_at                                                           │   │    │
│  │  └──────────────────────────────────────────────────────────────────────────┘   │    │
│  │                                                                                  │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The Onboarding Problem

### Current Behavior (No Blocking)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                      CURRENT FLOW: NO ONBOARDING CHECKS                                  │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   User clicks "Login with Google"                                                        │
│           │                                                                              │
│           ▼                                                                              │
│   ┌───────────────────────────────────────────────────────────────────────┐             │
│   │  google_auth_dynamodb() in views.py                                   │             │
│   │                                                                       │             │
│   │  1. Exchange auth_code for Google tokens ✓                           │             │
│   │  2. Fetch user info (email, name, picture) ✓                         │             │
│   │  3. Create Django user if not exists ✓     ◀── AUTO-CREATE!          │             │
│   │  4. Create SocialApp if not exists ✓       ◀── AUTO-CREATE!          │             │
│   │  5. Create SocialAccount if not exists ✓   ◀── AUTO-CREATE!          │             │
│   │  6. Create/Update SocialToken ✓            ◀── AUTO-CREATE!          │             │
│   │  7. Generate JWT tokens ✓                                             │             │
│   │  8. Return success response ✓                                         │             │
│   │                                                                       │             │
│   │  ⚠️ NO CHECK: Is this email allowed to register?                      │             │
│   │  ⚠️ NO CHECK: Does this user exist in the business 'users' table?     │             │
│   │  ⚠️ NO CHECK: Has this user been onboarded/approved?                  │             │
│   │                                                                       │             │
│   └───────────────────────────────────────────────────────────────────────┘             │
│           │                                                                              │
│           ▼                                                                              │
│   ✅ ANYONE with a valid Google account can login!                                       │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### What You Want (Onboarding Check)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                      PROPOSED FLOW: WITH ONBOARDING CHECK                                │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   User clicks "Login with Google"                                                        │
│           │                                                                              │
│           ▼                                                                              │
│   ┌───────────────────────────────────────────────────────────────────────┐             │
│   │  1. Exchange auth_code for Google tokens ✓                           │             │
│   │  2. Fetch user info (email, name, picture) ✓                         │             │
│   └─────────────────────────┬─────────────────────────────────────────────┘             │
│                             │                                                            │
│                             ▼                                                            │
│   ┌───────────────────────────────────────────────────────────────────────┐             │
│   │  ★ NEW: ONBOARDING CHECK                                              │             │
│   │                                                                       │             │
│   │  mysql_user = mysql_db.get_user_by_email(email)                       │             │
│   │                                                                       │             │
│   │  IF mysql_user is None:                                               │             │
│   │      → Return error: "Account not onboarded. Contact admin."          │             │
│   │      → BLOCK LOGIN                                                    │             │
│   │                                                                       │             │
│   │  IF mysql_user['is_active'] == False:                                 │             │
│   │      → Return error: "Account deactivated."                           │             │
│   │      → BLOCK LOGIN                                                    │             │
│   │                                                                       │             │
│   └─────────────────────────┬─────────────────────────────────────────────┘             │
│                             │ User exists & is active                                    │
│                             ▼                                                            │
│   ┌───────────────────────────────────────────────────────────────────────┐             │
│   │  3. Create/get Django user                                            │             │
│   │  4. Create/get SocialAccount                                          │             │
│   │  5. Create/Update SocialToken                                         │             │
│   │  6. Generate JWT with role/department from mysql_user                 │             │
│   └─────────────────────────┬─────────────────────────────────────────────┘             │
│                             │                                                            │
│                             ▼                                                            │
│   ✅ Only pre-approved users can login!                                                  │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Where & How Each Entity is Created

### 3.1 Django User (`auth_user` table)

**Created by:** `User.objects.create()` or `User.objects.get_or_create()`

**Location:** `views.py` line ~158-180

```python
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

    user = User.objects.create(
        email=email,
        username=username,
        first_name=name.split()[0] if name else "",
        last_name=" ".join(name.split()[1:]) if name and len(name.split()) > 1 else "",
    )
```

**Schema (Django's auth_user):**
| Column | Type | Description |
|--------|------|-------------|
| id | INT (PK) | Auto-increment primary key |
| username | VARCHAR(150) | Unique username |
| email | VARCHAR(254) | User's email |
| first_name | VARCHAR(150) | First name |
| last_name | VARCHAR(150) | Last name |
| password | VARCHAR(128) | Hashed password (empty for OAuth users) |
| is_active | BOOLEAN | Can user login? |
| is_staff | BOOLEAN | Can access admin? |
| is_superuser | BOOLEAN | Has all permissions? |
| date_joined | DATETIME | Registration timestamp |
| last_login | DATETIME | Last login timestamp |

---

### 3.2 Social App (`socialaccount_socialapp` table)

**Created by:** `SocialApp.objects.get_or_create()`

**Purpose:** Stores Google OAuth application credentials (client_id, secret)

**Location:** `views.py` line ~193-200

```python
from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp

social_app, created = SocialApp.objects.get_or_create(
    provider="google",
    defaults={
        "name": "Google",
        "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
        "secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
    },
)
```

**Schema (AllAuth's socialaccount_socialapp):**
| Column | Type | Description |
|--------|------|-------------|
| id | INT (PK) | Auto-increment primary key |
| provider | VARCHAR(30) | "google", "facebook", etc. |
| name | VARCHAR(40) | Display name |
| client_id | VARCHAR(191) | OAuth Client ID |
| secret | VARCHAR(191) | OAuth Client Secret |
| key | VARCHAR(191) | Additional key (optional) |

---

### 3.3 Social Account (`socialaccount_socialaccount` table)

**Created by:** `SocialAccount.objects.get_or_create()`

**Purpose:** Links Django user to their Google identity

**Location:** `views.py` line ~202-210

```python
social_account, created = SocialAccount.objects.get_or_create(
    user=user,                    # FK to auth_user
    provider="google",
    defaults={
        "uid": google_id,          # Google's unique user ID
        "extra_data": userinfo,    # JSON with email, name, picture
    },
)
```

**Schema (AllAuth's socialaccount_socialaccount):**
| Column | Type | Description |
|--------|------|-------------|
| id | INT (PK) | Auto-increment primary key |
| user_id | INT (FK) | References auth_user.id |
| provider | VARCHAR(30) | "google" |
| uid | VARCHAR(191) | Google's unique ID for this user |
| extra_data | TEXT (JSON) | Full Google profile data |
| last_login | DATETIME | Last OAuth login |
| date_joined | DATETIME | First OAuth connection |

**extra_data example:**
```json
{
    "id": "123456789012345678901",
    "email": "user@gmail.com",
    "verified_email": true,
    "name": "John Doe",
    "given_name": "John",
    "family_name": "Doe",
    "picture": "https://lh3.googleusercontent.com/..."
}
```

---

### 3.4 Social Token (`socialaccount_socialtoken` table)

**Created by:** `SocialToken.objects.create()` or `.get()` + `.save()`

**Purpose:** Stores Google OAuth access & refresh tokens for API calls

**Location:** `views.py` line ~213-237

```python
refresh_token = token_response_data.get("refresh_token", "")
try:
    social_token = SocialToken.objects.get(
        account=social_account,
        app=social_app,
    )
    # Update existing token
    social_token.token = access_token
    social_token.expires_at = timezone.now() + timedelta(seconds=token_response_data.get("expires_in", 3600))
    if refresh_token:
        social_token.token_secret = refresh_token
    social_token.save()
    
except SocialToken.DoesNotExist:
    # Create new token
    social_token = SocialToken.objects.create(
        account=social_account,        # FK to socialaccount
        app=social_app,                # FK to socialapp
        token=access_token,            # Google access token
        token_secret=refresh_token,    # Google refresh token
        expires_at=timezone.now() + timedelta(seconds=3600),
    )
```

**Schema (AllAuth's socialaccount_socialtoken):**
| Column | Type | Description |
|--------|------|-------------|
| id | INT (PK) | Auto-increment primary key |
| account_id | INT (FK) | References socialaccount_socialaccount.id |
| app_id | INT (FK) | References socialaccount_socialapp.id |
| token | TEXT | Google access_token (~2000 chars) |
| token_secret | TEXT | Google refresh_token |
| expires_at | DATETIME | When access_token expires |

---

### 3.5 Business User (`users` table - Custom MySQL)

**Created by:** `mysql_db.create_user()` (in `mysql_db.py`)

**Purpose:** Business-specific data (role, department, warehouse, quotas)

**Currently NOT created during OAuth login!** This is the gap.

**Location:** `mysql_db.py` line ~46-79

```python
def create_user(
    self,
    email: str,
    name: str,
    role: str,
    department: str,
    warehouse: str,
    position: str,
    created_by: str = None,
) -> Dict:
    """Create new user account"""
    user_id = str(uuid.uuid4())

    query = """
    INSERT INTO users 
    (user_id, email, name, role, department, warehouse, position, created_by)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    with self.get_cursor() as (cursor, conn):
        cursor.execute(query, (user_id, email, name, role, department, warehouse, position, created_by))

    return {"user_id": user_id, "email": email, "name": name, "role": role}
```

**Schema (Custom `users` table):**
| Column | Type | Description |
|--------|------|-------------|
| user_id | VARCHAR(255) PK | UUID primary key |
| email | VARCHAR(255) UNIQUE | User's email |
| name | VARCHAR(255) | Full name |
| role | VARCHAR(50) | "admin", "manager", "user" |
| department | VARCHAR(100) | Business department |
| warehouse | VARCHAR(100) | Assigned warehouse |
| position | VARCHAR(100) | Job title |
| google_id | VARCHAR(255) | Google's unique ID |
| google_access_token | TEXT | Stored access token |
| google_refresh_token | TEXT | Stored refresh token |
| token_expiry | DATETIME | Token expiration |
| daily_token_limit | INT | AI token quota |
| daily_request_limit | INT | API request quota |
| is_active | BOOLEAN | Account status |
| created_by | VARCHAR(255) | Admin who created |
| created_at | TIMESTAMP | Creation time |

---

## 4. Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              ENTITY RELATIONSHIPS                                        │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│                          ┌─────────────────────────┐                                     │
│                          │      SocialApp          │                                     │
│                          │   (Google OAuth App)    │                                     │
│                          │                         │                                     │
│                          │  id: 1                  │                                     │
│                          │  provider: "google"     │                                     │
│                          │  client_id: "10059..."  │                                     │
│                          │  secret: "GOCSPX-..."   │                                     │
│                          └───────────┬─────────────┘                                     │
│                                      │                                                   │
│                                      │ 1:N                                               │
│                                      │                                                   │
│  ┌──────────────────────┐           │           ┌──────────────────────┐                │
│  │   Django User        │           │           │   Business User      │                │
│  │   (auth_user)        │           │           │   (custom users)     │                │
│  │                      │           │           │                      │                │
│  │  id: 5               │           │           │  user_id: "abc-123"  │                │
│  │  email: john@...     │◀──────────┼──────────▶│  email: john@...     │                │
│  │  username: john      │    Same   │   email   │  role: "manager"     │                │
│  │  first_name: John    │   email   │           │  department: "ops"   │                │
│  │  last_name: Doe      │           │           │  warehouse: "WH-01"  │                │
│  └──────────┬───────────┘           │           └──────────────────────┘                │
│             │                       │                                                    │
│             │ 1:N                   │                                                    │
│             │                       │                                                    │
│             ▼                       │                                                    │
│  ┌──────────────────────┐           │                                                    │
│  │   SocialAccount      │           │                                                    │
│  │                      │           │                                                    │
│  │  id: 10              │           │                                                    │
│  │  user_id: 5 (FK)     │───────────┘                                                    │
│  │  provider: "google"  │                                                                │
│  │  uid: "123456789"    │                                                                │
│  │  extra_data: {...}   │                                                                │
│  └──────────┬───────────┘                                                                │
│             │                                                                            │
│             │ 1:N                                                                        │
│             │                                                                            │
│             ▼                                                                            │
│  ┌──────────────────────┐                                                                │
│  │   SocialToken        │                                                                │
│  │                      │                                                                │
│  │  id: 15              │                                                                │
│  │  account_id: 10 (FK) │                                                                │
│  │  app_id: 1 (FK)      │                                                                │
│  │  token: "ya29.a0..." │  ◀── Google Access Token                                       │
│  │  token_secret: "1//" │  ◀── Google Refresh Token                                      │
│  │  expires_at: ...     │                                                                │
│  └──────────────────────┘                                                                │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Current Login Flow (Step by Step)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                            CURRENT LOGIN FLOW (DETAILED)                                 │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  STEP 1: Frontend initiates Google OAuth                                                 │
│  ════════════════════════════════════════                                                │
│                                                                                          │
│  User clicks "Login with Google" button                                                  │
│          │                                                                               │
│          ▼                                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐                    │
│  │  Frontend: @react-oauth/google GoogleLogin component            │                    │
│  │                                                                 │                    │
│  │  useGoogleLogin({                                               │                    │
│  │      flow: 'auth-code',                                         │                    │
│  │      onSuccess: (response) => {                                 │                    │
│  │          // response.code = "4/0AQSTgQ..."                      │                    │
│  │          sendToBackend(response.code);                          │                    │
│  │      }                                                          │                    │
│  │  })                                                             │                    │
│  └─────────────────────────────────────────────────────────────────┘                    │
│          │                                                                               │
│          │ POST /api/google-auth/ { "code": "4/0AQSTgQ..." }                            │
│          ▼                                                                               │
│                                                                                          │
│  STEP 2: Backend exchanges code for tokens                                               │
│  ══════════════════════════════════════════                                              │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐                    │
│  │  views.py: google_auth_dynamodb()                               │                    │
│  │                                                                 │                    │
│  │  POST https://oauth2.googleapis.com/token                       │                    │
│  │  {                                                              │                    │
│  │      code: "4/0AQSTgQ...",                                      │                    │
│  │      client_id: settings.GOOGLE_OAUTH2_CLIENT_ID,               │                    │
│  │      client_secret: settings.GOOGLE_OAUTH2_CLIENT_SECRET,       │                    │
│  │      redirect_uri: "postmessage",                               │                    │
│  │      grant_type: "authorization_code"                           │                    │
│  │  }                                                              │                    │
│  │                                                                 │                    │
│  │  Response:                                                       │                    │
│  │  {                                                              │                    │
│  │      access_token: "ya29.a0AfH6SMB...",                         │                    │
│  │      refresh_token: "1//0g-pKJ3...",                            │                    │
│  │      expires_in: 3600,                                          │                    │
│  │      token_type: "Bearer"                                       │                    │
│  │  }                                                              │                    │
│  └─────────────────────────────────────────────────────────────────┘                    │
│          │                                                                               │
│          ▼                                                                               │
│                                                                                          │
│  STEP 3: Fetch user info from Google                                                     │
│  ════════════════════════════════════                                                    │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐                    │
│  │  GET https://www.googleapis.com/oauth2/v2/userinfo              │                    │
│  │  Headers: { Authorization: "Bearer ya29.a0AfH6SMB..." }         │                    │
│  │                                                                 │                    │
│  │  Response:                                                       │                    │
│  │  {                                                              │                    │
│  │      id: "123456789012345678901",                               │                    │
│  │      email: "john.doe@company.com",                             │                    │
│  │      verified_email: true,                                      │                    │
│  │      name: "John Doe",                                          │                    │
│  │      given_name: "John",                                        │                    │
│  │      family_name: "Doe",                                        │                    │
│  │      picture: "https://lh3.googleusercontent.com/..."           │                    │
│  │  }                                                              │                    │
│  └─────────────────────────────────────────────────────────────────┘                    │
│          │                                                                               │
│          ▼                                                                               │
│                                                                                          │
│  STEP 4: Create/Get Django User  ⚠️ NO BLOCKING CHECK HERE!                             │
│  ═══════════════════════════════                                                         │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐                    │
│  │  try:                                                           │                    │
│  │      user = User.objects.get(email=email)                       │                    │
│  │      # User exists in Django                                    │                    │
│  │  except User.DoesNotExist:                                      │                    │
│  │      # Create new Django user                                   │                    │
│  │      user = User.objects.create(                                │                    │
│  │          email=email,                                           │                    │
│  │          username=unique_username,                              │                    │
│  │          first_name=...,                                        │                    │
│  │          last_name=...                                          │                    │
│  │      )                                                          │                    │
│  │                                                                 │                    │
│  │  ⚠️ AUTO-CREATES USER - NO APPROVAL NEEDED!                     │                    │
│  └─────────────────────────────────────────────────────────────────┘                    │
│          │                                                                               │
│          ▼                                                                               │
│                                                                                          │
│  STEP 5: Create/Get SocialApp                                                            │
│  ════════════════════════════                                                            │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐                    │
│  │  social_app, _ = SocialApp.objects.get_or_create(               │                    │
│  │      provider="google",                                         │                    │
│  │      defaults={                                                 │                    │
│  │          "name": "Google",                                      │                    │
│  │          "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,         │                    │
│  │          "secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET         │                    │
│  │      }                                                          │                    │
│  │  )                                                              │                    │
│  │                                                                 │                    │
│  │  Usually created once, then reused                              │                    │
│  └─────────────────────────────────────────────────────────────────┘                    │
│          │                                                                               │
│          ▼                                                                               │
│                                                                                          │
│  STEP 6: Create/Get SocialAccount                                                        │
│  ════════════════════════════════                                                        │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐                    │
│  │  social_account, _ = SocialAccount.objects.get_or_create(       │                    │
│  │      user=user,                                                 │                    │
│  │      provider="google",                                         │                    │
│  │      defaults={                                                 │                    │
│  │          "uid": google_id,         # "123456789..."             │                    │
│  │          "extra_data": userinfo    # Full Google profile        │                    │
│  │      }                                                          │                    │
│  │  )                                                              │                    │
│  │                                                                 │                    │
│  │  Links Django user to their Google identity                     │                    │
│  └─────────────────────────────────────────────────────────────────┘                    │
│          │                                                                               │
│          ▼                                                                               │
│                                                                                          │
│  STEP 7: Create/Update SocialToken                                                       │
│  ═════════════════════════════════                                                       │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐                    │
│  │  try:                                                           │                    │
│  │      token = SocialToken.objects.get(account=social_account)    │                    │
│  │      token.token = access_token      # Update access token      │                    │
│  │      token.token_secret = refresh    # Update refresh token     │                    │
│  │      token.expires_at = now + 1hr    # Update expiry            │                    │
│  │      token.save()                                               │                    │
│  │  except SocialToken.DoesNotExist:                               │                    │
│  │      SocialToken.objects.create(                                │                    │
│  │          account=social_account,                                │                    │
│  │          app=social_app,                                        │                    │
│  │          token=access_token,                                    │                    │
│  │          token_secret=refresh_token,                            │                    │
│  │          expires_at=now + 1hr                                   │                    │
│  │      )                                                          │                    │
│  └─────────────────────────────────────────────────────────────────┘                    │
│          │                                                                               │
│          ▼                                                                               │
│                                                                                          │
│  STEP 8: Generate JWT & Return                                                           │
│  ═════════════════════════════                                                           │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐                    │
│  │  refresh = RefreshToken.for_user(user)                          │                    │
│  │  access_token_jwt = str(refresh.access_token)                   │                    │
│  │                                                                 │                    │
│  │  # JWT contains user claims from CustomTokenObtainPairSerializer│                    │
│  │  # which adds: role, department, warehouse from MySQL users     │                    │
│  │                                                                 │                    │
│  │  return JsonResponse({                                          │                    │
│  │      "access": access_token_jwt,                                │                    │
│  │      "refresh": str(refresh),                                   │                    │
│  │      "user": { id, email, username, name, picture }             │                    │
│  │  })                                                             │                    │
│  └─────────────────────────────────────────────────────────────────┘                    │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. How to Implement Onboarding Check

### Add This Block Between Step 3 and Step 4:

```python
# === ONBOARDING CHECK ===
# Check if user exists in business database BEFORE creating Django user

mysql_user = mysql_db.get_user_by_email(email)

if not mysql_user:
    return JsonResponse({
        "error": "Account not found. Please contact your administrator to be onboarded.",
        "code": "NOT_ONBOARDED"
    }, status=403)

if not mysql_user.get("is_active", True):
    return JsonResponse({
        "error": "Your account has been deactivated. Please contact your administrator.",
        "code": "ACCOUNT_DEACTIVATED"
    }, status=403)

# User is onboarded and active, proceed with login...
```

### Where to Add (views.py line ~155):

```python
# Current code (after fetching userinfo):
email = userinfo.get("email")
name = userinfo.get("name", "")
google_id = userinfo.get("id")
picture = userinfo.get("picture", "")

if not email:
    return JsonResponse({"error": "Email not provided by Google"}, status=400)

# === ADD ONBOARDING CHECK HERE ===
mysql_user = mysql_db.get_user_by_email(email)

if not mysql_user:
    return JsonResponse({
        "error": "Account not found. Please contact your administrator to be onboarded.",
        "code": "NOT_ONBOARDED"
    }, status=403)

if not mysql_user.get("is_active", True):
    return JsonResponse({
        "error": "Your account has been deactivated.",
        "code": "ACCOUNT_DEACTIVATED"  
    }, status=403)

print(f"✅ User verified in business database: {mysql_user['name']} ({mysql_user['role']})")
# === END ONBOARDING CHECK ===

# Then continue with existing code...
print(f"👤 Getting/creating user for: {email}")
```

---

## 7. Onboarding Flow (Admin Creates User)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                            ADMIN ONBOARDING FLOW                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  1. Admin logs into admin dashboard                                                      │
│          │                                                                               │
│          ▼                                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐                    │
│  │  Admin clicks "Add New User"                                    │                    │
│  │                                                                 │                    │
│  │  Form fields:                                                   │                    │
│  │  • Email: employee@company.com                                  │                    │
│  │  • Name: John Doe                                               │                    │
│  │  • Role: [manager ▼]                                            │                    │
│  │  • Department: [Operations ▼]                                   │                    │
│  │  • Warehouse: [WH-01 ▼]                                         │                    │
│  │  • Position: Shift Supervisor                                   │                    │
│  └─────────────────────────────────────────────────────────────────┘                    │
│          │                                                                               │
│          │ POST /api/users/create                                                        │
│          ▼                                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐                    │
│  │  Backend: mysql_db.create_user(                                 │                    │
│  │      email="employee@company.com",                              │                    │
│  │      name="John Doe",                                           │                    │
│  │      role="manager",                                            │                    │
│  │      department="Operations",                                   │                    │
│  │      warehouse="WH-01",                                         │                    │
│  │      position="Shift Supervisor",                               │                    │
│  │      created_by=admin_user_id                                   │                    │
│  │  )                                                              │                    │
│  │                                                                 │                    │
│  │  → Creates record in MySQL 'users' table                        │                    │
│  │  → Generates UUID for user_id                                   │                    │
│  │  → Sets is_active = TRUE                                        │                    │
│  │  → Records created_by and created_at                            │                    │
│  └─────────────────────────────────────────────────────────────────┘                    │
│          │                                                                               │
│          ▼                                                                               │
│  ✅ User is now "onboarded" and can login with Google OAuth                             │
│                                                                                          │
│  2. Employee tries to login with Google                                                  │
│          │                                                                               │
│          ▼                                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐                    │
│  │  google_auth_dynamodb():                                        │                    │
│  │                                                                 │                    │
│  │  1. Get email from Google: "employee@company.com"               │                    │
│  │  2. mysql_db.get_user_by_email("employee@company.com")          │                    │
│  │     → Returns: { user_id, name, role, department, ... }         │                    │
│  │  3. ✅ User exists! Proceed with login                          │                    │
│  │  4. Create Django user (if needed)                              │                    │
│  │  5. Create social account links                                 │                    │
│  │  6. Generate JWT with role/department claims                    │                    │
│  └─────────────────────────────────────────────────────────────────┘                    │
│          │                                                                               │
│          ▼                                                                               │
│  ✅ Employee successfully logged in with correct permissions!                            │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Summary Table

| Entity | Table | Database | Created By | Purpose |
|--------|-------|----------|------------|---------|
| Django User | `auth_user` | MySQL (Django) | `User.objects.create()` | Basic authentication |
| Social App | `socialaccount_socialapp` | MySQL (Django) | `SocialApp.get_or_create()` | Store Google OAuth credentials |
| Social Account | `socialaccount_socialaccount` | MySQL (Django) | `SocialAccount.get_or_create()` | Link user to Google identity |
| Social Token | `socialaccount_socialtoken` | MySQL (Django) | `SocialToken.create()` | Store access/refresh tokens |
| Business User | `users` | MySQL (Custom) | Admin via `mysql_db.create_user()` | Role, department, quotas |

---

## 9. Key Insight

**Currently:** Anyone with a valid Google account can create an account and login.

**With Onboarding:** Only users pre-created in the `users` table by an admin can login.

The check uses: `mysql_db.get_user_by_email(email)` → Returns `None` if not onboarded → Block login.
