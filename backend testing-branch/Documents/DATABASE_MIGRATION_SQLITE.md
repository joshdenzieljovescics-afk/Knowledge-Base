# Database Migration: MySQL to SQLite

## Overview

This document describes the migration from MySQL to SQLite and the implementation of a custom User model with onboarding checks.

---

## Migration Summary

| Component | Before | After |
|-----------|--------|-------|
| Database | MySQL (safexpressops_local) | SQLite (db.sqlite3) |
| User Model | Django's auth_user + MySQL users table | Custom `CustomUser` model |
| User Fields | username, email, first_name, last_name | fullname, gmail, role, is_active, created_by, created_at, updated_at |
| Auth Flow | Auto-create user on login | Require onboarding before login |
| Onboarding | None | Admin must onboard user first |

---

## New Schema: CustomUser Model

```
┌─────────────────────────────────────────────────────────────────────┐
│                           auth_user                                  │
├─────────────────────────────────────────────────────────────────────┤
│  Field         │ Type           │ Description                       │
├────────────────┼────────────────┼───────────────────────────────────┤
│  id            │ INTEGER PK     │ Auto-generated primary key        │
│  fullname      │ VARCHAR(255)   │ User's full name                  │
│  gmail         │ VARCHAR(254)   │ Email address (unique, username)  │
│  role          │ VARCHAR(20)    │ admin | manager | staff           │
│  is_active     │ BOOLEAN        │ False until onboarded             │
│  is_staff      │ BOOLEAN        │ Django admin access               │
│  created_by    │ VARCHAR(254)   │ Email of admin who onboarded      │
│  created_at    │ DATETIME       │ Account creation timestamp        │
│  updated_at    │ DATETIME       │ Last update timestamp             │
│  google_picture│ VARCHAR(200)   │ Google profile picture URL        │
│  password      │ VARCHAR(128)   │ Hashed password (optional)        │
│  last_login    │ DATETIME       │ Last login timestamp              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Authentication Flow (Updated)

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                        NEW AUTHENTICATION FLOW WITH ONBOARDING                        │
└──────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────┐          ┌──────────────┐          ┌──────────────┐
    │  User    │          │   Frontend   │          │   Backend    │
    └────┬─────┘          └──────┬───────┘          └──────┬───────┘
         │                       │                         │
         │  Click "Sign in       │                         │
         │  with Google"         │                         │
         │──────────────────────>│                         │
         │                       │                         │
         │                       │  Redirect to Google     │
         │<──────────────────────│                         │
         │                       │                         │
         │  Authenticate with    │                         │
         │  Google               │                         │
         │──────────────────────>│                         │
         │                       │                         │
         │  Auth code            │                         │
         │<──────────────────────│                         │
         │                       │                         │
         │                       │  POST /api/auth/google/ │
         │                       │  { "code": "..." }      │
         │                       │─────────────────────────>
         │                       │                         │
         │                       │                         │  Check if user exists
         │                       │                         │  in CustomUser table
         │                       │                         │
         │                       │                     ┌───┴───┐
         │                       │                     │ User  │
         │                       │                     │exists?│
         │                       │                     └───┬───┘
         │                       │                         │
         │                       │           NO            │           YES
         │                       │     ┌───────────────────┼───────────────────┐
         │                       │     │                   │                   │
         │                       │     ▼                   │                   ▼
         │                       │  ┌─────────────┐        │            ┌─────────────┐
         │                       │  │   403       │        │            │ is_active?  │
         │                       │  │ "Not        │        │            └──────┬──────┘
         │                       │  │ onboarded"  │        │                   │
         │                       │  └─────────────┘        │         YES       │    NO
         │                       │                         │     ┌─────────────┼────────┐
         │                       │                         │     │             │        │
         │                       │                         │     ▼             │        ▼
         │                       │                         │ ┌─────────┐       │  ┌─────────────┐
         │                       │                         │ │ Generate│       │  │   403       │
         │                       │                         │ │ JWT     │       │  │ "Account    │
         │                       │                         │ │ Tokens  │       │  │ deactivated"│
         │                       │                         │ └────┬────┘       │  └─────────────┘
         │                       │                         │      │            │
         │                       │  JWT tokens + user info │      │            │
         │                       │<────────────────────────┼──────┘            │
         │                       │                         │                   │
         │  Login successful     │                         │                   │
         │<──────────────────────│                         │                   │
         │                       │                         │                   │
         └───────────────────────┴─────────────────────────┴───────────────────┘
```

---

## Onboarding Flow

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              ADMIN ONBOARDING FLOW                                    │
└──────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────┐          ┌──────────────┐          ┌──────────────┐
    │  Admin   │          │   Frontend   │          │   Backend    │
    └────┬─────┘          └──────┬───────┘          └──────┬───────┘
         │                       │                         │
         │  Navigate to User     │                         │
         │  Management           │                         │
         │──────────────────────>│                         │
         │                       │                         │
         │  Fill onboard form:   │                         │
         │  - Full Name          │                         │
         │  - Gmail              │                         │
         │  - Role               │                         │
         │──────────────────────>│                         │
         │                       │                         │
         │                       │  POST /api/users/onboard/
         │                       │  {                      │
         │                       │    "fullname": "...",   │
         │                       │    "gmail": "...",      │
         │                       │    "role": "staff"      │
         │                       │  }                      │
         │                       │─────────────────────────>
         │                       │                         │
         │                       │                         │  Verify admin role
         │                       │                         │  Create user with
         │                       │                         │  is_active=True
         │                       │                         │
         │                       │  { user: {...} }        │
         │                       │<────────────────────────│
         │                       │                         │
         │  User onboarded!      │                         │
         │<──────────────────────│                         │
         │                       │                         │
         └───────────────────────┴─────────────────────────┘


