from apps.users.BBL.Commands.notification import NotificationCommand
from apps.users.BBL.Commands.profile import ProfileCommand
from apps.users.BBL.Commands.two_factor import TwoFactorCommand
from apps.users.BBL.Queries.notification import NotificationQueries
from apps.users.BBL.Queries.profile import ProfileQuery
from apps.users.BBL.Queries.two_factor import TwoFactorQuery
from apps.users.serializers import (BuyPointSerializer, ChangePasswordSerializer, 
            ConfirmResetPasswordSerializer, HallVerificationSerializer, LogoutSerializer, 
            ProfilePictureSerializer, ProfileSerializer, ProfileUpdateSerializer, 
            RefreshTokenSerializer, ReportSerializer, ResendVerificationEmailSerializer, 
            RetryPurchaseSerailizer, ToggleTwoFactorMethodSerializer, TwoFALoginSerializer, UploadStudentIdSerializer, 
            UserCreationSerializer, UserForgotPasswordSerializer, UserLoginSerializer, VerifyTotpSerializer)
from common.throttling.enums import UserTypeEnum
from common.throttling.throttler import CustomRateThrottle
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView, status
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.shortcuts import render
from django.conf import settings
from apps.users.BBL.Queries.FlutterConfirm import FlutterwaveConfirmQuery
from apps.users.BBL.Queries.PaystackConfirm import PaystackConfirmQuery
from apps.users.BBL.Queries.point_packages import PointPackagesQueries
from utils.base_result import BaseResultWithData
from utils.enums import GroupNamesEnum, PlatformEnum
from utils.helpers import UpdatePointsService
from utils.permissions import ConstantPermission
from .BBL.Commands.account_command import AccountCommand
from .BBL.Commands.auth_command import AuthCommand
from .BBL.Commands.report_command import ReportCommand
from .BBL.Commands.buy_points import BuyPointsCommand
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.parsers import MultiPartParser, FormParser


# ──────────────────────────────────────────────
# PUBLIC VIEWS (AllowAny)
# ──────────────────────────────────────────────

class CreateAccountView(generics.GenericAPIView):
    """Create a new user account"""
    serializer_class = UserCreationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [CustomRateThrottle(rate=5, period=3600, user_type=UserTypeEnum.ANON)]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AccountCommand.Execute(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class VerifyAccountEmailView(APIView):
    """Verify user email using verification token"""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [CustomRateThrottle(rate=20, period=60, user_type=UserTypeEnum.ANON)]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('token', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Token"),
        ]
    )
    def get(self, request):
        result = AccountCommand.VerifyEmail(request)
        context = {
            'message': result.message,
            'is_success': result.is_success,
            'BASE_FRONTEND_URL': settings.BASE_FRONTEND_URL
        }
        return render(request, 'email-verification.html', context)


class ResendVerificationEmailView(generics.GenericAPIView):
    """Allow user to resend verification link"""
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = ResendVerificationEmailSerializer
    throttle_classes = [CustomRateThrottle(rate=3, period=3600, user_type=UserTypeEnum.ANON)]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AccountCommand.ResendEmail(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class VerifyForgetPasswordEmailView(APIView):
    """Verify user email for forgot password using verification token"""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [CustomRateThrottle(rate=20, period=60, user_type=UserTypeEnum.ANON)]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('token', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Token"),
        ]
    )
    def get(self, request):
        result = AuthCommand.VerifyForgetPasswordEmail(request)
        context = {
            'message': result.message,
            'data': result.data,
            'is_success': result.is_success
        }
        return render(request, 'password-reset-verification.html', context)


