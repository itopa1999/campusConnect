from apps.moderator.BBL.Commands.category import CategoryCommand
from apps.moderator.BBL.Commands.hotspot import HotspotCommand
from apps.moderator.BBL.Commands.listing import ListingCommand
from apps.moderator.BBL.Commands.lost_and_found import LostAndFoundCommand
from apps.moderator.BBL.Commands.report import ReportCommand
from apps.moderator.BBL.Commands.review import ReviewCommand
from apps.moderator.BBL.Commands.user import UserCommand
from apps.moderator.BBL.Queries.category import CategoryQuery
from apps.moderator.BBL.Queries.get_dashboard import DashboardQuery
from apps.moderator.BBL.Queries.hotspot import HotspotQuery
from apps.moderator.BBL.Queries.listing import ListingQuery
from apps.moderator.BBL.Queries.lost_and_found import LostAndFoundQuery
from apps.moderator.BBL.Queries.report import ReportQuery
from apps.moderator.BBL.Queries.review import ReviewQuery
from apps.moderator.BBL.Queries.user import UserQuery
from apps.moderator.serializers import ModCategorySerializer, ModHotspotSerializer, ReasonSerializer, ReportAssignSerializer, ReportEscalateSerializer, ReportReopenSerializer, ReportResolveSerializer, ResolutionNoteSerializer, UserSuspensionSerializer
from common.throttling.enums import UserTypeEnum
from rest_framework.response import Response
from rest_framework import generics
from rest_framework.views import APIView
from common.throttling.throttler import CustomRateThrottle
from rest_framework.permissions import AllowAny, IsAuthenticated
from utils.enums import GroupNamesEnum
from utils.permissions import ConstantPermission
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class ModeratorDashboardStatsView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    def get(self, request):
        result = DashboardQuery.get_dashboard_stats(request)
        return Response(result.to_dict(), status=result.status_code)
    

class ModeratorListingListView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('category_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('listing_type', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('is_flagged', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('is_deleted', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('date_from', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('per_page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request):
        result = ListingQuery.get_all_listings(request, request.GET.dict())
        return Response(result.to_dict(), status=result.status_code)
    

class ModeratorListingDetailView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def get(self, request, listing_id):
        result = ListingQuery.get_listing_detail(request, listing_id)
        return Response(result.to_dict(), status=result.status_code)
    

class ModeratorListingApproveView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReasonSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, listing_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ListingCommand.approve_listing(request, listing_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)

