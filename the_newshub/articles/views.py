from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import (ListView, CreateView, DetailView,
                                  UpdateView, DeleteView, TemplateView)
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .permissions import ReadOnly
from .forms import ArticleForm
from .models import Article, Comment, Rating
from .serializers import (
    ArticleSerializer, CommentSerializer, RatingSerializer,
    )
from publications.models import Publication
from subscriptions.models import Subscription
from core.mixins import PaginationMixin


class HomeView(TemplateView):
    """
    The sites home page.

    - params: TemplateView, displays view template.
    - return: context, returns articles and newsletters.
    """
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        """
        Returns the context for the home page.

        - param: **kwargs, keyword arguments passed to the view.
        - return: context, a dictionary with latest articles and newsletters.
        """
        context = super().get_context_data(**kwargs)
        context["latest_articles"] = (
            Article.objects.filter(status="published", type="article")
            .order_by("-published_at")[:4]
        )
        context["latest_newsletters"] = (
            Article.objects.filter(status="published", type="newsletter")
            .order_by("-published_at")[:4]
        )
        return context


class ArticleListView(PaginationMixin, ListView):
    """
    Displays a list of published articles and newsletters.

    - param: LoginRequiredMixin, ensures user is logged in to view the list.
    - param: ListView, provides paginated display of articles and newsletters.
    - return: context containing all published articles and newsletters.
    """
    model = Article
    template_name = "articles/article_list.html"
    context_object_name = "articles"
    paginate_by = 10

    def get_queryset(self):
        """
        Returns the queryset for published articles or newsletters.

        - return: queryset filtered by type (if specified) and status.
        """
        queryset = Article.objects.filter(
            status="published").order_by("-published_at")

        article_type = self.request.GET.get("type")
        if article_type in ["article", "newsletter"]:
            queryset = queryset.filter(type=article_type)

        return queryset

    def get_context_data(self, **kwargs):
        """
        Adds separate article and newsletter lists to context.

        - return: context containing published articles and newsletters.
        """
        context = super().get_context_data(**kwargs)
        context["articles_only"] = (
            Article.objects.filter(status="published", type="article")
            .order_by("-published_at")
        )
        context["newsletters_only"] = (
            Article.objects.filter(status="published", type="newsletter")
            .order_by("-published_at")
        )
        return context


