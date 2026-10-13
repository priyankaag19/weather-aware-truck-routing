from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers


class PlaceSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)
    label = serializers.CharField(required=False, allow_blank=True, default="")


class AnalyzeSerializer(serializers.Serializer):
    origin = PlaceSerializer()
    destination = PlaceSerializer()
    departure = serializers.DateTimeField()
    load_lb = serializers.IntegerField(min_value=0, max_value=200_000)
    interval_mi = serializers.ChoiceField(choices=[10, 25, 50], default=25)

    def validate_departure(self, value):
        now = timezone.now()
        if value < now - timedelta(days=1):
            raise serializers.ValidationError("Departure can be at most 24 hours in the past.")
        if value > now + timedelta(days=10):
            raise serializers.ValidationError("Forecasts are only available up to 10 days ahead.")
        return value

    def validate(self, attrs):
        o, d = attrs["origin"], attrs["destination"]
        if abs(o["lat"] - d["lat"]) < 1e-4 and abs(o["lng"] - d["lng"]) < 1e-4:
            raise serializers.ValidationError("Origin and destination must be different places.")
        return attrs
