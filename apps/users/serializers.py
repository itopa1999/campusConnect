from apps.campus.models import Review
from apps.moderator.models import FlaggedContent, UserModeration
from rest_framework import serializers
from utils.constant_helper import ConstantHelper
from utils.helpers import calculate_profile_completion, humanize_date
from .models import Badge, PointTransaction, User
from utils.enums import ContentTypeEnum, IssueTypeEnum


class UserCreationSerializer(serializers.Serializer):
    """Serializer for user account creation"""
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, write_only=True, required=True)


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(min_length=8, write_only=True, required=True)
    platform = serializers.CharField(required=True)



class UserForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class ResendVerificationEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(min_length=8, write_only=True, required=True)
    new_password = serializers.CharField(min_length=8, write_only=True, required=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True, required=True)

class ReportSerializer(serializers.Serializer):
    reporter_name = serializers.CharField(max_length=255)
    reporter_email = serializers.EmailField()
    issue_type = serializers.ChoiceField(choices=IssueTypeEnum.choices())
    listing_identifier = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    reported_user_email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    message = serializers.CharField()

class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(max_length=5000, write_only=True, required=False)
    platform = serializers.CharField(required=True)
    
class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(max_length=5000, write_only=True, required=False)
    platform = serializers.CharField(required=True)

class ConfirmResetPasswordSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=200, write_only=True, required=True)
    email = serializers.EmailField(max_length=128, write_only=True, required=True)
    password = serializers.CharField(min_length=8, write_only=True, required=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True, required=True)

class BuyPointSerializer(serializers.Serializer):
    amount = serializers.IntegerField(required=True)
    gateway = serializers.CharField(max_length=200, required=True)
    package_id = serializers.IntegerField(required=True)
    points = serializers.IntegerField(required=True)

class RetryPurchaseSerailizer(serializers.Serializer):
    purchase_id = serializers.CharField(max_length=200, required=True)



class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ['name', 'icon', 'description']


class FlaggedContentSerializer(serializers.ModelSerializer):
    resolved_by = serializers.CharField(source='resolved_by.first_name', read_only=True)
    class Meta:
        model = FlaggedContent
        fields = [
            'reason', 'is_resolved', 'resolved_by', 'resolved_at', 'resolution_note',
            'created_at', 'modified_at'
        ]

class UserModerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModeration
        fields = [
            'warning_count', 'notes'
        ]


class ProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    member_since = serializers.SerializerMethodField()
    badges = BadgeSerializer(many=True, source='user_badges', read_only=True)
    moderation = serializers.SerializerMethodField()
    flags = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    trust_score = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()
    edit_day = serializers.SerializerMethodField()
    profile_completion = serializers.SerializerMethodField()
    missing_fields = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = [
            'full_name', 'email', 'phone', 'profile_picture',
            'points', 'matric_number', 'student_id_verified', 'student_id_verified_status',
            'department', 'faculty', 'level',
            'member_since', 'hall_residence', 'hall_number',
            'email_verified', 'hall_verified', 'hall_verified_status',
            'badges', 'flags', 'moderation',
            'trust_score', 'avg_rating', 'review_count',
            'profile_completion', 'missing_fields',
            'notification', 'visibility', 'edit_day', 'modified_at'
        ]

    def get_member_since(self, obj):
        return obj.created_at.year if obj.created_at else None

    def get_trust_score(self, obj):
        avg = self.get_avg_rating(obj) or 0
        return round((avg / 5) * 100, 1)

    def get_avg_rating(self, obj):
        # Use cached average_rating field
        return float(obj.average_rating) if obj.average_rating else 0.0

    def get_review_count(self, obj):
        return obj.reviews_received.filter(is_deleted=False).count()
    
    def get_edit_day(self, obj):
        return ConstantHelper.USER_EDIT_DAY
    
    def get_profile_completion(self, obj):
        data = calculate_profile_completion(obj)
        return data['percentage']

    def get_missing_fields(self, obj):
        data = calculate_profile_completion(obj)
        return data['missing_fields']

    def get_moderation(self, obj):
        mod, created = UserModeration.objects.get_or_create(user=obj)
        print(mod)
        return UserModerationSerializer(mod).data

    def get_flags(self, obj):
        flags = FlaggedContent.objects.filter(
            content_type=ContentTypeEnum.USER.value,
            content_id=obj.id,
        )
        return FlaggedContentSerializer(flags, many=True).data
    

class ProfileUpdateSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(required=True, write_only=True)
    class Meta:
        model = User
        fields = [
            'full_name', 'phone', 'department', 'faculty', 'level',
            'matric_number'
        ]

    def validate_full_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Full name is required.")
        return value.strip()

    def validate_phone(self, value):
        if value and not value.strip():
            return None
        return value

    def validate_level(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Level must be a positive integer.")
        return value


class ProfilePictureSerializer(serializers.Serializer):
    profile_picture = serializers.ImageField(
        required=True    )
    

class UploadStudentIdSerializer(serializers.Serializer):
    student_id = serializers.ImageField(
        required=True    )

class HallVerificationSerializer(serializers.Serializer):
    hall_number = serializers.CharField(max_length=300, required=True)
    hall_residence = serializers.CharField(max_length=300, required=True)


class ToggleTwoFactorMethodSerializer(serializers.Serializer):
    two_factor_Type = serializers.CharField(max_length=300, required=True)


class VerifyTotpSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6)

class TwoFALoginSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    code = serializers.CharField(max_length=20, min_length=6)
    platform = serializers.CharField(required=False, default='web')
    method = serializers.CharField(required=False, default='totp')