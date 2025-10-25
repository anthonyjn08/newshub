"""
URL configuration for the_newshub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView)
from articles.urls import router as articles_router
from articles.views import (
    HomeView, ArticleViewSet,
    CommentViewSet, RatingViewSet
    )
from publications.views import PublicationViewSet

router = DefaultRouter()
router.register(r"articles", ArticleViewSet, basename="article")
router.register(r"comments", CommentViewSet, basename="comment")
router.register(r"ratings", RatingViewSet, basename="rating")
router.register(r"publications", PublicationViewSet,
                basename="publication")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", HomeView.as_view(), name="home"),
    path("users/", include("users.urls")),
    path("articles/", include("articles.urls")),
    path("publications/", include("publications.urls")),
    path("subscriptions/", include("subscriptions.urls")),

    # DRF API endpoints
    path("api/", include(router.urls)),
    path("api/auth/token/", TokenObtainPairView.as_view(),
         name="token_obtain_pair"
         ),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(),
         name="token_refresh"
         ),
    path("api/", include(articles_router.urls)),
    # CKEditor
    path("ckeditor5/", include("django_ckeditor_5.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
