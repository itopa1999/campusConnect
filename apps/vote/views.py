from apps.vote.BLL.Commands.category import CategoryCommand
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.vote.serializers import PollCategoryCreateUpdateSerializer
from common.throttling.enums import UserTypeEnum
from common.throttling.throttler import CustomRateThrottle
from utils.enums import GroupNamesEnum
from utils.permissions import ConstantPermission


class CategoryCreateView(generics.GenericAPIView):
    """Create category"""
    serializer_class = PollCategoryCreateUpdateSerializer
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=5, period=3600, user_type=UserTypeEnum.AUTH)]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = CategoryCommand.create_category(request, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class CategoryUpdateView(generics.GenericAPIView):
    """Update category"""
    serializer_class = PollCategoryCreateUpdateSerializer
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=10, period=3600, user_type=UserTypeEnum.AUTH)]

    def patch(self, request, category_id: int):
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        result = CategoryCommand.update_category(request, category_id, serializer.validated_data)
        return Response(result.to_dict(), status=result.status_code)


class CategoryToggleView(generics.GenericAPIView):
    """Toggle category status (delete/restore)"""
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNamesEnum.MODERATOR.value)]
    throttle_classes = [CustomRateThrottle(rate=5, period=3600, user_type=UserTypeEnum.AUTH)]

    def delete(self, request, category_id: int):
        result = CategoryCommand.toggle_category_status(request, category_id)
        return Response(result.to_dict(), status=result.status_code)
