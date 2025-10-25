from rest_framework import serializers
from .models import Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            "id", "subscriber", "publication",
            "journalist", "created_at",
            ]
        read_only_fields = ["subscriber", "created_at"]

    def validate(self, data):
        publication = data.get("publication")
        journalist = data.get("journalist")

        if not publication and not journalist:
            raise serializers.ValidationError(
                "Please specify either a publication or journalist."
            )
        if publication and journalist:
            raise serializers.ValidationError(
                "Please choose only one: publication or journalist."
            )
        return data
