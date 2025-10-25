from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView
from django.shortcuts import redirect
from .models import User
from .forms import ReaderSignUpForm, JournalistSignUpForm, EditorSignUpForm
from publications.models import Publication
from articles.models import Article
from subscriptions.models import Subscription
from core.mixins import PaginationMixin


class SignUpReaderView(CreateView):
    """
    Allows registration for reader accounts, then assigns the
    reader role.

    - param: CreateView, provides user creation form and logic.
    - return: redirects to home page upon successful registration.
    """
    model = User
    form_class = ReaderSignUpForm
    template_name = "users/signup_reader.html"
    success_url = reverse_lazy("home")

    def get_form(self, form_class=None):
        """
        Returns readers signup form.

        - param: form_class, optional form class to use.
        - return: form instance with updated widget attributes.
        """
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        return form

    def form_valid(self, form):
        """
        Process a valid reader signup form.

        - param: form, validated user registration form.
        - return: redirect to home page.
        """
        user = form.save(commit=False)
        user.role = "reader"
        user.save()
        login(self.request, user)
        return redirect(self.success_url)


class SignUpJournalistView(CreateView):
    """
    Handles registration for journalist accounts and assigns the user
    to the journalist group.

    - param: CreateView, provides user creation form and logic.
    - return: redirects to home page upon successful registration.
    """
    model = User
    form_class = JournalistSignUpForm
    template_name = "users/signup_journalist.html"
    success_url = reverse_lazy("home")

    def get_form(self, form_class=None):
        """
        Returns journalist signup form.

        - param: form_class, optional form class to use.
        - return: form instance with updated widget attributes.
        """
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        return form

    def form_valid(self, form):
        """
        Process a valid journalist signup form.

        - param: form, validated user registration form.
        - return: redirect to home page.
        """
        user = form.save(commit=False)
        user.role = "journalist"
        user.save()
        login(self.request, user)
        return redirect(self.success_url)


class SignUpEditorView(CreateView):
    """
    Handles registration for editor accounts.

    Assigns the editor role to new users.

    - param: CreateView, provides user creation form and logic.
    - return: redirects to home page upon successful registration.
    """
    model = User
    form_class = EditorSignUpForm
    template_name = "users/signup_editor.html"
    success_url = reverse_lazy("home")

    def get_form(self, form_class=None):
        """
        Returns editor signup form.

        - param: form_class, optional form class to use.
        - return: form instance with updated widget attributes.
        """
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        return form

    def form_valid(self, form):
        """
        Process a valid editor signup form.

        - param: form, validated user registration form.
        - return: redirect to home page.
        """
        user = form.save(commit=False)
        user.role = "editor"
        user.save()
        login(self.request, user)
        return redirect(self.success_url)


class CustomLoginView(LoginView):
    """
    Custom login for all users.

    - param: LoginView, provides built-in authentication functionality.
    - return: renders login page and handles authentication.
    """
    template_name = "users/login.html"

    def get_form(self, form_class=None):
        """
        Gets the login form.

        - param: form_class, optional form class to use.
        - return: form instance with updated widget attributes.
        """
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        return form


class CustomLogoutView(LogoutView):
    """
    Custom logout view.

    - param: LogoutView, provides built-in logout functionality.
    - return: redirects to the home page after logout.
    """
    next_page = reverse_lazy("home")

    def dispatch(self, request, *args, **kwargs):
        """
        Add logout confirmation message before redirecting.

        - param: request, the current HTTP request.
        - param: *args, positional arguments.
        - param: **kwargs, keyword arguments.
        - return: response redirecting to the next page after logout.
        """
        messages.info(request, "You’ve been signed out successfully.")
        return super().dispatch(request, *args, **kwargs)


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    Displays a user's profile page.

    Readers have limited content shown.
    Journalists see their articles.
    Editors see their managed publications.

    - param: LoginRequiredMixin, ensures the user is authenticated.
    - param: TemplateView, provides template rendering.
    - return: renders user profile with personalized content.
    """
    template_name = "users/profile.html"

    def get_context_data(self, **kwargs):
        """
        Add user-specific data to the profile page.

        - For journalists: includes their articles.
        - For editors: includes publications they manage.
        - param: **kwargs, additional context arguments.
        - return: context dictionary with user-specific content.
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["articles"] = (
            user.articles.all()
            if user.role == "journalist" and hasattr(user, "articles")
            else Article.objects.none()
            )
        context["publications"] = (
            user.edited_publications.all()
            if user.role == "editor"
            else Publication.objects.none()
            )
        return context


