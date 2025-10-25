from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from django_ckeditor_5.fields import CKEditor5Field

User = settings.AUTH_USER_MODEL


class Article(models.Model):
    """
    Model for articles and newsletters.

    STATUS_CHOICES:
        - The current stage of the article or newsletter.

    TYPE_CHOICES:
        - If the content is an article or newsletter.

    Fields:
        - title: CharField, the title of article or newsletter.
        - slug: SlugField, the slug for article or newslettee.
        - author: ForiegnKey, the article or newsletters full name.
        - publication: ForiegnKey, the publication the author belongs to
          if the article or newsletter wasn't an independently published.
        - type: CharField, choice if content is a newesletter or an article.
        - status: CharField, the current status, from draft to
          published or rejected.
        - content: TextField, content or newsletter.
        - feedback: TextField, feedback from editor if applicable.
        - created_at: DateTimeField, when the article was created.
        - updated_at: DateTimeField, when the article was modified.
        - published_at: DateTimeField, when the article was published.
    """
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending_approval", "Pending Approval"),
        ("published", "Published"),
        ("rejected", "Rejected"),
        ]

    TYPE_CHOICES = [
        ("article", "Article"),
        ("newsletter", "Newsletter"),
        ]

    title = models.CharField(max_length=300)
    slug = models.SlugField(unique=True, blank=True)
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="articles"
        )
    publication = models.ForeignKey(
        "publications.Publication", on_delete=models.CASCADE,
        related_name="articles", null=True, blank=True,
        )
    type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default="article",
        help_text=("Choose 'Article' for multi-block content, "
                   "or 'Newsletter' for simple text content.")
        )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
        )
    content = CKEditor5Field("Content", config_name="default", blank=True)
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        """
        Override the default save method.

        - Automatically generates a unique slug if not provided.
        - Automatically sets `published_at` when status is 'published'.

        - param: *args, positional arguments passed to the parent save method.
        - param: **kwargs, keyword arguments passed to the parent save method.
        - return: None.
        """
        if not self.slug:
            self.slug = slugify(f"{self.title}-{timezone.now().timestamp()}")

        # Automatically set published_at when publishing
        if self.status == "published" and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def average_rating(self):
        """
        Returns the average score (1-5) for this article.
        If no ratings exist, returns 0.

        - param: none.
        - return: float representing the average rating rounded
          to 1 decimal place.
        """
        ratings = self.ratings.all()
        if ratings.exists():
            return round(sum(r.score for r in ratings) / ratings.count(), 1)
        return 0

    def __str__(self):
        return (
            f"{self.title} ({self.get_type_display()} - "
            f"{self.get_status_display()})"
            )


class Comment(models.Model):
    """
    Model for comments under  each article.

    Fields:
        - article: ForiegnKey, the article the comment belongs to.
        - user: ForiegnKey, the user the comment belongs to.
        - text: TextField, the comment text.
        - created_at: DateTimeField, the date when the comment was created.
    """
    article = models.ForeignKey(
        Article, related_name="comments", on_delete=models.CASCADE
        )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comment by {self.user} on {self.article}"


class Rating(models.Model):
    """
    For users to rate articles.

    Fields:
        - article: ForiegnKey, the aricle to be rated.
        - user: ForiegnKey, user who gave the rating.
        - score: PositiveIntegerField, the out of 5 score.
    """
    article = models.ForeignKey(
        Article, related_name="ratings", on_delete=models.CASCADE
        )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ("article", "user")

    def __str__(self):
        return f"{self.score}★ by {self.user.display_name or self.user.email}"
