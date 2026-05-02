from django.urls import path, include
from .views import *


urlpatterns = [
    path(
        "auth/",
        include(
            [
                path("register/", CreateAccountView.as_view(), name="register"),
                path("verify-email/", VerifyAccountEmailView.as_view(), name="verify_email"),
                path("", LoginView.as_view(), name="login"),
                path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
                path("change-password/", ChangePasswordView.as_view(), name="change_password"),
            ]
        )
    )
]