from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views
from .views import (PublicationListView, PublicationDetailView,
                    PublicationCreateView, PublicationUpdateView,
                    PublicationDeleteView, EditorDashboardView,
                    ApproveArticleView, RejectArticleView,
                    JoinPublicationView, JoinRequestListView,
                    ApproveJoinRequestView, RejectJoinRequestView,
                    JoinRequestViewSet, ArticleReviewView,
                    PublicationArticlesView
                    )


# DRF router for API endpoints
router = DefaultRouter()
router.register("publications", views.PublicationViewSet,
                basename="publication")
router.register(r'join-requests', JoinRequestViewSet, basename='join-requests')

urlpatterns = [
    path("create/", PublicationCreateView.as_view(),
         name="publication_create_view"
         ),

    path("editor/dashboard/", EditorDashboardView.as_view(),
         name="editor_dashboard"
         ),
    path("", PublicationListView.as_view(), name="publication_list"),
    path("publications/<int:pk>", PublicationDetailView.as_view(),
         name="publication_detail"
         ),
    path("<int:pk>/join/", JoinPublicationView.as_view(),
         name="join_publication"
         ),
    path("editor/join-requests/", JoinRequestListView.as_view(),
         name="join_requests_list"
         ),
    path("editor/join-requests/<int:pk>/approve/",
         ApproveJoinRequestView.as_view(), name="approve_join_request"
         ),
    path("editor/join-requests/<int:pk>/reject/",
         RejectJoinRequestView.as_view(), name="reject_join_request"
         ),
    path("editor/article/<int:pk>/review/", ArticleReviewView.as_view(),
         name="editor_review_article"),

    # Editor Views
    path("<int:pk>/edit/", PublicationUpdateView.as_view(),
         name="publication_edit"
         ),
    path("<int:pk>/delete/", PublicationDeleteView.as_view(),
         name="publication_delete"
         ),

    path("editor/article/<int:pk>/approve/", ApproveArticleView.as_view(),
         name="editor_approve_article"
         ),
    path("editor/article/<int:pk>/reject/", RejectArticleView.as_view(),
         name="editor_reject_article"
         ),
    path("editor/publication/<int:pk>/articles/",
         PublicationArticlesView.as_view(), name="editor_publication_articles",
         ),
]

urlpatterns += router.urls
