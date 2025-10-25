from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from .models import Subscription
from publications.models import Publication
from users.models import User


@login_required
def subscribe_publication(request, publication_id):
    """
    Allows a logged-in user to subscribe to a publication.

    Prevents duplicate subscriptions by checking existing records,
    then displays feedback messages for success or if already subscribed.

    - param: request, the current HTTP request.
    - param: publication_id, the ID of the publication to subscribe to.
    - return: redirects back to the referring page or home if no referrer.
    """
    publication = get_object_or_404(Publication, id=publication_id)
    existing = Subscription.objects.filter(
        subscriber=request.user,
        publication=publication
    ).first()

    if existing:
        messages.info(
            request, f"You are already subscribed to {publication.name}."
            )
    else:
        Subscription.objects.create(
            subscriber=request.user, publication=publication
            )
        messages.success(
            request, f"Subscribed to {publication.name} successfully."
            )
    return redirect(request.META.get("HTTP_REFERER", "home"))


@login_required
def unsubscribe_publication(request, publication_id):
    """
    Allows a logged-in user to unsubscribe from a publication.

    Deletes an existing subscription if found then displays feedback
    messages for success or if not subscribed.

    - param: request, the current HTTP request.
    - param: publication_id, the ID of the publication to unsubscribe from.
    - return: redirects back to the referring page or home if no referrer.
    """
    subscription = Subscription.objects.filter(
        subscriber=request.user,
        publication_id=publication_id
    ).first()

    if subscription:
        subscription.delete()
        messages.success(request, "Unsubscribed successfully.")
    else:
        messages.info(request, "You are not subscribed to this publication.")
    return redirect(request.META.get("HTTP_REFERER", "home"))


@login_required
def subscribe_journalist(request, journalist_id):
    """
    Allows a logged-in user to subscribe to a journalist.

    Prevents duplicate subscriptions to journalists. Displays feedback
    messages for success or if already subscribed.

    - param: request, the current HTTP request.
    - param: journalist_id, the ID of the journalist to subscribe to.
    - return: redirects back to the referring page or home if no referrer.
    """
    journalist = get_object_or_404(User, id=journalist_id, role="journalist")
    existing = Subscription.objects.filter(
        subscriber=request.user,
        journalist=journalist
    ).first()

    if existing:
        messages.info(
            request, f"You are already subscribed to {journalist.full_name}."
            )
    else:
        Subscription.objects.create(
            subscriber=request.user, journalist=journalist
            )
        messages.success(
            request, f"Subscribed to {journalist.full_name} successfully."
            )
    return redirect(request.META.get("HTTP_REFERER", "home"))


@login_required
def unsubscribe_journalist(request, journalist_id):
    """
    Allows a logged-in user to unsubscribe from a journalist.

    If found, deletes existing subscription, then displays feedback
    messages for success or if not subscribed.

    - param: request, the current HTTP request.
    - param: journalist_id, the ID of the journalist to unsubscribe from.
    - return: redirects back to the referring page or home if no referrer.
    """
    subscription = Subscription.objects.filter(
        subscriber=request.user,
        journalist_id=journalist_id
    ).first()

    if subscription:
        subscription.delete()
        messages.success(request, "Unsubscribed successfully.")
    else:
        messages.info(request, "You are not subscribed to this journalist.")
    return redirect(request.META.get("HTTP_REFERER", "home"))