class ModeratorListingRejectView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReasonSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, listing_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ListingCommand.reject_listing(request, listing_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorListingToggleDeleteView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReasonSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, listing_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ListingCommand.toggle_delete_listing(request, listing_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorListingToggleHideView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReasonSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, listing_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ListingCommand.toggle_hide_listing(request, listing_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorListingToggleFlagView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ResolutionNoteSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, listing_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ListingCommand.toggle_flag_listing(request, listing_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorLostItemListView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('is_flagged', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('is_deleted', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('date_from', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('per_page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request):
        result = LostAndFoundQuery.get_all_lost_items(request, request.GET.dict())
        return Response(result.to_dict(), status=result.status_code)
    

class ModeratorLostItemDetailView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def get(self, request, lost_item_id):
        result = LostAndFoundQuery.get_lost_item_detail(request, lost_item_id)
        return Response(result.to_dict(), status=result.status_code)
    

class ModeratorLostItemApproveView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReasonSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, lost_item_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = LostAndFoundCommand.approve_lost_item(request, lost_item_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)

class ModeratorLostItemRejectView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReasonSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, lost_item_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = LostAndFoundCommand.reject_lost_item(request, lost_item_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorLostItemToggleDeleteView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReasonSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, lost_item_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = LostAndFoundCommand.toggle_delete_lost_item(request, lost_item_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorLostItemToggleHideView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReasonSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, lost_item_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = LostAndFoundCommand.toggle_hide_lost_item(request, lost_item_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorLostItemToggleFlagView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ResolutionNoteSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, lost_item_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = LostAndFoundCommand.toggle_flag_lost_item(request, lost_item_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)



class ModeratorReviewListView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('from_user_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('to_user_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('listing_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('rating', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('is_flagged', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('is_deleted', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('date_from', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('per_page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request):
        result = ReviewQuery.get_all_reviews(request, request.GET.dict())
        return Response(result.to_dict(), status=result.status_code)


class ModeratorReviewDetailView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def get(self, request, review_id):
        result = ReviewQuery.get_review_detail(request, review_id)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorReviewToggleDeleteView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReasonSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, review_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ReviewCommand.toggle_delete_review(request, review_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorReviewToggleFlagView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReasonSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, review_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ReviewCommand.toggle_flag_review(request, review_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)
    

class ModeratorUserListView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('department', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('is_suspended', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('is_banned', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('is_active', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('is_flagged', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('is_deleted', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('date_from', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('per_page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request):
        result = UserQuery.get_all_users(request, request.GET.dict())
        return Response(result.to_dict(), status=result.status_code)


class ModeratorUserDetailView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def get(self, request, user_id):
        result = UserQuery.get_user_detail(request, user_id)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorUserWarningView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReasonSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def post(self, request, user_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = UserCommand.issue_warning(request, user_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorUserToggleSuspendView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = UserSuspensionSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, user_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = UserCommand.toggle_suspend_user(request, user_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorUserToggleBanView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReasonSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, user_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = UserCommand.toggle_ban_user(request, user_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorUserToggleDeleteView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReasonSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, user_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = UserCommand.toggle_delete_user(request, user_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)
    

class ModeratorReportListView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('issue_type', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('assigned_to', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('escalated_to_admin', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('date_from', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('per_page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request):
        result = ReportQuery.get_all_reports(request, request.GET.dict())
        return Response(result.to_dict(), status=result.status_code)


class ModeratorReportDetailView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def get(self, request, report_id):
        result = ReportQuery.get_report_detail(request, report_id)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorReportResolveView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReportResolveSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, report_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ReportCommand.resolve_report(request, report_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorReportEscalateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReportEscalateSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, report_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ReportCommand.escalate_report(request, report_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorReportAssignView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReportAssignSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, report_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ReportCommand.assign_report(request, report_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorReportReopenView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReportReopenSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, report_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ReportCommand.toggle_reopen_report(request, report_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)
    

class ModeratorCategoriesListView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('per_page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request):
        result = CategoryQuery.get_all_categories(request, request.GET.dict())
        return Response(result.to_dict(), status=result.status_code)


class ModeratorCategoryDetailView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def get(self, request, category_id):
        result = CategoryQuery.get_category_detail(request, category_id)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorCreateCategoryView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ModCategorySerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = CategoryCommand.create_category(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)



class ModeratorUpdateCategoryView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ModCategorySerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]

    def put(self, request, category_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = CategoryCommand.update_category(request, category_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)



class ModeratorCategoryToggleDeleteView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReasonSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    def patch(self, request, category_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = CategoryCommand.toggle_delete_category(request, category_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorHotspotListView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('per_page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request):
        result = HotspotQuery.get_all_hotspots(request, request.GET.dict())
        return Response(result.to_dict(), status=result.status_code)


class ModeratorHotspotDetailView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    def get(self, request, hotspot_id):
        result = HotspotQuery.get_hotspot_id_detail(request, hotspot_id)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorCreateHotspotView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ModHotspotSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = HotspotCommand.create_hotspot(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorUpdateHotspotView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ModHotspotSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    def put(self, request, hotspot_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = HotspotCommand.update_hotspot(request, hotspot_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class ModeratorHotspotToggleDeleteView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    serializer_class = ReasonSerializer
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    def patch(self, request, hotspot_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = HotspotCommand.toggle_delete_hotspot(request, hotspot_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)