class ConfirmResetPasswordView(generics.GenericAPIView):
    """Confirm reset password using verification token"""
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = ConfirmResetPasswordSerializer
    throttle_classes = [CustomRateThrottle(rate=5, period=3600, user_type=UserTypeEnum.ANON)]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthCommand.ConfirmResetPassword(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class LoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [CustomRateThrottle(rate=10, period=300, user_type=UserTypeEnum.ANON)]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthCommand.Execute(request, serializer.validated_data)
        if result.status_code != 200:
            return Response(result.to_dict(), status=result.status_code)
        response = Response(result.to_dict(), status=result.status_code)
        access_token = result.data.get('access_token')
        refresh_token = result.data.get('refresh_token')
        if not result.data.get('requires_2fa'):
            if result.data.get('platform') == PlatformEnum.WEB.value:
                access_lifetime_seconds = int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds())
                refresh_lifetime_seconds = int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())
                response.set_cookie(
                    'access_token',
                    access_token,
                    httponly=True,
                    secure=settings.COOKIE_SECURE,
                    samesite=settings.COOKIE_SAMESITE,
                    max_age=access_lifetime_seconds,
                    path='/',
                )
                response.set_cookie(
                    'refresh_token',
                    refresh_token,
                    httponly=True,
                    secure=settings.COOKIE_SECURE,
                    samesite=settings.COOKIE_SAMESITE,
                    max_age=refresh_lifetime_seconds,
                    path='/',
                )

        return response
    

class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = UserForgotPasswordSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [CustomRateThrottle(rate=5, period=3600, user_type=UserTypeEnum.ANON)]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthCommand.ForgotPassword(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class RefreshTokenView(generics.GenericAPIView):
    serializer_class = RefreshTokenSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [CustomRateThrottle(rate=20, period=60, user_type=UserTypeEnum.ANON)]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthCommand.RefreshToken(request, serializer.validated_data)
        if result.status_code != 200:
            response = Response(result.to_dict(), status=result.status_code)
            self._clear_auth_cookies(response)
            return response
        
        response = Response(result.to_dict(), status=result.status_code)
        access_token = result.data.get('access_token')
        refresh_token = result.data.get('refresh_token')

        access_lifetime_seconds = int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds())
        refresh_lifetime_seconds = int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())

        response.set_cookie(
            'access_token',
            access_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=access_lifetime_seconds,
            path='/',
        )
        response.set_cookie(
            'refresh_token',
            refresh_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=refresh_lifetime_seconds,
            path='/',
        )
        return response
    

    def _clear_auth_cookies(self, response):
        """Expire both access and refresh HttpOnly cookies."""
        response.set_cookie(
            'access_token',
            '',
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=0,
            expires='Thu, 01 Jan 1970 00:00:00 GMT',
            path='/',
        )
        response.set_cookie(
            'refresh_token',
            '',
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=0,
            expires='Thu, 01 Jan 1970 00:00:00 GMT',
            path='/',
        )


