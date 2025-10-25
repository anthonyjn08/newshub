import pytest
from django.urls import reverse
from django.test import Client
from rest_framework.test import APIClient
from articles.models import Article
from users.models import User
from publications.models import Publication


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def reader(db):
    return User.objects.create_user(
        email="reader@example.com",
        password="testpass123",
        role="reader",
        first_name="Rita",
        last_name="Reader"
        )


@pytest.fixture
def journalist(db):
    return User.objects.create_user(
        email="writer@example.com",
        password="testpass123",
        role="journalist",
        first_name="John",
        last_name="Journo"
        )


@pytest.fixture
def editor(db):
    return User.objects.create_user(
        email="editor@example.com",
        password="testpass123",
        role="editor",
        first_name="Eve",
        last_name="Editor"
        )


@pytest.fixture
def publication(db, editor, journalist):
    pub = Publication.objects.create(name="Daily Truth")
    pub.editors.add(editor)
    pub.journalists.add(journalist)
    return pub


@pytest.fixture
def journalist_article(db, journalist):
    return Article.objects.create(
        title="Journalist Story",
        author=journalist,
        content="<p>Draft content</p>",
        status="draft",
        slug="journalist-story"
        )


@pytest.fixture
def other_journalist(db):
    return User.objects.create_user(
        email="other@example.com",
        password="testpass123",
        role="journalist",
        first_name="Other",
        last_name="Writer",
        )


@pytest.fixture
def published_article(other_journalist):
    return Article.objects.create(
        title="Published Story",
        content="<p>Published content</p>",
        status="published",
        author=other_journalist,)


@pytest.fixture
def publication_article(db, journalist, publication):
    return Article.objects.create(
        title="Publication Story",
        author=journalist,
        publication=publication,
        content="<p>Pending content</p>",
        status="pending_approval",
        slug="publication-story"
    )


def extract_titles(response):
    data = response.data.get("results", response.data)
    return [a["title"] for a in data]

# Aricle creation


@pytest.mark.django_db
def test_reader_cannot_create_article(api_client, reader):
    api_client.force_authenticate(reader)
    url = reverse("article-list")
    res = api_client.post(url, ({"title": "Reader Try",
                                 "content": "<p>Nope</p>"}))
    assert res.status_code == 403


@pytest.mark.django_db
def test_journalist_can_create_article(api_client, journalist):
    api_client.force_authenticate(journalist)
    url = reverse("article-list")
    res = api_client.post(url, ({"title": "Journo Post",
                                 "content": "<p>Hello!</p>"}))
    assert res.status_code == 201
    article = Article.objects.get(title="Journo Post")
    assert article.status == "published"  # independent auto-publish


@pytest.mark.django_db
def test_editor_cannot_create_article(api_client, editor):
    api_client.force_authenticate(editor)
    url = reverse("article-list")
    res = api_client.post(url,
                          ({"title": "Editor Post",
                            "content": "<p>Should fail</p>"}))
    assert res.status_code == 403


# View tests


@pytest.mark.django_db
def test_reader_can_view_only_published(api_client, reader,
                                        published_article, journalist_article):

    api_client.force_authenticate(reader)
    url = reverse("article-list")
    res = api_client.get(url)
    titles = extract_titles(res)
    assert "Published Story" in titles
    assert "Journalist Story" not in titles


@pytest.mark.django_db
def test_journalist_can_view_own_and_published(
      api_client, journalist, published_article, journalist_article):

    api_client.force_authenticate(journalist)
    url = reverse("article-list")
    res = api_client.get(url)
    titles = extract_titles(res)
    assert "Published Story" in titles
    assert "Journalist Story" in titles


@pytest.mark.django_db
def test_editor_can_view_publication_articles(api_client,
                                              editor, publication_article):
    api_client.force_authenticate(editor)
    url = reverse("article-list")
    res = api_client.get(url)
    titles = extract_titles(res)
    assert "Publication Story" in titles

# Update tests


@pytest.mark.django_db
def test_journalist_can_update_own_article(api_client, journalist,
                                           journalist_article):
    api_client.force_authenticate(journalist)
    url = reverse("article-detail", args=[journalist_article.slug])
    res = api_client.patch(url, {"title": "Updated Title"}, format="json")
    assert res.status_code in [200, 202]
    journalist_article.refresh_from_db()
    assert journalist_article.title == "Updated Title"


@pytest.mark.django_db
def test_journalist_cannot_update_others_article(api_client, journalist,
                                                 published_article
                                                 ):
    api_client.force_authenticate(journalist)
    url = reverse("article-detail", args=[published_article.slug])
    res = api_client.patch(url, {"title": "Hack Attempt"}, format="json")
    assert res.status_code == 403


@pytest.mark.django_db
def test_editor_can_update_publication_article(api_client, editor,
                                               publication_article):
    api_client.force_authenticate(editor)
    url = reverse("article-detail", args=[publication_article.slug])
    res = api_client.patch(url, {"feedback": "Needs more detail"},
                           format="json"
                           )
    assert res.status_code in [200, 202]
    publication_article.refresh_from_db()
    assert publication_article.feedback == "Needs more detail"


@pytest.mark.django_db
def test_reader_cannot_update_article(api_client, reader, published_article):
    api_client.force_authenticate(reader)
    url = reverse("article-detail", args=[published_article.slug])
    res = api_client.patch(url, {"title": "Unauthorized"}, format="json")
    assert res.status_code == 403


@pytest.mark.django_db
def test_journalist_can_access_dashboard(journalist):
    """
    Journalists should be able to access their dashboard.
    """
    client = Client()
    client.force_login(journalist)
    url = reverse("journalist_dashboard")
    res = client.get(url)
    assert res.status_code == 200
    assert "articles" in res.context
    assert "drafts" in res.context
    assert "published" in res.context


@pytest.mark.django_db
def test_reader_cannot_access_journalist_dashboard(reader):
    """
    Readers should be denied access to the journalist dashboard.
    """
    client = Client()
    client.force_login(reader)
    url = reverse("journalist_dashboard")
    res = client.get(url)
    assert res.status_code in [302, 403]


@pytest.mark.django_db
def test_editor_cannot_access_journalist_dashboard(editor):
    """
    Editors should not be able to access the journalist dashboard.
    """
    client = Client()
    client.force_login(editor)
    url = reverse("journalist_dashboard")
    res = client.get(url)
    assert res.status_code in [302, 403]


@pytest.mark.django_db
def test_journalist_dashboard_groups_articles_by_status(journalist):
    """
    Journalist dashboard should group articles by status.
    """
    # Create test articles for the journalist
    Article.objects.create(title="Draft Story",
                           content="...", author=journalist, status="draft")

    Article.objects.create(title="Pending Story",
                           content="...", author=journalist,
                           status="pending_approval")

    Article.objects.create(title="Published Story",
                           content="...", author=journalist,
                           status="published")

    Article.objects.create(title="Rejected Story",
                           content="...", author=journalist, status="rejected")

    client = Client()
    client.force_login(journalist)
    url = reverse("journalist_dashboard")
    res = client.get(url)

    assert res.status_code == 200
    context = res.context

    # Verify the status exists.
    assert "drafts" in context
    assert "pending" in context
    assert "published" in context
    assert "rejected" in context

    # Check counts
    assert context["drafts"].count() == 1
    assert context["pending"].count() == 1
    assert context["published"].count() == 1
    assert context["rejected"].count() == 1
