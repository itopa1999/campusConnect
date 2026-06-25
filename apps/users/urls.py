from django.urls import path, include
from .views import *


urlpatterns = [
    path("auth/", include([
        path("register", CreateAccountView.as_view(), name="register"),
        path("verify-email", VerifyAccountEmailView.as_view(), name="verify_email"),
        path("resend-verification", ResendVerificationEmailView.as_view(), name="resend_email"),
        path("verify-forget-password-email", VerifyForgetPasswordEmailView.as_view(), name="verify_forget_password_email"),
        path("confirm-reset-password", ConfirmResetPasswordView.as_view(), name="confirm_reset_password"),
        path("login-user", LoginView.as_view(), name="login_user"),
        path("forgot-password", ForgotPasswordView.as_view(), name="forgot_password"),
        path("change-password", ChangePasswordView.as_view(), name="change_password"),
        path("logout-user", LogoutUserView.as_view(), name="logout_user"),
        path("refresh-token", RefreshTokenView.as_view(), name="refresh_token"),


        path("point-packages", PointPackagesView.as_view(), name="point_packages"),
        path("buy-points-initial", BuyPointView.as_view(), name="buy_points_initial"),
        path('paystack-points-confirm/<str:reference>', PaystackPointsConfirmView.as_view(), name='paystack-points-confirm'),
        path('monnify-confirm/<str:reference>', MonnifyPointsConfirmView.as_view(), name='monnify-confirm'),
        path('flutterwave-points-confirm/<str:reference>', FlutterwavePointsConfirmView.as_view(), name='flutterwave-points-confirm'),
        path('retry-purchase', RetryPurchaseView.as_view(), name='retry-payment')   
    ])),
    path("report/", include([
        path("submit", SubmitReportView.as_view(), name="submit_contact_report"),
    ])),
    path("", RefreshPointBalanceView.as_view(), name='refresh_token'),
]