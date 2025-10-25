from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class Publication(models.Model):
    """
    Represents a publication or news outlet.
    Editors manage publications, including approving articles for posting.
    Users with role of Journalists can request to become a
    writer for Publications.
    """
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    editors = models.ManyToManyField(
        User, related_name="edited_publications", blank=True
    )
    journalists = models.ManyToManyField(
        User, related_name="joined_publications", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def has_pending_request(self, user):
        """
        Check if this user already has a pending join request.
        """
        return self.join_requests.filter(
            user=user, status="pending").exists()

    def __str__(self):
        return self.name


class JoinRequest(models.Model):
    """
    A journalist's request to join a publication.
    Editors then approve or reject.
    """
    publication = models.ForeignKey(
        Publication, on_delete=models.CASCADE, related_name="join_requests"
        )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="publication_requests"
        )
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ],
        default="pending",
        )
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (f"{self.user.full_name} | {self.user.email} | "
                f"{self.publication.name} ({self.status})")
