from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Publication, JoinRequest

User = get_user_model()


class PublicationSerializer(serializers.ModelSerializer):
    """
    Serializer to create new publications.
    """
    editors = serializers.StringRelatedField(many=True, read_only=True)
    journalists = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Publication
        fields = [
            "id", "name", "description", "editors",
            "journalists", "created_at",
            ]


class JoinRequestSerializer(serializers.ModelSerializer):
    """
    Serialises journalist join requests for the API.
    Provides minimal user info directly rather than relying
    on a user serializer.
    """
    journalist_name = serializers.CharField(source="user.full_name",
                                            read_only=True
                                            )
    journalist_email = serializers.EmailField(source="user.email",
                                              read_only=True
                                              )
    publication_name = serializers.CharField(source="publication.name",
                                             read_only=True
                                             )

    class Meta:
        model = JoinRequest
        fields = [
                "id", "journalist_name", "journalist_email", "publication",
                "publication_name", "message", "status", "feedback",
                "created_at", "reviewed_at",
            ]
        read_only_fields = ["status", "feedback", "created_at", "reviewed_at"]
