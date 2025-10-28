import sys
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .tweepy import tweet_article
from .models import Article
from subscriptions.models import Subscription


@receiver(post_save, sender=Article)
def handle_article_publication(sender, instance, created, **kwargs):
    """
    Send tweet + email ONLY when an article is actually published.
    - Independent articles (no publication): notify if created as 'published'.
    - Publication articles: notify only when status changes to 'published'
      *after* editor approval.
    """
    # Skip external side effects during tests
    if 'test' in sys.argv:
        return

    # Skip unless the article is now published
    if created and instance.status == "published" and not instance.publication:
        should_notify = True

    # Publication articles: become published later after editor approval
    elif (not created and instance.status == "published"
          and instance.publication):
        should_notify = True

    else:
        should_notify = False

    if not should_notify:
        return

    # --- Notifications ---
    try:
        tweet_article(instance)
    except Exception as e:
        print(f"⚠️ Tweet not sent: {e}")

    if instance.publication:
        subs = Subscription.objects.filter(publication=instance.publication)
    else:
        subs = Subscription.objects.filter(journalist=instance.author)

    emails = sorted({
        s.subscriber.email for s in subs.select_related("subscriber")
        if s.subscriber.email
        })

    if not emails:
        return

    content_type = "newsletter" if instance.type == "newsletter" else "article"
    subject = f"New {content_type.capitalize()}: {instance.title}"
    message = (
        f"A new {content_type} has just been published on The Newshub!\n\n"
        f"Title: {instance.title}\n"
        f"Author: {instance.author.full_name}\n"
        f"Read it on The Newshub 📰"
        )

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL"),
        recipient_list=emails,
        fail_silently=False,
        )
