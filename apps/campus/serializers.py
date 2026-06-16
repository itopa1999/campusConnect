

from rest_framework import serializers
from django.core.exceptions import ValidationError
from apps.campus.models import Listing, Category, CampusHotspot
from apps.users.models import User

class ListingSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_deleted=False),
        write_only=True
    )
    hotspots = serializers.PrimaryKeyRelatedField(
        queryset=CampusHotspot.objects.filter(is_deleted=False),
        many=True,
        write_only=True,
        required=True
    )
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Listing
        fields = [
            'id', 'title', 'description', 'price', 'listing_type',
            'badge', 'status', 'expires_at', 'image',
            'category', 'hotspots'
        ]
        read_only_fields = ['id', 'status', 'expires_at']

    def create(self, validated_data):
        hotspots = validated_data.pop('hotspots', [])
        listing = Listing.objects.create(**validated_data)
        listing.hotspots.set(hotspots)
        return listing