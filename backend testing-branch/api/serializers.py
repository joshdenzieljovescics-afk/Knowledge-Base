from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

# from .models import Product, Cart this is how to use models


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "password")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims to JWT token
        from api.mysql_db import SafexpressMySQLDB

        mysql_db = SafexpressMySQLDB(
            host="localhost",
            database="safexpressops_local",
            user="root",
            password="",
        )

        # Get user data from MySQL
        mysql_user = mysql_db.get_user_by_email(user.email)

        if mysql_user:
            token["role"] = mysql_user["role"]
            token["department"] = mysql_user["department"]
            token["warehouse"] = mysql_user["warehouse"]
            token["user_id"] = mysql_user["user_id"]

        return token
