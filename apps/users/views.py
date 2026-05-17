
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.shortcuts import render
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


class ReturnOkay(generics.GenericAPIView):
    serializer_class = None
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response()