class ArticleDetailView(DetailView):
    """
    Displays a detailed view of a published article or newsletter.

    - param: DetailView, renders the detail template.
    - return: renders the detail template with the selected article or
      newsletter.
    """
    model = Article
    template_name = "articles/article_detail.html"
    context_object_name = "article"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        """
        Limits visibility to published items for readers,
        but allows authors to view their own articles/newsletters.

        - return: queryset of visible articles/newsletters.
        """
        qs = Article.objects.all()
        user = self.request.user
        if user.is_authenticated:
            return qs.filter(status="published") | qs.filter(author=user)
        return qs.filter(status="published")

    def get_context_data(self, **kwargs):
        """
        Add subscription information to the context to determine whether
        the current user follows the journalist or publication.

        - param: **kwargs, additional context arguments.
        - return: context dictionary with subscription flags.
        """
        context = super().get_context_data(**kwargs)
        article = self.get_object()
        user = self.request.user

        # default values
        context["is_subscribed_pub"] = False
        context["is_subscribed_jour"] = False

        if user.is_authenticated:
            # check if reader is subscribed to the publication if exists
            if article.publication:
                context["is_subscribed_pub"] = Subscription.objects.filter(
                    subscriber=user,
                    publication=article.publication
                ).exists()

            # check if reader is subscribed to this journalist
            context["is_subscribed_jour"] = Subscription.objects.filter(
                subscriber=user,
                journalist=article.author
            ).exists()

        return context

    def post(self, request, *args, **kwargs):
        """
        Handles POST actions from the detail page (comments, ratings,
        and subscription management), then redirects back to the article.

        - param: request, the current HTTP request.
        - param: *args, positional arguments for the view.
        - param: **kwargs, keyword arguments for the view.
        - return: HTTP redirect to the article/newsletter detail page.
        """
        # Comments
        self.object = self.get_object()

        if not request.user.is_authenticated:
            messages.info(request, "Please sign in to interact.")
            return redirect("login")

        if "text" in request.POST:
            text = (request.POST.get("text") or "").strip()
            if text:
                if hasattr(self.object, "comments"):
                    self.object.comments.create(user=request.user, text=text)
                    messages.success(request, "Comment added successfully.")
                else:
                    messages.error(
                        request,
                        "Comments are not enabled for this item."
                    )
            else:
                messages.error(
                    request,
                    "Please enter a comment before submitting."
                )

        # Ratings
        elif "rating" in request.POST:
            raw = request.POST.get("rating")
            try:
                rating_value = int(raw)
            except (TypeError, ValueError):
                rating_value = None

            if rating_value and 1 <= rating_value <= 5:
                if hasattr(self.object, "ratings") and hasattr(
                    self.object.ratings, "update_or_create"
                ):
                    # prevent journalist rating their own piece
                    if self.object.author == request.user:
                        messages.error(
                            request,
                            "You cannot rate your own article."
                        )
                    else:
                        self.object.ratings.update_or_create(
                            user=request.user,
                            defaults={"score": rating_value},
                        )
                        messages.success(
                            request,
                            "Rating submitted successfully."
                        )
                else:
                    messages.info(
                        request,
                        "Ratings are not enabled for this item."
                    )
            else:
                messages.error(
                    request,
                    "Please provide a rating between 1 and 5."
                )

        # Subscriptions
        elif "action" in request.POST:
            action = request.POST.get("action")
            user = request.user
            article = self.object

            author_publication_ids = (
                article.author.articles
                .exclude(publication__isnull=True)
                .values_list("publication_id", flat=True)
                .distinct()
            )
            author_has_multiple_pubs = len(author_publication_ids) > 1

            # Subscribe to publication
            if action == "subscribe_pub" and article.publication:
                # if already subscribed to the journalist
                if Subscription.objects.filter(
                    subscriber=user,
                    journalist=article.author
                ).exists():
                    # and journalist only writes for ONE publication
                    if not author_has_multiple_pubs:
                        messages.error(
                            request,
                            ("You cannot subscribe to both this publication "
                             "and its sole journalist.")
                            )
                        return redirect(
                            "article_detail", slug=article.slug
                            )

                Subscription.objects.get_or_create(
                    subscriber=user,
                    publication=article.publication
                    )
                messages.success(
                    request,
                    f"Subscribed to {article.publication.name}."
                    )

            # Unsubscribe from publication
            elif action == "unsubscribe_pub" and article.publication:
                Subscription.objects.filter(
                    subscriber=user,
                    publication=article.publication
                ).delete()
                messages.info(
                    request,
                    f"Unsubscribed from {article.publication.name}."
                )

            # Subscribe to journalist
            elif action == "subscribe_jour":
                # if already subscribed to this article's publication
                if article.publication and Subscription.objects.filter(
                    subscriber=user,
                    publication=article.publication
                ).exists():
                    # and journalist only writes for ONE publication
                    if not author_has_multiple_pubs:
                        messages.error(
                            request,
                            ("You cannot subscribe to both this journalist "
                             "and their only publication.")
                            )
                        return redirect(
                            "article_detail", slug=article.slug
                        )

                Subscription.objects.get_or_create(
                    subscriber=user,
                    journalist=article.author
                    )
                messages.success(
                    request,
                    f"Subscribed to {article.author.full_name}."
                    )

            # Unsubscribe from journalist
            elif action == "unsubscribe_jour":
                Subscription.objects.filter(
                    subscriber=user,
                    journalist=article.author
                ).delete()
                messages.info(
                    request,
                    f"Unsubscribed from {article.author.full_name}."
                )

            else:
                messages.error(request, "Unknown action.")

        return redirect("article_detail", slug=self.object.slug)


