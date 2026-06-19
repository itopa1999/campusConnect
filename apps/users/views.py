
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.shortcuts import render

from apps.users.BBL.Queries.point_packages import PointPackagesQueries
from utils.base_result import BaseResultWithData
from utils.helpers import UpdatePointsService
from .serializers import *
from .BBL.Commands.account_command import AccountCommand
from .BBL.Commands.auth_command import AuthCommand
from .BBL.Commands.report_command import ReportCommand


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


class VerifyAccountEmailView(generics.GenericAPIView):
    """Verify user email using verification token"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        token = request.query_params.get('token')
        result = AccountCommand.VerifyEmail(request, token)
        context = {
            'message': result.message,
            'is_success': result.is_success
        }
        return render(request, 'email_verification.html', context)
    

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



class VerifyForgetPasswordEmailView(generics.GenericAPIView):
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
        return render(request, 'password_reset_verification.html', context)


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
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        points = UpdatePointsService.check_points(request.user)
        result = BaseResultWithData(
            message="Points refreshed successfully",
            data={'points_balance': points},
            status_code=200
        )
        return Response(result.to_dict(), status=result.status_code)
    

class PointPackagesView(APIView):
    permission_classes = [IsAuthenticated]

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