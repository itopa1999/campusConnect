from django.urls import path, include

from apps.users.views import (AddStudentHallView, BuyPointView, ChangePasswordView, ConfirmResetPasswordView, CreateAccountView, DeleteAllNotificationView, 
                              FlutterwavePointsConfirmView, ForgotPasswordView, GetAllNotificationsView, GetNotificationsHeaderView, GetPointPurchasedView, GetStudentHallRecordView, GetStudentIDView, GetTransactionView, LoginView, LogoutUserView, 
                              MarkAllNotificationAsReadView, MonnifyPointsConfirmView, NotificationDeleteView, NotificationMarkAsReadView, 
                              PaystackPointsConfirmView, PointPackagesView, ProfileView, RefreshPointBalanceView, RefreshTokenView, 
                              ResendVerificationEmailView, RetryPurchaseView, SubmitReportView, UploadProfilePictureView, UploadStudentIdView, 
                              VerifyAccountEmailView, VerifyForgetPasswordEmailView
                            )

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

        path('profile', ProfileView.as_view(), name='profile'),
        path('profile-student-id', GetStudentIDView.as_view(), name='profile_student_id'),
        path('profile-student-hall', GetStudentHallRecordView.as_view(), name='profile_student_hall'),
        path('add-student-hall', AddStudentHallView.as_view(), name='add_student_hall'),
        path('profile-picture', UploadProfilePictureView.as_view(), name='profile_picture'),
        path('upload-student-id', UploadStudentIdView.as_view(), name='upload-student-id'),


        path("point-packages", PointPackagesView.as_view(), name="point_packages"),
        path("get-transactions", GetTransactionView.as_view(), name="get_transactions"),
        path("get-purchase", GetPointPurchasedView.as_view(), name="get_purchases"),
        path("buy-points-initial", BuyPointView.as_view(), name="buy_points_initial"),
        path('paystack-points-confirm/<str:reference>', PaystackPointsConfirmView.as_view(), name='paystack-points-confirm'),
        path('monnify-confirm/<str:reference>', MonnifyPointsConfirmView.as_view(), name='monnify-confirm'),
        path('flutterwave-points-confirm/<str:reference>', FlutterwavePointsConfirmView.as_view(), name='flutterwave-points-confirm'), 
        path('retry-purchase', RetryPurchaseView.as_view(), name='retry-payment') 
    ])),
    path("report/", include([
        path("submit", SubmitReportView.as_view(), name="submit_contact_report"),
    ])),

    path("notifications/", include([
        path("", GetAllNotificationsView.as_view(), name="get_all_notifications"),
        path("mark-read/<int:notification_id>", NotificationMarkAsReadView.as_view(), name="mark_read_notifications"),
        path("all-mark-read", MarkAllNotificationAsReadView.as_view(), name="mark_all_read_notifications"),
        path("delete/<int:notification_id>", NotificationDeleteView.as_view(), name="delete_notifications"),
        path("delete-all", DeleteAllNotificationView.as_view(), name="delete_all_notifications"),
        path("header", GetNotificationsHeaderView.as_view(), name="get_notifications_header"),
    ])),


    path("", RefreshPointBalanceView.as_view(), name='refresh_token'),
]