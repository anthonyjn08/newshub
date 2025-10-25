import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from publications.models import Publication

User = get_user_model()


@pytest.fixture
def api_client():
    """
    Reusable API client for DRF tests.
    """
    return APIClient()


@pytest.fixture
def reader(db):
    """
    Reader user is read only.
    """
    return User.objects.create_user(
        email="reader@example.com",
        password="password123",
        role="reader",
        first_name="Rita",
        last_name="Reader",
    )


@pytest.fixture
def journalist(db):
    """
    Journalist user can create and edit own articles.
    """
    return User.objects.create_user(
        email="writer@example.com",
        password="password123",
        role="journalist",
        first_name="Jack",
        last_name="Writer",
    )


@pytest.fixture
def editor(db):
    """
    Editor user can manage publications.
    """
    return User.objects.create_user(
        email="editor@example.com",
        password="password123",
        role="editor",
        first_name="Eve",
        last_name="Editor",
    )


@pytest.fixture
def publication(db):
    """
    A test publication.
    """
    return Publication.objects.create(
        name="Daily Truth", description="Independent news")


@pytest.fixture
def another_publication(db):
    """
    Another publication for permission testing.
    """
    return Publication.objects.create(
        name="Tech Weekly", description="Tech reviews")
