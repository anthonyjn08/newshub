from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import (ListView, CreateView, DetailView,
                                  UpdateView, DeleteView, TemplateView)
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .permissions import ReadOnly, ArticlePermissions
from .forms import ArticleForm
from .models import Article, Comment, Rating
from .serializers import (
    ArticleSerializer, CommentSerializer, RatingSerializer,
    )
from publications.models import Publication
from subscriptions.models import Subscription
from core.mixins import PaginationMixin


class HomeView(TemplateView):
    """The sites home page.

        :params TemplateView: displays view template.
    """
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        """Returns the context for the home page.

            :param: **kwargs, keyword arguments passed to the view.
            :return: context, a dictionary with latest articles and
             newsletters.
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
    """Displays a list of published articles and newsletters.

        :param LoginRequiredMixin: ensures user is logged in to view the list.
        :param ListView: provides paginated display of articles and
         newsletters.
    """
    model = Article
    template_name = "articles/article_list.html"
    context_object_name = "articles"
    paginate_by = 10

    def get_queryset(self):
        """Returns the queryset for published articles or newsletters.

            :return queryset: filteres by type (if specified) and status.
        """
        queryset = Article.objects.filter(
            status="published").order_by("-published_at")

        article_type = self.request.GET.get("type")
        if article_type in ["article", "newsletter"]:
            queryset = queryset.filter(type=article_type)

        return queryset

    def get_context_data(self, **kwargs):
        """Adds separate article and newsletter lists to context.

            :return context: published articles and newsletters.
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
    """Display a detailed view of a published article or newsletter.

        :param DetailView: Renders the article detail template.
    """
    model = Article
    template_name = "articles/article_detail.html"
    context_object_name = "article"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        """Limit visibility to published items for readers and include
        author's own drafts.

            :return: Filtered queryset of articles.
            :rtype: QuerySet
        """
        qs = Article.objects.all()
        user = self.request.user
        if user.is_authenticated:
            return qs.filter(status="published") | qs.filter(author=user)
        return qs.filter(status="published")

    def get_context_data(self, **kwargs):
        """Add subscription info to context for publication and journalist.

            :param **kwargs: Additional context data.
            :return: Updated context dictionary.
            :rtype: dict
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
        """Handle comments, ratings, and subscription actions, then redirect
        to the article detail page.

            :param request: Current HTTP request.
            :type request: HttpRequest
            :return: Redirect to article detail.
            :rtype: HttpResponseRedirect
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
    """View for managing and viewing published articles.

        :param ModelViewSet: Base class for REST framework viewsets.
    """
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated, ArticlePermissions]
    lookup_field = "slug"
    queryset = Article.objects.select_related(
        "author", "publication").order_by("-created_at")

    def get_queryset(self):
        """Filter articles based on user role.

        All users see published articles, journalists also see
        their own and editors see articles all articles in their
        publications.

        :return: Filtered queryset of articles.
        :rtype: QuerySet
        """
        user = self.request.user

        if user.role == "reader":
            return Article.objects.filter(status="published")

        if user.role == "journalist":
            return Article.objects.filter(
                Q(author=user) | Q(status="published")
            ).distinct()

        if user.role == "editor":
            return Article.objects.filter(
                Q(publication__in=user.edited_publications.all())
                | Q(status="published")
            ).distinct()

        return Article.objects.none()

    def perform_create(self, serializer):
        """Assign author and status upon creation.

        Independent articles are published immediately,
        publication linked articles require editor approval.

        :param serializer: Validated article serializer.
        :type serializer: ArticleSerializer
        :return: None
        """
        article = serializer.save(author=self.request.user)
        if not article.publication:
            article.status = "published"
            article.published_at = timezone.now()
            article.save()

    def get_object(self):
        """Retrieve an article and enforce object-level permissions.

        Ensures users can only access articles they have permission for.

        :return: The requested article object.
        :rtype: Article
        """
        lookup_field_value = self.kwargs.get(self.lookup_field)
        article = get_object_or_404(
            Article, **{self.lookup_field: lookup_field_value}
            )
        # Explicitly check permissions on this object
        self.check_object_permissions(self.request, article)
        return article

# --- Journalist Article Views ---


class JournalistPermissionMixin(UserPassesTestMixin):
    """Ensure user is a journalist and has relevant permissions.
    """
    def test_func(self):
        """Check if the user is a journalist.

            :return: True if the user's role is journalist.
            :rtype: bool
        """
        return self.request.user.role == "journalist"


