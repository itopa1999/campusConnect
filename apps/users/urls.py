from django.urls import path, include
from .views import *


urlpatterns = [
    path("auth/", include([
        path("register", CreateAccountView.as_view(), name="register"),
        path("verify-email", VerifyAccountEmailView.as_view(), name="verify_email"),
        path("verify-forget-password-email", VerifyForgetPasswordEmailView.as_view(), name="verify_forget_password_email"),
        path("confirm-reset-password", ConfirmResetPasswordView.as_view(), name="confirm_reset_password"),
        path("login-user", LoginView.as_view(), name="login_user"),
        path("forgot-password", ForgotPasswordView.as_view(), name="forgot_password"),
        path("change-password", ChangePasswordView.as_view(), name="change_password"),
        path("logout-user", LogoutUserView.as_view(), name="logout_user"),
        path("refresh-token", RefreshTokenView.as_view(), name="refresh_token"),
    ])),
    path("report/", include([
        path("submit", SubmitReportView.as_view(), name="submit_contact_report"),
    ])),
    path("", ReturnOkay.as_view()),
]