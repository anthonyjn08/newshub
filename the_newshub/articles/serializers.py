from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Article, Comment, Rating

User = get_user_model()


class ArticleSerializer(serializers.ModelSerializer):
    """
    Article serializer.
    """
    author_name = serializers.CharField(
        source="author.full_name", read_only=True
        )

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "type",
            "content",
            "status",
            "feedback",
            "author_name",
            "publication",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["author_name", "status"]

    def create(self, validated_data):
        """
        Automatically assign author and set publication status:
        - Independent articles (no publication) auto-publish.
        - Publication-linked articles go to pending approval.
        """
        user = self.context["request"].user
        validated_data["author"] = user

        publication = validated_data.get("publication")
        if publication:
            validated_data["status"] = "pending_approval"
        else:
            validated_data["status"] = "published"

        article = Article.objects.create(**validated_data)
        return article


class CommentSerializer(serializers.ModelSerializer):
    """
    Serializer for user comments.
    """
    user_display = serializers.ReadOnlyField(source="user.display_name")

    class Meta:
        model = Comment
        fields = [
            "id", "article", "user", "user_display", "text", "created_at"
            ]


class RatingSerializer(serializers.ModelSerializer):
    """
    Serializer for user ratings.
    """
    user_display = serializers.ReadOnlyField(source="user.display_name")

    class Meta:
        model = Rating
        fields = ["id", "article", "user", "user_display", "score"]

    def validate(self, data):
        user = self.context["request"].user
        article = data["article"]
        if Rating.objects.filter(article=article, user=user).exists():
            raise serializers.ValidationError(
                "You have already rated this article."
                )
        return data
