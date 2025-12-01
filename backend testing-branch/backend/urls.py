from django.contrib import admin
from django.urls import path, include
from api.views import *
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf.urls.static import static
from api.views import dynamic_mapping_workflow
from api.serializers import CustomTokenObtainPairSerializer

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/user/register/", UserCreate.as_view(), name="user_create"),
    # ✅ JWT Token endpoints - Use custom serializer for role-based tokens
    path(
        "api/token/",
        TokenObtainPairView.as_view(serializer_class=CustomTokenObtainPairSerializer),
        name="token_obtain_pair",
    ),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api-auth/", include("rest_framework.urls")),
    path("accounts/", include("allauth.urls")),
    path("callback/", google_login_callback, name="callback"),
    path("api/auth/user/", UserDetailView.as_view(), name="user_detail"),
    path("api/google/validate_token/", validate_google_token, name="validate_token"),
    # ✅ DynamoDB authentication (legacy - can remove if not using)
    path(
        "api/auth/dynamodb/google/", google_auth_dynamodb, name="google_auth_dynamodb"
    ),
    # ✅ MySQL authentication (current implementation)
    path("api/auth/mysql/google/", google_auth_mysql, name="google_auth_mysql"),
    path("api/auth/mysql/create-user/", create_user_account, name="create_user"),
    path("api/auth/mysql/users/", get_all_users, name="get_all_users"),  # ✅ Add this
    # Workflow endpoints
    path(
        "api/dynamic-mapping/upload/",
        dynamic_mapping_workflow,
        name="dynamic_mapping_workflow",
    ),
    path("api/abc-analysis/", abc_analysis_workflow, name="abc_analysis_workflow"),
    path(
        "api/workload-analysis/",
        workload_analysis_workflow,
        name="workload_analysis_workflow",
    ),
    # Monitoring endpoints
    path("api/monitoring/summary/", agent_monitoring_summary, name="agent_monitoring"),
    path("api/monitoring/feedback/", submit_agent_feedback, name="agent_feedback"),
]