class SubmitReportView(generics.GenericAPIView):
    serializer_class = ReportSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [CustomRateThrottle(rate=10, period=3600, user_type=UserTypeEnum.ANON)]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ReportCommand.Add(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


# Payment gateway callback views – high limit to avoid blocking gateways
class PaystackPointsConfirmView(APIView):
    throttle_classes = [CustomRateThrottle(rate=100, period=60, user_type=UserTypeEnum.ANON)]

    def get(self, request, reference, *args, **kwargs):
        result = PaystackConfirmQuery.execute(reference)
        context = {
            'message': result.message,
            'data': result.data,
            'is_success': result.is_success,
            'BASE_FRONTEND_URL': settings.BASE_FRONTEND_URL
        }
        return render(request, 'payment-confirmation.html', context)


class MonnifyPointsConfirmView(APIView):
    """Handle Monnify payment confirmation"""
    throttle_classes = [CustomRateThrottle(rate=100, period=60, user_type=UserTypeEnum.ANON)]

    def get(self, request, reference, *args, **kwargs):
        # TODO: Implement Monnify validation
        return Response(
            {
                "status": "pending",
                "message": "Monnify payment confirmation - Implementation in progress",
                "reference": reference,
                "gateway": "monnify"
            },
            status=status.HTTP_200_OK
        )


class FlutterwavePointsConfirmView(APIView):
    """Handle Flutterwave payment confirmation"""
    throttle_classes = [CustomRateThrottle(rate=100, period=60, user_type=UserTypeEnum.ANON)]

    def get(self, request, reference, *args, **kwargs):
        result = FlutterwaveConfirmQuery.execute(reference)
        context = {
            'message': result.message,
            'data': result.data,
            'is_success': result.is_success,
            'BASE_FRONTEND_URL': settings.BASE_FRONTEND_URL
        }
        return render(request, 'payment-confirmation.html', context)


# ──────────────────────────────────────────────
# AUTHENTICATED VIEWS (IsAuthenticated)
# ──────────────────────────────────────────────

class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=5, period=3600, user_type=UserTypeEnum.AUTH)]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthCommand.ChangePassword(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class LogoutUserView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=20, period=60, user_type=UserTypeEnum.AUTH)]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        platform = serializer.validated_data.get('platform')
        refresh_token_str = None
        if platform == PlatformEnum.WEB.value:
            refresh_token_str = request.COOKIES.get('refresh_token')                
        else:
            refresh_token_str = serializer.validated_data.get('refresh_token')
        if not refresh_token_str:
            return Response(
                    {"message": "Refresh token required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        try:
            token = RefreshToken(refresh_token_str)
            token.blacklist()
            response = Response({"message": "Logged out successfully"}, status=200)
            self._clear_auth_cookies(response)
            return response
        except TokenError:
            return Response({"error": "Invalid or expired token"}, status=400)
        

    def _clear_auth_cookies(self, response):
        """Expire both access and refresh HttpOnly cookies."""
        response.set_cookie(
            'access_token',
            '',
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=0,
            expires='Thu, 01 Jan 1970 00:00:00 GMT',
            path='/',
        )
        response.set_cookie(
            'refresh_token',
            '',
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=0,
            expires='Thu, 01 Jan 1970 00:00:00 GMT',
            path='/',
        )
        
        

class RefreshPointBalanceView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def get(self, request):
        points = UpdatePointsService.check_points(request.user)
        result = BaseResultWithData(
            message="Points refreshed successfully",
            data={'points_balance': points},
            status_code=200
        )
        return Response(result.to_dict(), status=result.status_code)


class GetTransactionView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=20, period=60, user_type=UserTypeEnum.AUTH)]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('transaction_type', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('reference', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('date_from', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('per_page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request):
        result = PointPackagesQueries.get_transactions(request, request.GET.dict())
        return Response(result.to_dict(), status=result.status_code)
    

class GetPointPurchasedView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=20, period=60, user_type=UserTypeEnum.AUTH)]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('reference', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('gateway', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('completed_at', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('points_awarded', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('date_from', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('per_page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request):
        result = PointPackagesQueries.get_purchases(request, request.GET.dict())
        return Response(result.to_dict(), status=result.status_code)
    

class PointPackagesView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=20, period=60, user_type=UserTypeEnum.AUTH)]
    def get(self, request):
        result = PointPackagesQueries.get_point_packages()
        return Response(result.to_dict(), status=result.status_code)
        


class BuyPointView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    serializer_class = BuyPointSerializer
    throttle_classes = [CustomRateThrottle(rate=10, period=3600, user_type=UserTypeEnum.AUTH)]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = BuyPointsCommand.execute(request, request.user, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class RetryPurchaseView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    serializer_class = RetryPurchaseSerailizer
    throttle_classes = [CustomRateThrottle(rate=5, period=3600, user_type=UserTypeEnum.AUTH)]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = BuyPointsCommand.payment_retry(request, request.user, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ProfileView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return ProfileUpdateSerializer
        return ProfileSerializer

    def get(self, request, *args, **kwargs):
        result = ProfileQuery.get_profile_detail(request, request.user)
        return Response(result.to_dict(), status=result.status_code)

    def put(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ProfileCommand.update_profile(request, request.user, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class GetStudentIDView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    def get(self, request, *args, **kwargs):
        result = ProfileQuery.get_student_id_record(request, request.user)
        return Response(result.to_dict(), status=result.status_code)


class GetStudentHallRecordView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    def get(self, request, *args, **kwargs):
        result = ProfileQuery.get_student_hall_verification_record(request, request.user)
        return Response(result.to_dict(), status=result.status_code)


class GetStudentVisibilityView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    def get(self, request, *args, **kwargs):
        result = ProfileQuery.get_student_visibility(request, request.user)
        return Response(result.to_dict(), status=result.status_code)


class AddStudentHallView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    serializer_class = HallVerificationSerializer
    throttle_classes = [CustomRateThrottle(rate=10, period=300, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ProfileCommand.add_student_hall(request, request.user, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ToggleVisibilityView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=10, period=300, user_type=UserTypeEnum.AUTH)]
    def patch(self, request, *args, **kwargs):
        result = ProfileCommand.toggle_visibilty(request, request.user)
        return Response(result.to_dict(), status=result.status_code)

    

class UploadProfilePictureView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    serializer_class = ProfilePictureSerializer
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [CustomRateThrottle(rate=10, period=300, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ProfileCommand.update_profile_picture(request, request.user, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class UploadStudentIdView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    serializer_class = UploadStudentIdSerializer
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [CustomRateThrottle(rate=10, period=300, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ProfileCommand.upload_student_id(request, request.user, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class GetAllNotificationsView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('is_read', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('per_page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request, *args, **kwargs):
        result = NotificationQueries.get_notification(request, request.user, request.GET.dict())
        return Response(result.to_dict(), status=result.status_code)


class GetNotificationsHeaderView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=40, period=60, user_type=UserTypeEnum.AUTH)]

    def get(self, request, *args, **kwargs):
        result = NotificationQueries.get_notifications_header(request, request.user)
        return Response(result.to_dict(), status=result.status_code)


class NotificationMarkAsReadView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def put(self, request, notification_id):
        result = NotificationCommand.mark_as_read(request.user, notification_id)
        return Response(result.to_dict(), status=result.status_code)


class MarkAllNotificationAsReadView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=10, period=300, user_type=UserTypeEnum.AUTH)]

    def put(self, request):
        result = NotificationCommand.mark_all_as_read(request.user)
        return Response(result.to_dict(), status=result.status_code)


class NotificationDeleteView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=20, period=60, user_type=UserTypeEnum.AUTH)]

    def delete(self, request, notification_id):
        result = NotificationCommand.delete_notification(request.user, notification_id)
        return Response(result.to_dict(), status=result.status_code)


class DeleteAllNotificationView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=5, period=3600, user_type=UserTypeEnum.AUTH)]

    def delete(self, request):
        result = NotificationCommand.delete_all_notifications(request.user)
        return Response(result.to_dict(), status=result.status_code)


# ─── 1. Toggle 2FA Setup (authenticated) ──────────────────────────
class ToggleTwoFASetupView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=100, period=300, user_type=UserTypeEnum.AUTH)]
    serializer_class = ToggleTwoFactorMethodSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = TwoFactorCommand.toggle_setup(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


# ─── 2. Verify TOTP (authenticated) ───────────────────────────────
class VerifyTwoFAView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [CustomRateThrottle(rate=100, period=60, user_type=UserTypeEnum.AUTH)]
    serializer_class = VerifyTotpSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = TwoFactorCommand.verify_totp(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


# ─── 3. TOTP Login Step (public) ──────────────────────────────────
class TwoFALoginView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [CustomRateThrottle(rate=100, period=60, user_type=UserTypeEnum.ANON)]
    serializer_class = TwoFALoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = TwoFactorCommand._2fa_verify_login(request, serializer.validated_data)
        if result.status_code != 200:
            return Response(result.to_dict(), status=result.status_code)
        response = Response(result.to_dict(), status=result.status_code)
        access_token = result.data.get('access_token')
        refresh_token = result.data.get('refresh_token')
        if result.data.get('platform') == PlatformEnum.WEB.value:
            access_lifetime_seconds = int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds())
            refresh_lifetime_seconds = int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())
            response.set_cookie(
                'access_token',
                access_token,
                httponly=True,
                secure=settings.COOKIE_SECURE,
                samesite=settings.COOKIE_SAMESITE,
                max_age=access_lifetime_seconds,
                path='/',
            )
            response.set_cookie(
                'refresh_token',
                refresh_token,
                httponly=True,
                secure=settings.COOKIE_SECURE,
                samesite=settings.COOKIE_SAMESITE,
                max_age=refresh_lifetime_seconds,
                path='/',
            )

        return response




# ─── 4. Disable All 2FA (authenticated) ───────────────────────────
class Disable2FAView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [CustomRateThrottle(rate=100, period=300, user_type=UserTypeEnum.AUTH)]

    def post(self, request):
        result = TwoFactorCommand.disable_2fa(request)
        return Response(result.to_dict(), status=result.status_code)
    

class GetUser2FAMethodsView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [CustomRateThrottle(rate=100, period=300, user_type=UserTypeEnum.AUTH)]

    def get(self, request):
        result = TwoFactorQuery.get_user_2fa_methods(request)
        return Response(result.to_dict(), status=result.status_code)