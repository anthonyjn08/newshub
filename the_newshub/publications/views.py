from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (ListView, DetailView, CreateView, DeleteView,
                                  UpdateView, TemplateView)
from .models import Publication, JoinRequest
from .serializers import PublicationSerializer, JoinRequestSerializer
from .permissions import IsEditor, ReadOnly
from .forms import PublicationForm, JoinRequestForm
from articles.models import Article
from articles.forms import ArticleForm
from core.mixins import PaginationMixin


class PublicationListView(ListView, PaginationMixin):
    """Display a paginated list of all publications.

    Combines standard list rendering with pagination to efficiently
    display publication entries.
    """
    model = Publication
    template_name = "publications/publication_list.html"
    context_object_name = "publications"

    def get_queryset(self):
        """Retrieve all publications and mark whether the logged-in journalist
        has a pending join request for each.

            :return: QuerySet of publications with a custom attribute
             has_pending_request added for the current user.
            :rtype: QuerySet
        """
        set = Publication.objects.prefetch_related("editors", "join_requests")
        user = self.request.user
        for pub in set:
            pub.has_pending_request = (
                pub.join_requests.filter(user=user, status="pending").exists()
                if user.is_authenticated and user.role == "journalist"
                else False
            )
        return set


class PublicationDetailView(DetailView):
    """Display detailed information about a publication, including its
    published articles and subscription status.
    """
    model = Publication
    template_name = "publications/publication_detail.html"
    context_object_name = "publication"

    def get_context_data(self, **kwargs):
        """Add subscription status and published articles to the context.

            :param kwargs: Additional keyword arguments passed to the view.
            :type kwargs: dict
            :return: Context dictionary including is_subscribed and
             articles.
            :rtype: dict
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Check if the user is subscribed to the publication
        is_subscribed = self.object.subscriptions.filter(
            subscriber=user).exists()

        context["is_subscribed"] = is_subscribed

        context["articles"] = self.object.articles.filter(
            status="published"
        ).order_by("-published_at")

        return context


class PublicationViewSet(viewsets.ModelViewSet):
    """Provide CRUD operations for publications.

    Editors can create and manage publications, while readers
    can only view them.
    """
    queryset = Publication.objects.all()
    serializer_class = PublicationSerializer

    def get_permissions(self):
        """Assign view or edit permissions depending on the action.

            :return: List of permission instances.
            :rtype: list
        """
        if self.action in ["list", "retrieve"]:
            return [ReadOnly()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Automatically assign the current user as an editor
        when creating a publication..

            :param serializer: Validated publication serializer instance.
            :type serializer: PublicationSerializer
            :return: None
        """
        # Auto-assign current user as editor
        publication = serializer.save()
        publication.editors.add(self.request.user)
        if self.request.user.role != "editor":
            self.request.user.role = "editor"
            self.request.user.save()

# --- Journalist views ---


