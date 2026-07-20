from rest_framework import serializers

class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=1000,
    )


class ResolutionNoteSerializer(serializers.Serializer):
    resolution_note = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=1000,
    )

    
class UserSuspensionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, max_length=500)
    duration_hours = serializers.IntegerField(required=False, default=24, min_value=1, max_value=720)


class ReportResolveSerializer(serializers.Serializer):
    resolution_notes = serializers.CharField(required=True, max_length=500)

class ReportEscalateSerializer(serializers.Serializer):
    escalated_note = serializers.CharField(required=True, max_length=500)

class ReportAssignSerializer(serializers.Serializer):
    assigned_to = serializers.IntegerField(required=True)

class ReportReopenSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, max_length=500)

class ModCategorySerializer(serializers.Serializer):
    name = serializers.CharField(required=True, max_length=500)
    description = serializers.CharField(required=True, max_length=1000)
    icon = serializers.CharField(required=False, max_length=50)
    sort_order = serializers.IntegerField(required=False)


class ModHotspotSerializer(serializers.Serializer):
    name = serializers.CharField(required=True, max_length=500)
    description = serializers.CharField(required=True, max_length=1000)
    sort_order = serializers.IntegerField(required=False)