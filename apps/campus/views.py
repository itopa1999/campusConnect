from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import generics
from rest_framework.views import APIView
from apps.campus.BBL.Queries.get_dashboard import DashboardQuery
from apps.campus.BBL.Queries.get_lookup import LookUpQuery
from apps.campus.BBL.Queries.index_products import IndexProductsQuery
from apps.campus.BBL.Commands.lisiting import ListingCommand
from apps.campus.BBL.Queries.listing import GetListingDetailQuery
from apps.campus.serializers import *

# Create your views here.

class GetIndexDefaultLisitingView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        result = IndexProductsQuery.get_index_product()
        return Response(result.to_dict(), status=result.status_code)

class GetDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = DashboardQuery.get_dashboard(request)
        return Response(result.to_dict(), status=result.status_code)
    

class GetLookUpView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = LookUpQuery.get_lookup(request)
        return Response(result.to_dict(), status=result.status_code)
    

class ListingView(generics.GenericAPIView):
    serializer_class = ListingSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        result = ListingCommand.create_listing(request.user, request.data)
        return Response(result.to_dict(), status=result.status_code)

class MarkAsSoldView(APIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, listing_id):
        result = ListingCommand.mark_sold(request.user, listing_id)
        return Response(result.to_dict(), status=result.status_code)
    

class UploadImageView(APIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, listing_id):
        result = ListingCommand.image_upload(request.user, listing_id, )
        return Response(result.to_dict(), status=result.status_code)
    

class ListingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, listing_id):
        result = GetListingDetailQuery.get_listing_detail(request.user, listing_id)
        return Response(result.to_dict(), status=result.status_code)
    
    def put(self, request, listing_id):
        result = ListingCommand.update_listing(request.user, listing_id, request.data, partial=False)
        return Response(result.to_dict(), status=result.status_code)

    def patch(self, request, listing_id):
        result = ListingCommand.reactivate_listing(request.user, listing_id)
        return Response(result.to_dict(), status=result.status_code)

    def delete(self, request, listing_id):
        result = ListingCommand.delete_listing(request.user, listing_id)
        return Response(result.to_dict(), status=result.status_code)