from apps.campus.models import Review
from rest_framework import serializers
from utils.constant_helper import ConstantHelper
from utils.helpers import calculate_profile_completion, humanize_date
from .models import Badge, PointTransaction, User
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

class RetryPurchaseSerailizer(serializers.Serializer):
    purchase_id = serializers.CharField(max_length=200, required=True)



class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ['name', 'icon', 'description']

class ReviewForProfileSerializer(serializers.ModelSerializer):
    from_user_name = serializers.CharField(source='from_user.get_full_name', read_only=True)
    date = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['from_user_name', 'rating', 'comment', 'date']

    def get_date(self, obj):
        return humanize_date(obj.created_at)


class TransactionForProfileSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    description = serializers.CharField()
    date = serializers.DateTimeField(source='created_at')
    balance = serializers.IntegerField(source='balance_after')

    class Meta:
        model = PointTransaction
        fields = ['type', 'amount', 'description', 'date', 'balance']

    def get_type(self, obj):
        return 'credit' if obj.amount > 0 else 'debit'

class ProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    member_since = serializers.SerializerMethodField()
    badges = BadgeSerializer(many=True, source='user_badges', read_only=True)
    trust_score = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    transactions = serializers.SerializerMethodField()
    edit_day = serializers.SerializerMethodField()
    profile_completion = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = [
            'full_name', 'email', 'phone', 'profile_picture',
            'points', 'matric_number', 'student_id_verified',
            'department', 'faculty', 'level',
            'member_since',
            'email_verified', 'hall_verified',
            'badges',
            'trust_score', 'avg_rating', 'review_count',
            'reviews', 'transactions', 'profile_completion',
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

    def get_reviews(self, obj):
        # Get latest 10 reviews received
        reviews = obj.reviews_received.filter(is_deleted=False).order_by('-created_at')[:10]
        return ReviewForProfileSerializer(reviews, many=True).data

    def get_transactions(self, obj):
        # Get latest 10 transactions
        transactions = obj.point_transactions.order_by('-created_at')[:10]
        return TransactionForProfileSerializer(transactions, many=True).data
    
    def get_edit_day(self, obj):
        return ConstantHelper.USER_EDIT_DAY
    
    def get_profile_completion(self, obj):
        return calculate_profile_completion(obj)
    

class ProfileUpdateSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(required=True, write_only=True)
    class Meta:
        model = User
        fields = [
            'full_name', 'phone', 'department', 'faculty', 'level',
            'matric_number', 'notification', 'visibility'
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
    