class ArticleViewSet(viewsets.ModelViewSet):
    """
    Displays all articles.

    - param: ModelViewSet, the articles in the model
    - return: the articles
    """
    queryset = Article.objects.all().select_related("author", "publication")
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Return all published articles.

        - return: QuerySet of published articles
        """
        return Article.objects.filter(status="published")

    def perform_create(self, serializer):
        """
        Automatically set the author to the current user and manages article
        publication status.

        - param: serializer, serializer instance for the article
        - return: None
        """
        article = serializer.save(author=self.request.user)
        if not article.publication:
            article.status = "published"
            article.published_at = timezone.now()
            article.save()

    def get_object(self):
        """
        Override default method to fetch an article by its slug
        instead of primary key.

        - return: Article instance matching the slug
        """
        slug = self.kwargs.get("slug")  # Get slug from URL
        return Article.objects.get(slug=slug)

    @action(detail=False, methods=["get"],
            permission_classes=[IsAuthenticated]
            )
    def my_submissions(self, request):
        """
        Journalist: Retrieve all their articles grouped by status.

        - param: request, HTTP request object
        - return: Response object with categorized articles
        """
        user = request.user
        if user.role != "journalist":
            return Response(
                {"detail": "Only journalists can access submissions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        articles = Article.objects.filter(author=user).order_by("-updated_at")
        data = {
            "drafts": ArticleSerializer(
                articles.filter(status="draft"), many=True
            ).data,
            "pending_approval": ArticleSerializer(
                articles.filter(status="pending_approval"), many=True
            ).data,
            "published": ArticleSerializer(
                articles.filter(status="published"), many=True
            ).data,
            "rejected": ArticleSerializer(
                articles.filter(status="rejected"), many=True
            ).data,
        }
        return Response(data, status=status.HTTP_200_OK)

# --- Journalist Article Views ---


class JournalistPermissionMixin(UserPassesTestMixin):
    """
    Ensure user is a journalist and has relevant permissions.
    """
    def test_func(self):
        return self.request.user.role == "journalist"


class ArticleCreateView(LoginRequiredMixin, JournalistPermissionMixin,
                        CreateView
                        ):
    """
    Allows journalists to create articles and newsletters.

    - Independent articles (no publication) are automatically published.
    - Articles linked to a publication are submitted for editor approval.

    - param: LoginRequiredMixin, ensures user is logged in.
    - param: JournalistPermissionMixin, ensures the user's role is journalist.
    - param: CreateView, provides article creation form and logic.
    - return: redirects user to article list upon successful creation.
    """
    model = Article
    form_class = ArticleForm
    template_name = "articles/article_form.html"
    success_url = reverse_lazy("journalist_dashboard")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user

        # Only show publications this journalist belongs to
        form.fields["publication"].queryset = Publication.objects.filter(
            journalists=user
        )
        return form

    def form_valid(self, form):
        """
        Called when the submitted form is valid.

        - param: form, the submitted article form containing valid data.
        - return: redirects to the article list page after saving.
        """
        form.instance.author = self.request.user

        # Automatically set article status
        if form.cleaned_data.get("publication"):
            form.instance.status = "pending_approval"
        else:
            form.instance.status = "published"

        self.object = form.save()

        # Display success messages
        if self.object.status == "published":
            messages.success(
                self.request,
                "Independent article published automatically!"
            )
        else:
            messages.success(
                self.request,
                "Article submitted for editor approval."
            )

        return redirect(self.success_url)

    def form_invalid(self, form):
        """
        Called when the submitted form is invalid.

        - param: form, the submitted article form containing errors.
        - return: re-rendres the form with validation error messages.
        """
        messages.error(self.request,
                       "There was a problem saving your article.")
        return super().form_invalid(form)


class ArticleUpdateView(LoginRequiredMixin, JournalistPermissionMixin,
                        UpdateView
                        ):
    """
    Allows journalists to update existing articles and newsletters.

    - Independent articles (no publication) are automatically published.
    - Articles linked to a publication are submitted for editor approval.
    - Journalists can only edit their own articles.

    - param: LoginRequiredMixin, ensures user is logged in.
    - param: JournalistPermissionMixin, ensures the user's role is journalist.
    - param: UpdateView, provides article editing form and logic.
    - return: redirects user to their journalist dashboard upon
      successful update.
    """
    model = Article
    form_class = ArticleForm
    template_name = "articles/article_form.html"
    success_url = reverse_lazy("journalist_dashboard")

    def get_queryset(self):
        """
        Ensures journalists can only see their own articles to edit.

        - return: queryset containing only the current journalist's articles.
        """
        return Article.objects.filter(author=self.request.user)

    def get_form(self, form_class=None):
        """
        Limit publication choices to the journalist's joined publications.
        """
        form = super().get_form(form_class)
        user = self.request.user

        # Only show publications the journalist is a member of
        form.fields["publication"].queryset = Publication.objects.filter(
            journalists=user
        )
        return form

    def form_valid(self, form):
        form.instance.author = self.request.user

        if (form.instance.publication
            and not form.instance.publication.journalists.filter(
                id=self.request.user.id).exists()):
            messages.error(self.request,
                           "You cannot assign this article to a publication "
                           "you are not a member of.")
            return self.form_invalid(form)

        if form.cleaned_data.get("publication"):
            form.instance.status = "pending_approval"
            form.instance.published_at = None
        else:
            form.instance.status = "published"
            if not form.instance.published_at:
                form.instance.published_at = timezone.now()

        self.object = form.save()

        # Display success messages
        if self.object.status == "published":
            messages.success(
                self.request,
                "Independent article updated and published automatically!"
            )
        else:
            messages.success(
                self.request,
                "Article updated and submitted for editor approval."
            )

        return redirect(self.success_url)

    def form_invalid(self, form):
        """
        Called when the submitted form is invalid.

        - param: form, the submitted article form containing errors.
        - return: re-renders the form with validation error messages.
        """
        messages.error(
            self.request,
            "There was a problem updating your article."
        )
        return super().form_invalid(form)


class ArticleDeleteView(LoginRequiredMixin, JournalistPermissionMixin,
                        DeleteView
                        ):
    """
    Allows journalists to delete their articles and newsletters.

    - param: LoginRequiredMixin, ensures user is logged in.
    - param: JournalistPermissionMixin, ensures the user's role is journalist.
    - param: DeleteView, provides article deletion confirmation and logic.
    - return: redirects user to article list upon successful deletion.
    """
    model = Article
    template_name = "articles/article_delete.html"
    success_url = reverse_lazy("journalist_dashboard")

    def get_queryset(self):
        """
        Limits which articles the journalist can delete.

        - return: articles authored by the logged-in journalist.
        """
        return Article.objects.filter(author=self.request.user)


class SubmitForApprovalView(LoginRequiredMixin, JournalistPermissionMixin,
                            TemplateView
                            ):
    """
    Journalist submits an article for editor approval.

    - param: LoginRequiredMixin, ensures user is logged in.
    - param: JournalistPermissionMixin, ensures user has journalist permission.
    - param: TemplateView, the template.
    - return: returns user to article list.
    """
    def post(self, request, *args, **kwargs):
        """
        Handles POST request when journalist submits an article for approval.

        - param: request, the current HTTP request.
        - param: *args, positional arguments.
        - param: **kwargs, keyword arguments.
        - return: redirect to journalist dashboard with feedback messages.
        """
        article = get_object_or_404(Article, pk=kwargs["pk"],
                                    author=request.user
                                    )
        if article.publication:
            article.status = "pending_approval"
            article.save()
            messages.info(request, "Article submitted for editor approval.")
        else:
            messages.warning(request,
                             "Independent articles are auto-published."
                             )
        return redirect("journalist_dashboard")


class JournalistDashboardView(LoginRequiredMixin, JournalistPermissionMixin,
                              ListView
                              ):
    """
    Displays the journalist dashboard showing all of their articles and
    newsletters.

    - param: LoginRequiredMixin, ensures the user is logged in.
    - param: JournalistPermissionMixin, ensures the user has
      journalist permission.
    - param: ListView, provides list of articles belonging to the
      current journalist.
    - return: renders the journalist dashboard template with articles.
    """
    model = Article
    template_name = "articles/journalist_dashboard.html"
    context_object_name = "articles"

    def get_queryset(self):
        """
        Retrieves all articles authored by the logged-in journalist, ordered by
        creation date (most recent first).

        - return: queryset of all articles/newsletters authored by the
          current journalist.
        """
        return (
            Article.objects.filter(author=self.request.user)
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        """
        Adds additional context to group the journalist's content by status.

        - return: context, dictionary including grouped article lists.
        """
        context = super().get_context_data(**kwargs)
        user_articles = self.get_queryset()

        context["drafts"] = user_articles.filter(status="draft")
        context["pending"] = user_articles.filter(status="pending_approval")
        context["published"] = user_articles.filter(status="published")
        context["rejected"] = user_articles.filter(status="rejected")

        return context

# --- Editor Views ---


class EditorPermissionMixin(UserPassesTestMixin):
    """
    Ensure user is an editor with relevant permissions.
    """
    def test_func(self):
        return self.request.user.role == "editor"


class PendingArticlesView(LoginRequiredMixin, EditorPermissionMixin, ListView):
    """
    Displays list of pending articles.

    - param: LoginRequiredMixin, ensures user is logged in.
    - param: EditorPermissionMixin, ensures user is an editor.
    - param: ListView, list of the pending articles.
    - return: returns list  of pending articles.
    """
    model = Article
    template_name = "articles/article_pending_list.html"
    context_object_name = "articles"

    def get_queryset(self):
        """
        Filter articles pending editor approval for the logged-in editor.

        - return: queryset of articles awaiting approval.
        """
        return Article.objects.filter(
            publication__editor=self.request.user, status="pending_approval"
        )


class ApproveArticleView(LoginRequiredMixin, EditorPermissionMixin,
                         TemplateView
                         ):
    """
    View of all the approved articles.

    - param: LoginRequireMixin, ensures user is logged in.
    - param: EditorPermissionMixin, ensures user is an editor.
    - param: TemplateView, displays template.
    - return: redirests to pending articles.
    """
    def post(self, request, *args, **kwargs):
        """
        Handle article approval by an editor.

        Changes status to 'published' and redirects back to the
        pending articles list.

        - param: request, the current HTTP request.
        - param: *args, positional arguments.
        - param: **kwargs, keyword arguments.
        - return: redirect to pending articles view.
        """
        article = get_object_or_404(
            Article, pk=kwargs["pk"], publication__editor=request.user
        )
        article.status = "published"
        article.feedback = ""
        article.save()
        messages.success(request, "Article approved and published.")
        return redirect("pending_articles")


class RejectArticleView(LoginRequiredMixin, EditorPermissionMixin,
                        TemplateView
                        ):
    """
    View of all the approved articles.

    - param: LoginRequireMixin, ensures user is logged in.
    - param: EditorPermissionMixin, ensures user is an editor.
    - param: TemplateView, displays template.
    - return: redirests to pending articles.
    """
    def post(self, request, *args, **kwargs):
        article = get_object_or_404(
            Article, pk=kwargs["pk"], publication__editor=request.user
        )
        feedback = request.POST.get("feedback", "")
        article.status = "rejected"
        article.feedback = feedback
        article.save()
        messages.warning(request, "Article rejected with feedback.")
        return redirect("pending_articles")

# --- Comments and ratings ---


class CommentViewSet(viewsets.ModelViewSet):
    """
    Display user comments.

    - param: ModelViewSet, user article comments.
    """
    queryset = Comment.objects.all().select_related("user", "article")
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated | ReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class RatingViewSet(viewsets.ModelViewSet):
    """
    Display user comments.

    - param: ModelViewSet, user article ratings.
    """
    queryset = Rating.objects.all().select_related("user", "article")
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
