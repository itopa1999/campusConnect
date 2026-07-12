
from apps.users.BBL.Commands.notification import NotificationCommand
from apps.users.BBL.Commands.profile import ProfileCommand
from apps.users.BBL.Queries.notification import NotificationQueries
from apps.users.BBL.Queries.profile import ProfileQuery
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
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
from utils.enums import GroupNames
from utils.helpers import UpdatePointsService
from utils.permissions import ConstantPermission
from .serializers import *
from .BBL.Commands.account_command import AccountCommand
from .BBL.Commands.auth_command import AuthCommand
from .BBL.Commands.report_command import ReportCommand
from .BBL.Commands.buy_points import BuyPointsCommand


class CreateAccountView(generics.GenericAPIView):
    """Create a new user account"""
    serializer_class = UserCreationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AccountCommand.Execute(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class VerifyAccountEmailView(APIView):
    """Verify user email using verification token"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        token = request.query_params.get('token')
        result = AccountCommand.VerifyEmail(request, token)
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
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AccountCommand.ResendEmail(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)



class VerifyForgetPasswordEmailView(APIView):
    """Verify user email for forgot password using verification token"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        token = request.query_params.get('token')
        result = AuthCommand.VerifyForgetPasswordEmail(request, token)
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

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthCommand.ConfirmResetPassword(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)

class LoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthCommand.Execute(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)
        # response = Response(
        #     {
        #         "is_success": result.is_success,
        #         "message": result.message,
        #         "data": result.data["user"]
        #     },
        #     status=result.status_code
        # )

        # response.set_cookie(
        #     key="access_token",
        #     value=result.data["access_token"],
        #     httponly=True,
        #     secure=False,
        #     samesite="Lax",
        #     max_age=60 * 60,
        #     path="/"
        # )

        # response.set_cookie(
        #     key="refresh_token",
        #     value=result.data["refresh_token"],
        #     httponly=True,
        #     secure=False,
        #     samesite="Lax",
        #     max_age=60 * 60 * 24 * 7,
        #     path="/"
        # )

        # return response



class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = UserForgotPasswordSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthCommand.ForgotPassword(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.STUDENT.value)]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthCommand.ChangePassword(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class RefreshTokenView(generics.GenericAPIView):
    serializer_class = RefreshTokenSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthCommand.RefreshToken(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)

class LogoutUserView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.STUDENT.value)]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh_token = serializer.validated_data['refresh_token']

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logged out successfully"}, status=200)
        except TokenError:
            return Response({"error": "Invalid or expired token"}, status=400)


class SubmitReportView(generics.GenericAPIView):
    serializer_class = ReportSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ReportCommand.Add(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class RefreshPointBalanceView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.STUDENT.value)]

    def get(self, request):
        points = UpdatePointsService.check_points(request.user)
        result = BaseResultWithData(
            message="Points refreshed successfully",
            data={'points_balance': points},
            status_code=200
        )
        return Response(result.to_dict(), status=result.status_code)
    

class PointPackagesView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.STUDENT.value)]

    def get(self, request):
        is_transaction = request.query_params.get('is_transaction', 'false')
        is_purchase = request.query_params.get('is_purchase', 'false')

        # Convert to boolean
        is_transaction_bool = is_transaction.lower() in ('true', '1', 'yes', 'y')
        is_purchase_bool = is_purchase.lower() in ('true', '1', 'yes', 'y')

        # Always include packages
        packages = PointPackagesQueries.get_point_packages(request)

        data = {'point_packages': packages}

        if is_transaction_bool:
            # fetch transactions paginated
            page = request.query_params.get('page', 1)
            per_page = request.query_params.get('per_page', 10)
            txn_result = PointPackagesQueries.get_transactions(request.user, page, per_page)
            if txn_result.is_success:
                data['transactions'] = txn_result.data
            else:
                # handle error? Maybe return error
                return Response(txn_result.to_dict(), status=txn_result.status_code)

        if is_purchase_bool:
            page = request.query_params.get('page', 1)
            per_page = request.query_params.get('per_page', 10)
            purchase_result = PointPackagesQueries.get_purchases(request.user, page, per_page)
            if purchase_result.is_success:
                data['purchases'] = purchase_result.data
            else:
                return Response(purchase_result.to_dict(), status=purchase_result.status_code)

        return Response({
            'is_success': True,
            'message': 'Data retrieved successfully',
            'data': data
        }, status=200)

class BuyPointView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.STUDENT.value)]
    serializer_class = BuyPointSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)        
        result = BuyPointsCommand.execute(request, request.user, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)
    

class PaystackPointsConfirmView(APIView):
    def get(self, request, reference, *args, **kwargs):
        
        result =  PaystackConfirmQuery.execute(reference)

        context = {
            'message': result.message,
            'data': result.data,
            'is_success': result.is_success,
            'BASE_FRONTEND_URL': settings.BASE_FRONTEND_URL
        }
        return render(request, 'payment-confirmation.html', context)
    


class MonnifyPointsConfirmView(APIView):
    """Handle Monnify payment confirmation"""
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
    def get(self, request, reference, *args, **kwargs):
        result = FlutterwaveConfirmQuery.execute(reference)
        context = {
            'message': result.message,
            'data': result.data,
            'is_success': result.is_success,
            'BASE_FRONTEND_URL': settings.BASE_FRONTEND_URL
        }
        return render(request, 'payment-confirmation.html', context)


class RetryPurchaseView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.STUDENT.value)]
    serializer_class = RetryPurchaseSerailizer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)        
        result = BuyPointsCommand.payment_retry(request, request.user, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)
    

class ProfileView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.STUDENT.value)]
    
    def get_serializer_class(self):
        # Use the appropriate serializer based on the HTTP method
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
    

class UploadProfilePictureView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.STUDENT.value)]
    serializer_class = ProfilePictureSerializer

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = ProfileCommand.update_profile_picture(request, request.user, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class UploadStudentIdView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.STUDENT.value)]
    serializer_class = UploadStudentIdSerializer

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = ProfileCommand.upload_student_id(request, request.user, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class GetAllNotificationsView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.STUDENT.value)]

    def get(self, request, *args, **kwargs):
        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 10)
        result = NotificationQueries.get_notification(request, request.user, page=page, per_page=per_page)
        return Response(result.to_dict(), status=result.status_code)


class GetNotificationsHeaderView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.STUDENT.value)]

    def get(self, request, *args, **kwargs):
        result = NotificationQueries.get_notifications_header(request, request.user)
        return Response(result.to_dict(), status=result.status_code)
    

class NotificationMarkAsReadView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.STUDENT.value)]

    def put(self, request, notification_id):
        result = NotificationCommand.mark_as_read(request.user, notification_id)
        return Response(result.to_dict(), status=result.status_code)


class MarkAllNotificationAsReadView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.STUDENT.value)]

    def put(self, request):
        result = NotificationCommand.mark_all_as_read(request.user)
        return Response(result.to_dict(), status=result.status_code)


class NotificationDeleteView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.STUDENT.value)]

    def delete(self, request, notification_id):
        result = NotificationCommand.delete_notification(request.user, notification_id)
        return Response(result.to_dict(), status=result.status_code)


class DeleteAllNotificationView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.STUDENT.value)]

    def delete(self, request):
        result = NotificationCommand.delete_all_notifications(request.user)
        return Response(result.to_dict(), status=result.status_code)