class ReaderDashboardView(LoginRequiredMixin, PaginationMixin, TemplateView):
    """
    Displays the reader's dashboard.
    Shows and allows management of their active subscriptions to
    publications and journalists.

    - param: LoginRequiredMixin, ensures the user is logged in.
    - param: PaginationMixin, enables pagination for subscriptions.
    - param: TemplateView, provides dashboard rendering.
    - return: renders the reader dashboard page.
    """
    template_name = "users/reader_dashboard.html"
    paginate_by = 10

    def get_context_data(self, **kwargs):
        """
        Add paginated publication and journalist subscriptions to the context.

        - Splits pagination between publications and journalists.
        - param: **kwargs, additional context arguments.
        - return: dictionary with subscription data and pagination objects.
        """
        context = super().get_context_data(**kwargs)
        (paginator_pub, page_obj_pub, publication_subs,
         is_paginated_pub) = self.paginate_queryset(
             Subscription.objects.filter(subscriber=self.request.user,
                                         publication__isnull=False
                                         ).select_related("publication"
                                                          ), self.paginate_by,
                                                          )

        (paginator_jour, page_obj_jour, journalist_subs,
         is_paginated_jour) = self.paginate_queryset(
            Subscription.objects.filter(subscriber=self.request.user,
                                        journalist__isnull=False
                                        ).select_related("journalist"
                                                         ), self.paginate_by,
                                                           )

        context.update({
            "publication_subs": publication_subs,
            "journalist_subs": journalist_subs,
            "paginator_pub": paginator_pub,
            "page_obj_pub": page_obj_pub,
            "is_paginated_pub": is_paginated_pub,
            "paginator_jour": paginator_jour,
            "page_obj_jour": page_obj_jour,
            "is_paginated_jour": is_paginated_jour,
            })
        return context


def editor_profile(request, editor_id):
    """
    Displays the public profile of an editor.

    Shows all publications managed by the editor.

    - param: request, the current HTTP request.
    - param: editor_id, the ID of the editor to display.
    - return: rendered editor profile template with publications and articles.
    """
    editor = get_object_or_404(User, id=editor_id, role="editor")

    # All publications this editor manages
    publications = (
        Publication.objects.filter(editors=editor)
        .distinct()
        .order_by("name")
        )

    # All articles under those publications
    articles = (
        Article.objects.filter(publication__in=publications)
        .select_related("publication", "author")
        .order_by("-published_at")
    )

    context = {
        "editor": editor,
        "publications": publications,
        "articles": articles,
    }
    return render(request, "users/editor_profile.html", context)


def journalist_profile(request, journalist_id):
    """
    Displays the public profile of a journalist.

    Shows all published articles authored by the journalist, lists all
    publications they have written forand indicates whether the current
    reader is subscribed to this journalist.

    - param: request, the current HTTP request.
    - param: journalist_id, the ID of the journalist to display.
    - return: rendered journalist profile template with articles and
      subscription info.
    """
    journalist = get_object_or_404(User, id=journalist_id, role="journalist")

    articles = (
        Article.objects.filter(author=journalist, status="published")
        .select_related("publication")
        .order_by("-published_at")
    )

    # All publications they’ve written for
    publications = (
        Publication.objects.filter(articles__author=journalist)
        .distinct()
        .order_by("name")
    )

    # Check if current reader is subscribed
    is_subscribed = False
    if request.user.is_authenticated and request.user.role == "reader":
        is_subscribed = journalist.journalist_subscriptions.filter(
            subscriber=request.user
            ).exists()

    context = {
        "journalist": journalist,
        "articles": articles,
        "publications": publications,
        "is_subscribed": is_subscribed,
    }
    return render(request, "users/journalist_profile.html", context)


@login_required
def reader_profile(request):
    """
    Displays the reader's profile page.

    Shows their active subscriptions to publications and journalists.

    - param: request, the current HTTP request.
    - return: rendered reader profile template with subscription data.
    """
    if request.user.role != "reader":
        return render(request, "users/profile.html")

    publication_subs = Subscription.objects.filter(
        subscriber=request.user, publication__isnull=False
    ).select_related("publication")

    journalist_subs = Subscription.objects.filter(
        subscriber=request.user, journalist__isnull=False
    ).select_related("journalist")

    context = {
        "publication_subs": publication_subs,
        "journalist_subs": journalist_subs,
    }
    return render(request, "users/reader_profile.html", context)
