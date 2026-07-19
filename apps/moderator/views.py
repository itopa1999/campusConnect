from apps.moderator.BBL.Commands.get_dashboard import DashboardQuery
from common.throttling.enums import UserTypeEnum
from rest_framework.response import Response
from rest_framework import generics
from rest_framework.views import APIView
from common.throttling.throttler import CustomRateThrottle
from rest_framework.permissions import AllowAny, IsAuthenticated
from utils.enums import GroupNames
from utils.permissions import ConstantPermission


class GetDashboardView(APIView):
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=30, period=60, user_type=UserTypeEnum.AUTH)]
    def get(self, request):
        result = DashboardQuery.get_dashboard(request)
        return Response(result.to_dict(), status=result.status_code)