class JoinRequestViewSet(viewsets.ModelViewSet):
    """Manage join requests between journalists and publications.

    Journalists can request to join publications, while editors can
    view, approve, or reject these requests.
    """
    queryset = JoinRequest.objects.all()
    serializer_class = JoinRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter join requests based on the logged-in user's role.

        Editors see requests for their publications.
        Journalists see only their own requests.

            :return: Filtered queryset of join requests.
            :rtype: QuerySet
        """
        user = self.request.user
        if user.role == "editor":
            # Editors see requests for their publications
            return JoinRequest.objects.filter(publication__editors=user)
        elif user.role == "journalist":
            # Journalists see their own requests
            return JoinRequest.objects.filter(user=user)
        return JoinRequest.objects.none()

    def perform_create(self, serializer):
        """Allow journalists to request to join a publication.

            :param serializer: Validated join request serializer instance.
            :type serializer: JoinRequestSerializer
            :return: Response indicating success or forbidden action.
            :rtype: Response
        """
        if self.request.user.role != "journalist":
            return Response(
                ({"detail": "Only journalists can "
                  "request to join publications."}),
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[IsEditor])
    def approve(self, request, pk=None):
        """Approve a journalist's join request.

            :param request: Current HTTP request.
            :type request: HttpRequest
            :param pk: Primary key of the join request.
            :type pk: int
            :return: Response confirming approval.
            :rtype: Response
        """
        join_request = self.get_object()
        join_request.status = "approved"
        join_request.reviewed_at = timezone.now()
        join_request.feedback = request.data.get("feedback", "")
        join_request.save()

        join_request.publication.journalists.add(join_request.user)

        return Response(
            {"detail": "Request approved."}, status=status.HTTP_200_OK
            )

    @action(detail=True, methods=["post"], permission_classes=[IsEditor])
    def reject(self, request, pk=None):
        """Reject a journalist's join request.

            :param request: Current HTTP request.
            :type request: HttpRequest
            :param pk: Primary key of the join request.
            :type pk: int
            :return: Response confirming rejection.
            :rtype: Response
        """
        join_request = self.get_object()
        join_request.status = "rejected"
        join_request.reviewed_at = timezone.now()
        join_request.feedback = request.data.get("feedback", "")
        join_request.save()
        return Response(
            {"detail": "Request rejected."}, status=status.HTTP_200_OK
            )


class JournalistPermissionMixin(UserPassesTestMixin):
    """Restrict access to users with the journalist role.
    """
    def test_func(self):
        """Verify the user has a journalist role.

            :return: True if the user's role is journalist.
            :rtype: bool
        """
        return self.request.user.role == "journalist"


class JoinPublicationView(LoginRequiredMixin, JournalistPermissionMixin,
                          CreateView
                          ):
    """Allow journalists to submit join requests for publications.

    Prevents duplicate requests and provides confirmation messages
    upon successful submission.
    """
    model = JoinRequest
    form_class = JoinRequestForm
    template_name = "publications/join_publication.html"

    def dispatch(self, request, *args, **kwargs):
        """Prevent duplicate join requests for the same publication.

            :param request: Current HTTP request.
            :type request: HttpRequest
            :return: Redirect if a duplicate exists, otherwise proceed
             normally.
            :rtype: HttpResponseRedirect
        """
        self.publication = get_object_or_404(Publication, pk=self.kwargs["pk"])

        # prevent duplicate requests
        existing_request = JoinRequest.objects.filter(
            user=request.user,
            publication=self.publication,
            status="pending"
        ).exists()
        if existing_request:
            messages.warning(request,
                             "You already have a pending request "
                             "for this publication.")
            return redirect("publication_list")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Process and save a valid join request form.

        Assigns the current user and selected publication before saving.

            :param form: Validated join request form.
            :type form: JoinRequestForm
            :return: Redirect after successful submission.
            :rtype: HttpResponseRedirect
        """
        form.instance.user = self.request.user
        form.instance.publication = self.publication
        response = super().form_valid(form)

        messages.success(self.request, "Join request submitted successfully!")
        return response

    def get_context_data(self, **kwargs):
        """Add publication data to the form context.

            :param kwargs: Additional context arguments.
            :type kwargs: dict
            :return: Context including publication object.
            :rtype: dict
        """
        context = super().get_context_data(**kwargs)
        context["publication"] = self.publication
        return context

    def get_success_url(self):
        """Redirect to the publication list upon successful submission.

            :return: URL for publication list view.
            :rtype: str
        """
        return reverse_lazy("publication_list")

# --- Editor views ---


class EditorPermissionMixin(UserPassesTestMixin):
    """Restrict access to users with the editor role.
    """
    def test_func(self):
        """Verify that the current user is an editor.

            :return: True if the user's role is editor.
            :rtype: bool
        """
        return self.request.user.role == "editor"


