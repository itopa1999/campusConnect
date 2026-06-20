from rest_framework import serializers
from .models import User
from utils.enums import IssueTypeEnum


class UserCreationSerializer(serializers.Serializer):
    """Serializer for user account creation"""
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    password = serializers.CharField(max_length=128, write_only=True, required=True)


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(max_length=128, write_only=True, required=True)


class UserForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class ResendVerificationEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(max_length=128, write_only=True, required=True)
    new_password = serializers.CharField(max_length=128, write_only=True, required=True)


class ReportSerializer(serializers.Serializer):
    reporter_name = serializers.CharField(max_length=255)
    reporter_email = serializers.EmailField()
    issue_type = serializers.ChoiceField(choices=IssueTypeEnum.choices())
    listing_identifier = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    reported_user_email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    message = serializers.CharField()

class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(max_length=5000, write_only=True, required=True)

class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(max_length=5000, write_only=True, required=True)

class ConfirmResetPasswordSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=200, write_only=True, required=True)
    email = serializers.EmailField(max_length=128, write_only=True, required=True)
    password = serializers.CharField(max_length=128, write_only=True, required=True)
    confirm_password = serializers.CharField(max_length=128, write_only=True, required=True)

class BuyPointSerializer(serializers.Serializer):
    amount = serializers.IntegerField(required=True)
    gateway = serializers.CharField(max_length=200, required=True)
    package_id = serializers.IntegerField(required=True)
    points = serializers.IntegerField(required=True)