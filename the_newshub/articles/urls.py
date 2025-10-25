from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (ArticleViewSet, ArticleCreateView, ArticleUpdateView,
                    ArticleDeleteView, SubmitForApprovalView,
                    PendingArticlesView, ApproveArticleView, RejectArticleView,
                    ArticleListView, ArticleDetailView, RatingViewSet,
                    JournalistDashboardView, CommentViewSet
                    )

router = DefaultRouter()
router.register("articles", ArticleViewSet, basename="article")
router.register("comments", CommentViewSet, basename="comment")
router.register("ratings", RatingViewSet, basename="rating")

urlpatterns = [
    # Web views for readers
    path("create/", ArticleCreateView.as_view(), name="article_create"),
    path("", ArticleListView.as_view(), name="article_list"),
    path("<slug:slug>/", ArticleDetailView.as_view(), name="article_detail"),

    # Journalist views

    path("<int:pk>/edit/", ArticleUpdateView.as_view(), name="article_edit"),
    path("<int:pk>/delete/", ArticleDeleteView.as_view(),
         name="article_delete"
         ),
    path("<int:pk>/submit/", SubmitForApprovalView.as_view(),
         name="article_submit"
         ),
    path("journalist/dashboard/", JournalistDashboardView.as_view(),
         name="journalist_dashboard"
         ),

    # Editor views
    path("pending/", PendingArticlesView.as_view(), name="pending_articles"),
    path("<int:pk>/approve/", ApproveArticleView.as_view(),
         name="article_approve"
         ),
    path("<int:pk>/reject/", RejectArticleView.as_view(),
         name="article_reject"
         ),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
]

urlpatterns += router.urls