class ArticleCreateView(LoginRequiredMixin, JournalistPermissionMixin,
                        CreateView
                        ):
    """Allow journalists to create new articles or newsletters.

    Independent articles are published automatically, while those linked
    to a publication are submitted for editor approval.
    """
    model = Article
    form_class = ArticleForm
    template_name = "articles/article_form.html"
    success_url = reverse_lazy("journalist_dashboard")

    def get_form(self, form_class=None):
        """Limit publication choices to those the journalist belongs to.

            :param form_class: Form class used to render the article form.
            :type form_class: Form or None
            :return: Form instance with filtered publication queryset.
            :rtype: ArticleForm
        """
        form = super().get_form(form_class)
        user = self.request.user

        # Only show publications this journalist belongs to
        form.fields["publication"].queryset = Publication.objects.filter(
            journalists=user
        )
        return form

    def form_valid(self, form):
        """Save a valid form, assign author, and set publication status.

            :param form: Submitted form with validated data.
            :type form: ArticleForm
            :return: Redirect to dashboard after successful creation.
            :rtype: HttpResponseRedirect
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
        """Handle invalid form submission.

            :param form: Form containing validation errors.
            :type form: ArticleForm
            :return: Re-rendered form with error messages.
            :rtype: HttpResponse
        """
        messages.error(self.request,
                       "There was a problem saving your article.")
        return super().form_invalid(form)


class ArticleUpdateView(LoginRequiredMixin, JournalistPermissionMixin,
                        UpdateView
                        ):
    """
    Allow journalists to edit their existing articles or newsletters.

    Independent articles are published automatically, while publication-linked
    ones are submitted for approval. Journalists can only edit their own work.
    """
    model = Article
    form_class = ArticleForm
    template_name = "articles/article_form.html"
    success_url = reverse_lazy("journalist_dashboard")

    def get_queryset(self):
        """Restrict editable articles to the current journalist.

            :return: Queryset containing only the journalist's articles.
            :rtype: QuerySet
        """
        return Article.objects.filter(author=self.request.user)

    def get_form(self, form_class=None):
        """Limit publication choices to the journalist's memberships.

            :param form_class: Form class used to render the update form.
            :type form_class: Form or None
            :return: Form instance with filtered publication queryset.
            :rtype: ArticleForm
        """
        form = super().get_form(form_class)
        user = self.request.user

        # Only show publications the journalist is a member of
        form.fields["publication"].queryset = Publication.objects.filter(
            journalists=user
        )
        return form

    def form_valid(self, form):
        """Save changes and update publication status and timestamps.

            :param form: Submitted article form with valid data.
            :type form: ArticleForm
            :return: Redirect to dashboard after successful update.
            :rtype: HttpResponseRedirect
        """
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
        """Handle invalid form submissions.

            :param form: Form containing validation errors.
            :type form: ArticleForm
            :return: Re-rendered form with error messages.
            :rtype: HttpResponse
        """
        messages.error(
            self.request,
            "There was a problem updating your article."
        )
        return super().form_invalid(form)


class ArticleDeleteView(LoginRequiredMixin, JournalistPermissionMixin,
                        DeleteView
                        ):
    """Allow journalists to delete their own articles or newsletters.

    Requires login and journalist permissions.
    """
    model = Article
    template_name = "articles/article_delete.html"
    success_url = reverse_lazy("journalist_dashboard")

    def get_queryset(self):
        """Restrict deletable articles to those authored by the current user.

            :return: QuerySet of articles owned by the journalist.
            :rtype: QuerySet
        """
        return Article.objects.filter(author=self.request.user)


class SubmitForApprovalView(LoginRequiredMixin, JournalistPermissionMixin,
                            TemplateView
                            ):
    """Handle article submission for editor approval.

    Journalists can submit only their own articles.
    """
    def post(self, request, *args, **kwargs):
        """Process article submission for editor review.

            :param request: Current HTTP request.
            :type request: HttpRequest
            :param *args: Positional arguments.
            :param **kwargs: Keyword arguments containing the article ID.
            :return: Redirect to journalist dashboard with status message.
            :rtype: HttpResponseRedirect
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
    """Display a dashboard of all articles authored by the journalist.

    Includes published, pending, draft, and rejected items.
    """
    model = Article
    template_name = "articles/journalist_dashboard.html"
    context_object_name = "articles"

    def get_queryset(self):
        """Retrieve all articles authored by the current journalist.

            :return: QuerySet of the journalist's articles ordered by creation
             date.
            :rtype: QuerySet
        """
        return (
            Article.objects.filter(author=self.request.user)
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        """Add grouped article lists to the context by publication status.

            :param **kwargs: Additional context arguments.
            :return: Context dictionary with grouped article data.
            :rtype: dict
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
    """Display a list of articles pending editor approval.

    Requires login and editor permissions.
    """
    model = Article
    template_name = "articles/article_pending_list.html"
    context_object_name = "articles"

    def get_queryset(self):
        """Retrieve articles awaiting approval for the logged-in editor.

            :return: QuerySet of pending articles.
            :rtype: QuerySet
        """
        return Article.objects.filter(
            publication__editor=self.request.user, status="pending_approval"
        )


class ApproveArticleView(LoginRequiredMixin, EditorPermissionMixin,
                         TemplateView
                         ):
    """Handle article approval by editors.

    Changes the article's status to published.
    """
    def post(self, request, *args, **kwargs):
        """Approve an article and mark it as published.

            :param request: Current HTTP request.
            :type request: HttpRequest
            :param *args: Positional arguments.
            :param **kwargs: Keyword arguments containing the article ID.
            :return: Redirect to the pending articles list.
            :rtype: HttpResponseRedirect
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
    """Handle article rejection by editors.

    Stores feedback and marks the article as rejected.
    """

    def post(self, request, *args, **kwargs):
        """Reject an article and store feedback.

            :param request: Current HTTP request.
            :type request: HttpRequest
            :param *args: Positional arguments.
            :param **kwargs: Keyword arguments containing the article ID.
            :return: Redirect to the pending articles list.
            :rtype: HttpResponseRedirect
        """
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
    """Manage article comments from authenticated users.
    """
    queryset = Comment.objects.all().select_related("user", "article")
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated | ReadOnly]

    def perform_create(self, serializer):
        """Assign the current user to the created comment.

            :param serializer: Comment serializer instance.
            :type serializer: CommentSerializer
        """
        serializer.save(user=self.request.user)


class RatingViewSet(viewsets.ModelViewSet):
    """Manage article ratings from authenticated users.
    """
    queryset = Rating.objects.all().select_related("user", "article")
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """Assign the current user to the created rating.

            :param serializer: Rating serializer instance.
            :type serializer: RatingSerializer
        """
        serializer.save(user=self.request.user)
