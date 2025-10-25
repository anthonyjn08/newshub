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
    """
    Displays a paginated list of all publications.

    - param: ListView, provides list rendering functionality.
    - param: PaginationMixin, handles pagination for large lists.
    - return: renders publication list template with pagination.
    """
    model = Publication
    template_name = "publications/publication_list.html"
    context_object_name = "publications"

    def get_queryset(self):
        """
        Retrieve all publications, marking whether the logged-in journalist
        has a pending join request for each.

        - return: list of publications.
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
    """
    Displays detailed information about a specific publication, including
    its published articles and subscription status.

    - param: DetailView, provides detail page rendering.
    - return: renders publication detail template with context data.
    """
    model = Publication
    template_name = "publications/publication_detail.html"
    context_object_name = "publication"

    def get_context_data(self, **kwargs):
        """
        Adds subscription status and the publication's published articles
        to the context.

        - param: **kwargs, additional context arguments.
        - return: context dictionary including `is_subscribed` and `articles`.
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
    """
    Editors can create and manage their own publications.
    Readers can only view.

    - param: ModelViewSet, provides editors functionality for publications.
    - return: serialized publication data or HTTP responses.
    """
    queryset = Publication.objects.all()
    serializer_class = PublicationSerializer

    def get_permissions(self):
        """
        Assigns permissions based on user action.

        - 'list' and 'retrieve' actions are read-only.
        - All other actions require authentication.

        - return: list of permission instances.
        """
        if self.action in ["list", "retrieve"]:
            return [ReadOnly()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """
        Automatically assigns the current user as an editor when creating
        a publication. If the user's role is not already 'editor',
        it updates it.

        - param: serializer, the validated publication serializer instance.
        - return: None.
        """
        # Auto-assign current user as editor
        publication = serializer.save()
        publication.editors.add(self.request.user)
        if self.request.user.role != "editor":
            self.request.user.role = "editor"
            self.request.user.save()

# --- Journalist views ---


class JoinRequestViewSet(viewsets.ModelViewSet):
    """
    Handles join requests between journalists and publications.

    - Journalists can request to join publications.
    - Editors can view, approve, or reject these requests.

    - param: ModelViewSet, provides CRUD operations for join requests.
    - return: serialized join request data or HTTP responses.
    """
    queryset = JoinRequest.objects.all()
    serializer_class = JoinRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filters join requests based on user role.

        Editors see requests for their own publications while journalists
        can only see their own requests.

        - return: filtered queryset of join requests.
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
        """
        Allows journalists to request to join a publication.

        - param: serializer, validated join request serializer instance.
        - return: HTTP response indicating success or forbidden action.
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
        """
        Allows editors to approve a journalist's join request.

        - param: request, the current HTTP request.
        - param: pk, primary key of the join request.
        - return: HTTP 200 response indicating success.
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
        """
        Allows editors to reject a journalist's join request.

        - param: request, the current HTTP request.
        - param: pk, primary key of the join request.
        - return: HTTP 200 response confirming rejection.
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
    """
    Ensure user is a journalist.
    """
    def test_func(self):
        return self.request.user.role == "journalist"


class JoinPublicationView(LoginRequiredMixin, JournalistPermissionMixin,
                          CreateView
                          ):
    """
    Allows journalists to submit a join request for a publication.

    Prevents duplicate requests for the same publication and displays
    confirmation message on success.

    - param: LoginRequiredMixin, ensures user is logged in.
    - param: JournalistPermissionMixin, ensures user is a journalist.
    - param: CreateView, handles join request form rendering and submission.
    - return: redirects to publication list upon successful request.
    """
    model = JoinRequest
    form_class = JoinRequestForm
    template_name = "publications/join_publication.html"

    def dispatch(self, request, *args, **kwargs):
        """
        Handles initial request dispatch.

        Prevents duplicate join requests for the same publication.

        - param: request, the current HTTP request.
        - return: redirect if duplicate request exists, else proceeds normally.
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
        """
        Process and save a valid join request forms.

        - Assigns the current user and selected publication before saving.
        - param: form, the validated join request form.
        - return: HTTP response after saving with success message.
        """
        form.instance.user = self.request.user
        form.instance.publication = self.publication
        response = super().form_valid(form)

        messages.success(self.request, "Join request submitted successfully!")
        return response

    def get_context_data(self, **kwargs):
        """
        Adds publication data to the form page.

        - param: **kwargs, additional context arguments.
        - return: context dictionary including publication object.
        """
        context = super().get_context_data(**kwargs)
        context["publication"] = self.publication
        return context

    def get_success_url(self):
        return reverse_lazy("publication_list")

# --- Editor views ---


class EditorPermissionMixin(UserPassesTestMixin):
    """
    Ensures a user has editor permissions.
    """
    def test_func(self):
        return self.request.user.role == "editor"


class EditorDashboardView(LoginRequiredMixin, TemplateView, PaginationMixin):
    """
    Displays the editor dashboard, showing all relevant publication data.

    - Shows all publications managed by the editor.
    - Displays pending join requests from journalists.
    - Lists all articles and newsletters awaiting editorial approval.

    - param: LoginRequiredMixin, ensures the user is logged in.
    - param: TemplateView, provides template rendering for the
      editor dashboard.
    - return: renders the editor dashboard with publications, requests,
      and pending articles.
    """
    template_name = "publications/editor_dashboard.html"

    def get_context_data(self, **kwargs):
        """
        Adds editor-related data, including publications,
        join requests, and pending articles.

        - param: **kwargs, additional context arguments.
        - return: context dictionary with dashboard data for the editor.
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
    """
    Allows editors to preview, edit, approve, reject, or delete
    articles within their publications.

    - param: LoginRequiredMixin, ensures the user is logged in.
    - param: DetailView, provides detailed view of the article.
    - return: renders article review page or redirects after actions.
    """
    model = Article
    template_name = "publications/article_review.html"
    context_object_name = "article"

    def get_queryset(self):
        """
        Limit visible articles to those managed by the logged-in editor.

        - return: queryset of articles under the editor's management.
        """
        return Article.objects.filter(publication__editors=self.request.user)

    def get_context_data(self, **kwargs):
        """
        Include the inline editing form for article content.

        - param: **kwargs, additional context arguments.
        - return: context dictionary including the edit form.
        """
        context = super().get_context_data(**kwargs)
        context["form"] = ArticleForm(instance=self.get_object())
        return context

    def post(self, request, *args, **kwargs):
        """
        Handles editor actions (edit, approve, reject, or delete).

        - param: request, the current HTTP request.
        - param: *args, positional arguments for the view.
        - param: **kwargs, keyword arguments for the view.
        - return: redirect to the same page or editor dashboard after action.
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
    """
    Displays all articles belonging to a publication managed by the editor.
    Editors can edit or delete any article within their publication.

    - param: LoginRequiredMixin, ensures the user is logged in.
    - param: ListView, provides list rendering of publication articles.
    - return: renders list of articles within a publication.
    """
    template_name = "publications/publication_articles.html"
    context_object_name = "articles"
    paginate_by = 10

    def get_queryset(self):
        """
        Retrieve all articles for a specific publication managed by the editor.

        - return: queryset of publication articles ordered by creation date.
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
        """
        Adds publication data to the context for rendering.

        - param: **kwargs, additional context arguments.
        - return: context dictionary including publication information.
        """
        context = super().get_context_data(**kwargs)
        context["publication"] = self.publication
        return context


class JoinRequestListView(LoginRequiredMixin, EditorPermissionMixin,
                          ListView, PaginationMixin
                          ):
    """
    Displays a list of pending join requests for publications managed
    by the logged-in editor.

    - param: LoginRequiredMixin, ensures the user is logged in.
    - param: EditorPermissionMixin, ensures the user has editor privileges.
    - param: ListView, provides the listing behaviour.
    - param: PaginationMixin, enables pagination for large lists.
    - return: renders the join requests list template.
    """
    model = JoinRequest
    template_name = "publications/join_requests_list.html"
    context_object_name = "requests"

    def get_queryset(self):
        """
        Retrieves all pending join requests related to the
        editor's publications.

        - return: queryset of pending join requests with related user and
          publication data.
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
    """
    Handles the approval of a journalist's join request by an editor.

    - param: LoginRequiredMixin, ensures the user is logged in.
    - param: EditorPermissionMixin, ensures the user is an editor.
    - param: UpdateView, provides object update functionality.
    - return: redirects back to the join requests list after approval.
    """
    model = JoinRequest
    fields = []
    template_name = "publications/approve_join_request.html"

    def post(self, request, *args, **kwargs):
        """
        Approves a pending join request and adds the journalist
        to the publication.

        - param: request, the current HTTP request.
        - param: *args, positional arguments.
        - param: **kwargs, keyword arguments.
        - return: redirect to the join requests list with success message.
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
    """
    Handles rejection of a journalist's join request by an editor.

    - param: LoginRequiredMixin, ensures the user is logged in.
    - param: EditorPermissionMixin, ensures the user is an editor.
    - param: UpdateView, allows modification of join request instance.
    - return: redirects back to the join requests list after rejection.
    """
    model = JoinRequest
    fields = []
    template_name = "publications/reject_join_request.html"

    def post(self, request, *args, **kwargs):
        """
        Rejects a join request, optionally recording editor feedback.

        - param: request, the current HTTP request.
        - param: *args, positional arguments.
        - param: **kwargs, keyword arguments.
        - return: redirect to the join requests list with info message.
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
    """
    Allows editors to approve and publish submitted articles.

    - param: LoginRequiredMixin, ensures the user is logged in.
    - param: EditorPermissionMixin, ensures only editors can approve.
    - param: View, provides HTTP method handling.
    - return: redirects back to the editor dashboard.
    """
    def post(self, request, *args, **kwargs):
        """
        Publishes an article by changing its status to 'published'.

        - param: request, the current HTTP request.
        - param: *args, positional arguments.
        - param: **kwargs, keyword arguments.
        - return: redirect to editor dashboard with success message.
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
    """
    Allows editors to reject submitted articles and provide feedback.

    - param: LoginRequiredMixin, ensures the user is logged in.
    - param: EditorPermissionMixin, ensures only editors can reject.
    - param: View, provides HTTP method handling.
    - return: redirects back to the editor dashboard.
    """
    def post(self, request, *args, **kwargs):
        """
        Rejects an article and saves optional feedback from the editor.

        - param: request, the current HTTP request.
        - param: *args, positional arguments.
        - param: **kwargs, keyword arguments (expects 'pk').
        - return: redirect to editor dashboard with warning message.
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
    """
    Allows editors to create new publications.

    Adds the creator as an editor of the new publication and displays
    success message on creation.

    - param: LoginRequiredMixin, ensures user is logged in.
    - param: EditorPermissionMixin, ensures user has editor privileges.
    - param: CreateView, provides publication creation form and logic.
    - return: redirects to editor dashboard upon success.
    """
    model = Publication
    form_class = PublicationForm
    template_name = "publications/publication_form.html"

    def form_valid(self, form):
        """
        Handles valid publication form submission.

        - param: form, the validated publication form.
        - return: response redirecting to success URL.
        """
        self.object = form.save()
        self.object.editors.add(self.request.user)
        messages.success(self.request, "Publication created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        """
        Redirects the editor to their dashboard after successful creation.
        """
        return reverse_lazy("editor_dashboard")


class PublicationUpdateView(LoginRequiredMixin, EditorPermissionMixin,
                            UpdateView
                            ):
    """
    Allows editors to update existing publications they manage.

    - param: LoginRequiredMixin, ensures user is logged in.
    - param: EditorPermissionMixin, ensures user is an editor.
    - param: UpdateView, provides publication editing form and logic.
    - return: redirects to editor dashboard upon success.
    """
    model = Publication
    form_class = PublicationForm
    template_name = "publications/publication_form.html"

    def form_valid(self, form):
        """
        Handles valid publication update submissions.

        - param: form, the validated publication form.
        - return: response redirecting to success URL.
        """
        form.instance.editor = self.request.user
        messages.success(self.request, "Publication created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        """
        Redirects to the editor dashboard after publication update.
        """
        return reverse_lazy("editor_dashboard")


class PublicationDeleteView(LoginRequiredMixin, EditorPermissionMixin,
                            DeleteView
                            ):
    """
    Allows editors to delete publications they manage.

    - Only publications belonging to the current editor can be deleted.

    - param: LoginRequiredMixin, ensures user is logged in.
    - param: EditorPermissionMixin, ensures user is an editor.
    - param: DeleteView, provides deletion confirmation and logic.
    - return: redirects to editor dashboard after deletion.
    """
    model = Publication
    template_name = "publications/publication_delete.html"
    success_url = reverse_lazy("editor_dashboard")

    def get_queryset(self):
        """
        Restrict deletable publications to those owned by the editor.
        """
        return Publication.objects.filter(editors=self.request.user)