class EditorDashboardView(LoginRequiredMixin, TemplateView, PaginationMixin):
    """Display the editor dashboard with key editorial data.

    Shows the editor's publications, pending join requests, and
    articles awaiting approval.
    """
    template_name = "publications/editor_dashboard.html"

    def get_context_data(self, **kwargs):
        """Add editor-related data to the dashboard context.

        Includes publications managed by the editor, join requests,
        and articles pending approval.

            :param kwargs: Additional context arguments.
            :type kwargs: dict
            :return: Context dictionary with editor dashboard data.
            :rtype: dict
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["publications"] = user.edited_publications.all()
        context["pending_requests"] = (
            JoinRequest.objects.filter(publication__editors=user,
                                       status="pending"
                                       )
            .select_related("user", "publication")
            .order_by("-created_at")
        )
        context["pending_articles"] = (
            Article.objects.filter(publication__editors=user,
                                   status="pending_approval"
                                   )
            .select_related("author", "publication")
            .order_by("-created_at")
        )
        return context


class ArticleReviewView(LoginRequiredMixin, DetailView):
    """Allow editors to review, edit, approve, reject, or delete
    articles within their publications.
    """
    model = Article
    template_name = "publications/article_review.html"
    context_object_name = "article"

    def get_queryset(self):
        """Limit visible articles to those managed by the current editor.

            :return: QuerySet of articles under the editor's publications.
            :rtype: QuerySet
        """
        return Article.objects.filter(publication__editors=self.request.user)

    def get_context_data(self, **kwargs):
        """Include the inline article editing form in the context.

            :param kwargs: Additional context arguments.
            :type kwargs: dict
            :return: Context dictionary including edit form.
            :rtype: dict
        """
        context = super().get_context_data(**kwargs)
        context["form"] = ArticleForm(instance=self.get_object())
        return context

    def post(self, request, *args, **kwargs):
        """Handle editor actions such as save, approve, reject, or delete.

            :param request: Current HTTP request.
            :type request: HttpRequest
            :param args: Positional arguments.
            :type args: list
            :param kwargs: Keyword arguments.
            :type kwargs: dict
            :return: Redirect to the same page or dashboard after action.
            :rtype: HttpResponseRedirect
        """
        article = self.get_object()
        action = request.POST.get("action")

        # Inline content edit
        if action == "save_edits":
            form = ArticleForm(request.POST, instance=article)
            if form.is_valid():
                form.save()
                messages.success(
                    request, f"Changes to '{article.title}' have been saved."
                    )
                return redirect(request.path)
            else:
                messages.error(request,
                               "There was an error saving your edits."
                               )
                return self.get(request, *args, **kwargs)

        # Approve / reject / delete actions
        if action == "approve":
            article.status = "published"
            article.save()
            messages.success(
                request, f"'{article.title}' has been approved and published."
                )
        elif action == "reject":
            feedback = request.POST.get("feedback", "")
            article.status = "rejected"
            article.feedback = feedback
            article.save()
            messages.warning(request, f"'{article.title}' has been rejected.")
        elif action == "delete":
            title = article.title
            article.delete()
            messages.info(request, f"'{title}' has been deleted.")
        else:
            messages.error(request, "Invalid action.")

        return redirect(reverse_lazy("editor_dashboard"))


class PublicationArticlesView(LoginRequiredMixin, ListView, PaginationMixin):
    """Display all articles belonging to a publication managed by the editor.

    Editors can view, edit, or delete any article within their publication.
    """
    template_name = "publications/publication_articles.html"
    context_object_name = "articles"
    paginate_by = 10

    def get_queryset(self):
        """Retrieve all articles for a specific publication managed by
        the editor.

            :return: QuerySet of articles ordered by creation date.
            :rtype: QuerySet
        """
        self.publication = get_object_or_404(
            Publication, pk=self.kwargs["pk"], editors=self.request.user
        )
        return (
            Article.objects.filter(publication=self.publication)
            .select_related("author", "publication")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        """Add publication data to the view context.

            :param kwargs: Additional context arguments.
            :type kwargs: dict
            :return: Context dictionary including publication details.
            :rtype: dict
        """
        context = super().get_context_data(**kwargs)
        context["publication"] = self.publication
        return context


class JoinRequestListView(LoginRequiredMixin, EditorPermissionMixin,
                          ListView, PaginationMixin
                          ):
    """Display all pending join requests for the editor's publications.

    Provides a paginated list of journalist requests awaiting approval.
    """
    model = JoinRequest
    template_name = "publications/join_requests_list.html"
    context_object_name = "requests"

    def get_queryset(self):
        """Retrieve pending join requests for publications managed
        by the editor.

            :return: QuerySet of pending join requests with related user
             and publication data.
            :rtype: QuerySet
        """
        return (
            JoinRequest.objects.filter(
                publication__editors=self.request.user, status="pending"
            )
            .select_related("user", "publication")
            )


class ApproveJoinRequestView(LoginRequiredMixin, EditorPermissionMixin,
                             UpdateView
                             ):
    """Handle the rejection of a journalist's join request by an editor.
    """
    model = JoinRequest
    fields = []
    template_name = "publications/approve_join_request.html"

    def post(self, request, *args, **kwargs):
        """Reject a join request and optionally record feedback.

            :param request: Current HTTP request.
            :type request: HttpRequest
            :param args: Positional arguments.
            :type args: list
            :param kwargs: Keyword arguments.
            :type kwargs: dict
            :return: Redirect to the join requests list with an info message.
            :rtype: HttpResponseRedirect
        """
        join_request = self.get_object()
        join_request.status = "approved"
        join_request.publication.journalists.add(join_request.user)
        join_request.save()
        messages.success(request,
                         (f"{join_request.user.full_name} added to "
                          f"{join_request.publication.name}.")
                         )
        return redirect("join_requests_list")


class RejectJoinRequestView(LoginRequiredMixin, EditorPermissionMixin,
                            UpdateView):
    """"Handle the rejection of a journalist's join request by an editor.
    """
    model = JoinRequest
    fields = []
    template_name = "publications/reject_join_request.html"

    def post(self, request, *args, **kwargs):
        """Reject a join request and optionally record editor feedback.

            :param request: Current HTTP request.
            :type request: HttpRequest
            :param args: Positional arguments.
            :type args: list
            :param kwargs: Keyword arguments.
            :type kwargs: dict
            :return: Redirect to the join requests list with an info message.
            :rtype: HttpResponseRedirect
        """
        join_request = self.get_object()
        feedback_text = request.POST.get("feedback", "").strip()
        if feedback_text:
            join_request.feedback = feedback_text
        join_request.status = "rejected"
        join_request.save()
        messages.info(request, (f"Join request from "
                                f"{join_request.user.full_name} "
                                f"rejected.")
                      )
        return redirect("join_requests_list")


class ApproveArticleView(LoginRequiredMixin, EditorPermissionMixin, View):
    """Allow editors to approve and publish submitted articles.
    """
    def post(self, request, *args, **kwargs):
        """Publish an article by changing its status to published.

            :param request: Current HTTP request.
            :type request: HttpRequest
            :param args: Positional arguments.
            :type args: list
            :param kwargs: Keyword arguments.
            :type kwargs: dict
            :return: Redirect to the editor dashboard with a success message.
            :rtype: HttpResponseRedirect
        """
        article = get_object_or_404(
            Article,
            pk=kwargs["pk"],
            publication__editors=request.user,
        )
        article.status = "published"
        article.feedback = ""
        article.save()

        messages.success(request, f"'{article.title}' approved and published.")
        return redirect("editor_dashboard")


class RejectArticleView(LoginRequiredMixin, EditorPermissionMixin, View):
    """Allow editors to reject submitted articles and provide feedback.
    """
    def post(self, request, *args, **kwargs):
        """Reject an article and save optional editor feedback.

            :param request: Current HTTP request.
            :type request: HttpRequest
            :param args: Positional arguments.
            :type args: list
            :param kwargs: Keyword arguments.
            :type kwargs: dict
            :return: Redirect to the editor dashboard with a warning message.
            :rtype: HttpResponseRedirect
        """
        article = get_object_or_404(
            Article,
            pk=kwargs["pk"],
            publication__editors=request.user,
        )
        feedback = request.POST.get("feedback", "")
        article.status = "rejected"
        article.feedback = feedback
        article.save()

        messages.warning(request, f"'{article.title}' rejected.")
        return redirect("editor_dashboard")


class PublicationCreateView(LoginRequiredMixin, EditorPermissionMixin,
                            CreateView
                            ):
    """Allow editors to create new publications.

    The creator is automatically added as an editor and receives
    a success message upon creation.
    """
    model = Publication
    form_class = PublicationForm
    template_name = "publications/publication_form.html"

    def form_valid(self, form):
        """Process and save a valid publication form.

            :param form: Validated publication form instance.
            :type form: PublicationForm
            :return: Redirect to the success URL with a success message.
            :rtype: HttpResponseRedirect
        """
        self.object = form.save()
        self.object.editors.add(self.request.user)
        messages.success(self.request, "Publication created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        """Redirect to the editor dashboard upon successful creation.

            :return: URL of the editor dashboard.
            :rtype: str
        """
        return reverse_lazy("editor_dashboard")


class PublicationUpdateView(LoginRequiredMixin, EditorPermissionMixin,
                            UpdateView
                            ):
    """Allow editors to update existing publications they manage.
    """
    model = Publication
    form_class = PublicationForm
    template_name = "publications/publication_form.html"

    def form_valid(self, form):
        """Process and save a valid publication update form.

            :param form: Validated publication form instance.
            :type form: PublicationForm
            :return: Redirect to the success URL with a success message.
            :rtype: HttpResponseRedirect
        """
        form.instance.editor = self.request.user
        messages.success(self.request, "Publication created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        """Redirect to the editor dashboard after updating the publication.

            :return: URL of the editor dashboard.
            :rtype: str
        """
        return reverse_lazy("editor_dashboard")


class PublicationDeleteView(LoginRequiredMixin, EditorPermissionMixin,
                            DeleteView
                            ):
    """Allow editors to delete publications they manage.

    Only publications associated with the current editor can be deleted.
    """
    model = Publication
    template_name = "publications/publication_delete.html"
    success_url = reverse_lazy("editor_dashboard")

    def get_queryset(self):
        """Limit deletable publications to those owned by the logged-in editor.

            :return: QuerySet of publications the editor manages.
            :rtype: QuerySet
        """
        return Publication.objects.filter(editors=self.request.user)
