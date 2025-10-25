from django.db import models
from django.conf import settings
from publications.models import Publication

User = settings.AUTH_USER_MODEL


class Subscription(models.Model):
    """
    Readers can subscribe to publications and or individual journalist.
    """
    subscriber = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="subscriptions"
        )
    publication = models.ForeignKey(
        Publication, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="subscriptions",
        )
    journalist = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="journalist_subscriptions",
        )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """
        Ensure each (subscriber, publication) is unique,
        and each (subscriber, journalist) is unique.
        """
        unique_together = ("subscriber", "publication", "journalist")

    def clean_sub(self):
        """
        Ensure only one target (publication OR journalist) is chosen.
        """
        if not self.publication and not self.journalist:
            raise ValueError(
                "Please specify either a publication or a journalist."
            )
        if self.publication and self.journalist:
            raise ValueError(
                "Please subscribe to either a publication or a "
                "journalist, not both."
            )

    def __str__(self):
        if self.publication:
            return f"{self.subscriber.email} | {self.publication.name}"
        if self.journalist:
            return f"{self.subscriber.email} | {self.journalist.email}"
        return f"{self.subscriber.email} | (no target)"
