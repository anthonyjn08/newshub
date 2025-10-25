import pytest
from django.urls import reverse
from django.test import Client
from publications.models import JoinRequest, Publication
from articles.models import Article


@pytest.mark.django_db
def test_reader_can_only_view_publications(api_client, reader, publication):
    api_client.force_authenticate(reader)
    url = reverse("publication-list")
    res = api_client.get(url)
    assert res.status_code == 200
    assert any(pub["name"] == "Daily Truth" for pub in res.data["results"])
    # reader should not be able to create, edit or delete
    post_res = api_client.post(url, {"name": "Reader Pub"})
    assert post_res.status_code == 403


@pytest.mark.django_db
def test_journalist_can_view_but_not_create(api_client, journalist,
                                            publication):
    api_client.force_authenticate(journalist)
    url = reverse("publication-list")
    res = api_client.get(url)
    assert res.status_code == 200
    post_res = api_client.post(url, {"name": "Journalist Pub"})
    assert post_res.status_code == 403


@pytest.mark.django_db
def test_editor_can_create_publication(api_client, editor):
    api_client.force_authenticate(editor)
    url = reverse("publication-list")
    res = api_client.post(url, {"name": "New Publication",
                                "description": "Testing"})
    assert res.status_code in [201, 200]
    assert "New Publication" in str(res.data)


@pytest.mark.django_db
def test_editor_can_update_own_publication(api_client, editor, publication):
    publication.editors.add(editor)
    api_client.force_authenticate(editor)
    url = reverse("publication-detail", args=[publication.id])
    res = api_client.patch(url, {"description": "Updated desc"}, format="json")
    assert res.status_code in [200, 202]
    publication.refresh_from_db()
    assert publication.description == "Updated desc"


@pytest.mark.django_db
def test_editor_cannot_update_other_publication(api_client, editor,
                                                another_publication
                                                ):
    api_client.force_authenticate(editor)
    url = reverse("publication-detail", args=[another_publication.id])
    res = api_client.patch(url, {"description": "Hack!"}, format="json")
    assert res.status_code in [403, 404]


@pytest.mark.django_db
def test_editor_dashboard_requires_login():
    """
    Unauthenticated users should be redirected to login.
    """
    client = Client()
    url = reverse("editor_dashboard")
    res = client.get(url)
    assert res.status_code == 302
    assert "/login" in res.url.lower()


@pytest.mark.django_db
def test_reader_cannot_access_editor_dashboard(reader):
    """
    Readers should get 403 when trying to access the editor dashboard.
    """
    client = Client()
    client.force_login(reader)
    url = reverse("editor_dashboard")
    res = client.get(url)
    # Should have no access
    assert res.status_code in [302, 403]


@pytest.mark.django_db
def test_editor_dashboard_loads_with_context(editor, publication):
    """
    Editors should see their publications, pending join requests,
    and pending articles on the dashboard.
    """
    client = Client()
    client.force_login(editor)

    # Link editor to the publication
    publication.editors.add(editor)

    # Create dummy join request and pending article
    JoinRequest.objects.create(
        user=editor,
        publication=publication,
        status="pending",
    )
    Article.objects.create(
        title="Pending Article",
        author=editor,
        publication=publication,
        status="pending_approval",
        content="<p>Waiting approval</p>",
    )

    url = reverse("editor_dashboard")
    res = client.get(url)

    assert res.status_code == 200
    assert "publications" in res.context
    assert "pending_requests" in res.context
    assert "pending_articles" in res.context
    assert publication in res.context["publications"]
    assert res.context["pending_articles"].first().title == "Pending Article"


@pytest.mark.django_db
def test_editor_dashboard_context_data(editor, journalist):
    """
    Ensure the editor dashboard context contains:
    - publications managed by the editor
    - pending join requests
    - pending approval articles
    """
    # Create publication and assign editor
    pub = Publication.objects.create(name="Investigative Weekly",
                                     description="Serious news")
    pub.editors.add(editor)

    # Add pending join request
    JoinRequest.objects.create(user=journalist, publication=pub,
                               status="pending")

    # Add pending article for that publication
    Article.objects.create(
        title="Pending Investigation",
        content="Classified.",
        author=journalist,
        publication=pub,
        status="pending_approval"
    )

    client = Client()
    client.force_login(editor)
    url = reverse("editor_dashboard")
    res = client.get(url)

    assert res.status_code == 200
    context = res.context

    # Check expected context
    assert "publications" in context
    assert "pending_requests" in context
    assert "pending_articles" in context

    # Validate contents
    assert pub in context["publications"]
    assert context["pending_requests"].filter(user=journalist).exists()
    assert context["pending_articles"].filter(
        title="Pending Investigation").exists()
