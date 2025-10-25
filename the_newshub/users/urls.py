from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (SignUpReaderView, SignUpJournalistView, SignUpEditorView,
                    CustomLoginView, ProfileView, ReaderDashboardView,
                    journalist_profile, reader_profile
                    )

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="home"), name="logout"),
    path("signup/reader/", SignUpReaderView.as_view(), name="signup_reader"),
    path("signup/journalist/",
         SignUpJournalistView.as_view(), name="signup_journalist"
         ),
    path("signup/editor/", SignUpEditorView.as_view(), name="signup_editor"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("journalist/<int:journalist_id>/",
         journalist_profile, name="journalist_profile"),
    path("reader/profile/", reader_profile, name="reader_profile"),
    path("reader/dashboard/", ReaderDashboardView.as_view(),
         name="reader_dashboard"),
]