Now the new user can login with Google OAuth!
```

---

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/google/` | Google OAuth login (requires onboarded user) | None |
| POST | `/api/token/` | Get JWT tokens (username/password) | None |
| POST | `/api/token/refresh/` | Refresh JWT token | JWT |

### User Management (Admin Only)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/users/onboard/` | Onboard new user | JWT (admin) |
| GET | `/api/users/` | List all users | JWT (admin) |
| PATCH | `/api/users/<id>/` | Update user | JWT (admin) |
| DELETE | `/api/users/<id>/deactivate/` | Deactivate user | JWT (admin) |

---

## Example API Requests

### 1. Onboard a New User (Admin)

```bash
POST /api/users/onboard/
Authorization: Bearer <admin_jwt_token>
Content-Type: application/json

{
    "fullname": "John Doe",
    "gmail": "john.doe@example.com",
    "role": "staff"
}
```

**Response (201 Created):**
```json
{
    "message": "User john.doe@example.com has been successfully onboarded.",
    "user": {
        "id": 1,
        "fullname": "John Doe",
        "gmail": "john.doe@example.com",
        "role": "staff",
        "is_active": true,
        "created_by": "admin@example.com",
        "created_at": "2025-01-15T10:30:00Z",
        "updated_at": "2025-01-15T10:30:00Z"
    }
}
```

### 2. Google OAuth Login (Onboarded User)

```bash
POST /api/auth/google/
Content-Type: application/json

{
    "code": "<google_auth_code>"
}
```

**Response (200 OK):**
```json
{
    "access": "<jwt_access_token>",
    "refresh": "<jwt_refresh_token>",
    "user": {
        "id": 1,
        "fullname": "John Doe",
        "gmail": "john.doe@example.com",
        "role": "staff",
        "is_active": true,
        "picture": "https://..."
    }
}
```

**Response (403 Forbidden - Not Onboarded):**
```json
{
    "error": "Account not found",
    "message": "Your account has not been onboarded yet. Please contact an administrator to create your account.",
    "email": "john.doe@example.com"
}
```

### 3. List Users (Admin)

```bash
GET /api/users/?role=staff&is_active=true
Authorization: Bearer <admin_jwt_token>
```

**Response:**
```json
{
    "count": 5,
    "users": [
        {
            "id": 1,
            "fullname": "John Doe",
            "gmail": "john.doe@example.com",
            "role": "staff",
            "is_active": true,
            "created_by": "admin@example.com",
            "created_at": "2025-01-15T10:30:00Z",
            "updated_at": "2025-01-15T10:30:00Z"
        }
    ]
}
```

---

## Migration Steps

### Step 1: Prepare the Environment

```bash
# Delete old MySQL-related packages (optional)
# pip uninstall mysqlclient mysql-connector-python

# Ensure you have the required packages
pip install django djangorestframework djangorestframework-simplejwt django-allauth django-cors-headers
```

### Step 2: Run Migrations

```bash
# Navigate to the backend directory
cd backend testing-branch

# Create migrations for the new CustomUser model
python manage.py makemigrations api

# Apply migrations (this creates the SQLite database)
python manage.py migrate
```

### Step 3: Create Initial Admin User

```bash
# Create a superuser (first admin)
python manage.py createsuperuser

# Follow the prompts:
# Gmail: admin@example.com
# Fullname: Admin User
# Password: (enter password)
```

### Step 4: Verify the Migration

```bash
# Start the development server
python manage.py runserver

# Access Django Admin to verify
# http://localhost:8000/admin/
```

---

## Files Modified

| File | Changes |
|------|---------|
| `backend/settings.py` | Changed database to SQLite, added AUTH_USER_MODEL |
| `api/models.py` | Created CustomUser model with CustomUserManager |
| `api/serializers.py` | Updated serializers for CustomUser |
| `api/views.py` | Updated Google OAuth with onboarding check, added onboard/user management endpoints |
| `api/admin.py` | Registered CustomUser with admin interface |
| `backend/urls.py` | Updated URL patterns for new endpoints |

---

## Deleted/Deprecated Files

| File | Status |
|------|--------|
| `api/mysql_db.py` | No longer needed (can be deleted or archived) |

---

## JWT Token Claims

The JWT token now includes these custom claims:

```json
{
    "token_type": "access",
    "exp": 1705322400,
    "iat": 1705319400,
    "jti": "...",
    "user_id": 1,
    "role": "staff",
    "fullname": "John Doe",
    "gmail": "john.doe@example.com"
}
```

---

## Troubleshooting

### Error: "No such table: auth_user"

```bash
# Run migrations
python manage.py migrate
```

### Error: "Column 'gmail' cannot be null"

```bash
# The email field is required. Check your request payload.
```

### Error: "Permission denied. Only admins can onboard users."

```bash
# Ensure you're logged in as an admin user (role = "admin")
```

### Need to reset the database?

```bash
# Delete the SQLite file and re-run migrations
del db.sqlite3
python manage.py makemigrations api
python manage.py migrate
python manage.py createsuperuser
```

---

## Security Considerations

1. **Onboarding Required**: Users cannot login unless an admin onboards them first
2. **Role-Based Access**: Only admins can manage users
3. **Soft Delete**: Deactivating a user sets `is_active=False` instead of deleting
4. **JWT Claims**: Role and user info embedded in token for stateless auth
5. **AllAuth Integration**: Google OAuth tokens stored securely via django-allauth

---

## Next Steps

1. [ ] Update frontend to use new `/api/auth/google/` endpoint
2. [ ] Create admin UI for user management
3. [ ] Add email notifications for onboarding
4. [ ] Implement password reset flow
5. [ ] Add audit logging for user actions
