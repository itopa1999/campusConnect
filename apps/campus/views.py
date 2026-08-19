from apps.campus.BBL.Commands.favourite import FavouriteCommand
from apps.campus.BBL.Queries.favourite import FavouriteQuery
from apps.campus.serializers import (ClaimSerializer, ListingAutoActivationSerializer, ListingSerializer, ListingUpdateSerializer, LostAndFoundSerializer, UpdateAdsViewSerializer, UploadListingImageSerializer)
from common.throttling.enums import UserTypeEnum
from common.throttling.throttler import CustomRateThrottle
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import generics
from rest_framework.views import APIView
from apps.campus.BBL.Commands.lost_and_found import LostandFoundCommand
from apps.campus.BBL.Queries.get_dashboard import DashboardQuery
from apps.campus.BBL.Queries.get_lookup import LookUpQuery
from apps.campus.BBL.Queries.index_products import IndexProductsQuery
from apps.campus.BBL.Commands.listing import ListingCommand
from apps.campus.BBL.Queries.listing import ListingQuery
from apps.campus.BBL.Queries.lost_and_found import GetLostItemsQuery
from django.shortcuts import render
from django.conf import settings
from utils.enums import GroupNamesEnum
from utils.helpers import run_async
from utils.permissions import ConstantPermission
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import asyncio

# ──────────────────────────────────────────────
# PUBLIC VIEWS
# ──────────────────────────────────────────────

class GetIndexDefaultListingView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [CustomRateThrottle(rate=60, period=60, user_type=UserTypeEnum.ANON)]
    
    def get(self, request):
        result = IndexProductsQuery.get_index_product(request)
        return Response(result.to_dict(), status=result.status_code)


# ──────────────────────────────────────────────
# AUTHENTICATED VIEWS
# ──────────────────────────────────────────────

class LostAndFoundView(generics.GenericAPIView):
    serializer_class = LostAndFoundSerializer
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=5, period=3600, user_type=UserTypeEnum.AUTH)]
    parser_classes = [MultiPartParser, FormParser]
    def post(self, request):
        result = LostandFoundCommand.create_item(request.user, request.data)
        return Response(result.to_dict(), status=result.status_code)


class LostAndFoundListView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('per_page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request):
        result = run_async(GetLostItemsQuery.get_items(request, request.GET.dict()))
        return Response(result.to_dict(), status=result.status_code)


class LostAndFoundClaimView(generics.GenericAPIView):
    serializer_class = ClaimSerializer
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=10, period=3600, user_type=UserTypeEnum.ANON)]
    
    def post(self, request):
        result = LostandFoundCommand.create_claim(request, request.data)
        return Response(result.to_dict(), status=result.status_code)


class ApproveClaimView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=10, period=3600, user_type=UserTypeEnum.ANON)]    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('claim_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Claim ID"),
            openapi.Parameter('email', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Email address")
        ]
    )
    def get(self, request):
        result = LostandFoundCommand.approve_claim(request)
        context = {
            'message': result.message,
            'is_success': result.is_success,
            'BASE_FRONTEND_URL': settings.BASE_FRONTEND_URL
        }
        return render(request, 'claim-approve.html', context)



class GetDashboardView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    def get(self, request):
        result = run_async(DashboardQuery.get_dashboard(request))
        return Response(result.to_dict(), status=result.status_code)


