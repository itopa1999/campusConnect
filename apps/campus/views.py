from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import generics
from rest_framework.views import APIView
from apps.campus.BBL.Queries.get_dashboard import DashboardQuery
from apps.campus.BBL.Queries.index_products import IndexProductsQuery

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