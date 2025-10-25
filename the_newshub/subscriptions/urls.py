from django.urls import path
from . import views

urlpatterns = [
    path(
        "subscribe/publication/<int:publication_id>/",
        views.subscribe_publication, name="subscribe_publication",
        ),
    path(
        "unsubscribe/publication/<int:publication_id>/",
        views.unsubscribe_publication, name="unsubscribe_publication",
        ),
    path(
        "subscribe/journalist/<int:journalist_id>/",
        views.subscribe_journalist, name="subscribe_journalist",
        ),
    path(
        "unsubscribe/journalist/<int:journalist_id>/",
        views.unsubscribe_journalist, name="unsubscribe_journalist",
        ),
]