class GetDashboardReviewsView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('per_page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request):
        result = result = run_async(DashboardQuery.get_dashboard_reviews(request, request.GET.dict()))
        return Response(result.to_dict(), status=result.status_code)
    


class GetDashboardListingView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('per_page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request):
        result = run_async(DashboardQuery.get_dashboard_listing(request, request.GET.dict()))
        return Response(result.to_dict(), status=result.status_code)
    

class GetDashboardUpCommingExpirationListingView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    def get(self, request):
        result = run_async(DashboardQuery.get_expiring_listing(request))
        return Response(result.to_dict(), status=result.status_code)


class GetLookUpView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=20, period=60, user_type=UserTypeEnum.AUTH)]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('is_category', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('is_subcategory', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('is_hotspot', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('is_condition_choices', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('is_type_choices', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('is_advert_type', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
        ]
    )
    def get(self, request):
        result = run_async(LookUpQuery.get_lookup(request, request.GET.dict()))
        return Response(result.to_dict(), status=result.status_code)


class ListingView(generics.GenericAPIView):
    serializer_class = ListingSerializer
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [CustomRateThrottle(rate=10, period=3600, user_type=UserTypeEnum.AUTH)]
    
    def post(self, request):
        result = ListingCommand.create_listing(request.user, request.data)
        return Response(result.to_dict(), status=result.status_code)


class MarkAsSoldView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=20, period=60, user_type=UserTypeEnum.AUTH)]
    
    def patch(self, request, listing_id):
        result = ListingCommand.mark_sold(request.user, listing_id)
        return Response(result.to_dict(), status=result.status_code)


class UploadImageView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    serializer_class = UploadListingImageSerializer
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [CustomRateThrottle(rate=10, period=300, user_type=UserTypeEnum.AUTH)]
    
    def patch(self, request, listing_id):
        result = ListingCommand.image_upload(request.user, listing_id, request.FILES.get('image'))
        return Response(result.to_dict(), status=result.status_code)


class ListingDetailView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [
        CustomRateThrottle(rate=60, period=600, user_type=UserTypeEnum.AUTH, scope="listing_detail_get"),
    ]
    
    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return ListingUpdateSerializer
        return None
    
    def get(self, request, listing_id):
        result = run_async(ListingQuery.get_listing_detail(request, request.user, listing_id))
        return Response(result.to_dict(), status=result.status_code)
    
    def put(self, request, listing_id):
        # Override throttle for write operations
        self.throttle_classes = [CustomRateThrottle(rate=15, period=300, user_type=UserTypeEnum.AUTH)]
        self.check_throttles(request)
        result = ListingCommand.update_listing(request.user, listing_id, request.data, partial=False)
        return Response(result.to_dict(), status=result.status_code)

    def patch(self, request, listing_id):
        self.throttle_classes = [CustomRateThrottle(rate=15, period=300, user_type=UserTypeEnum.AUTH)]
        self.check_throttles(request)
        result = ListingCommand.reactivate_listing(request.user, listing_id)
        return Response(result.to_dict(), status=result.status_code)

    def delete(self, request, listing_id):
        self.throttle_classes = [CustomRateThrottle(rate=5, period=300, user_type=UserTypeEnum.AUTH)]
        self.check_throttles(request)
        result = ListingCommand.delete_listing(request.user, listing_id)
        return Response(result.to_dict(), status=result.status_code)


class UpdateAdsView(generics.GenericAPIView):
    serializer_class = UpdateAdsViewSerializer
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=5, period=300, user_type=UserTypeEnum.AUTH)]
    
    def patch(self, request, listing_id):
        result = ListingCommand.update_ads(request.user, listing_id, request.data, partial=False)
        return Response(result.to_dict(), status=result.status_code)


class ListingAutoActivation(generics.GenericAPIView):
    serializer_class = ListingAutoActivationSerializer
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=5, period=300, user_type=UserTypeEnum.AUTH)]
    
    def patch(self, request, listing_id):
        result = ListingCommand.listing_auto_reactivation(request.user, listing_id, request.data, partial=False)
        return Response(result.to_dict(), status=result.status_code)


class CategorizedListingsView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=40, period=60, user_type=UserTypeEnum.AUTH)]    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('section', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('max_price', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('category_name', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('condition', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('search_query', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('date_from', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('per_page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request):
        result = run_async(ListingQuery.get_categorized_listings(request, request.user, request.GET.dict()))
        return Response(result.to_dict(), status=result.status_code)


class ListingDetailsView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=60, period=60, user_type=UserTypeEnum.AUTH)]
    
    def get(self, request, listing_id):
        result = run_async(ListingQuery.listing_details(request, listing_id))
        return Response(result.to_dict(), status=result.status_code)


class ToggleFavouriteListingView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=60, period=60, user_type=UserTypeEnum.AUTH)]
    
    def post(self, request, listing_id):
        result = FavouriteCommand.toggle_favourite(request.user, listing_id)
        return Response(result.to_dict(), status=result.status_code)



class ListFavouriteListingView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.STUDENT.value)]
    throttle_classes = [CustomRateThrottle(rate=60, period=60, user_type=UserTypeEnum.AUTH)]
    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('per_page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request):
        result = run_async(
            FavouriteQuery.get_favourites(request, request.GET.dict())
        )
        return Response(result.to_dict(), status=result.status_code)