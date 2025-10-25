from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from articles.models import Article
from publications.models import Publication

User = get_user_model()


class JournalistFlowTests(TestCase):
    """
    Tests journalist workflow including article creation,
    automatic publishing for independent article, and dashboard display.
    """

    def setUp(self):
        # Create users and publication
        self.journalist = User.objects.create_user(
            email="jdvance@test.com",
            first_name="JD",
            last_name="Vance",
            password="pass123",
            role="journalist",
        )
        self.editor = User.objects.create_user(
            email="potus@test.com",
            first_name="Donald",
            last_name="Trump",
            password="pass123",
            role="editor",
        )
        self.publication = Publication.objects.create(
            name="Fake News",
            description="A trusted source of controlled media."
        )
        self.publication.editors.add(self.editor)
        self.publication.journalists.add(self.journalist)

    def test_journalist_can_access_dashboard(self):
        """
        Tests journalist dashboard loads correctly.
        """
        logged_in = self.client.login(email="jdvance@test.com",
                                      password="pass123"
                                      )
        self.assertTrue(logged_in,
                        ("Login failed — check AUTHENTICATION_BACKENDS "
                         "or USERNAME_FIELD."
                         ))
        response = self.client.get(reverse("journalist_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Articles")

    def test_journalist_creates_independent_article_auto_publishes(self):
        """
        Tests that independent articles publish immediately.
        """
        self.client.login(email="jdvance@test.com", password="pass123")
        data = {
            "title": "Independent Article",
            "type": "article",
            "content": "<p>Some genuine content.</p>",
        }
        response = self.client.post(reverse("article_create"),
                                    data, follow=True
                                    )
        self.assertEqual(response.status_code, 200)
        article = Article.objects.last()
        self.assertEqual(article.author, self.journalist)
        self.assertEqual(article.status, "published")

    def test_journalist_creates_article_for_publication_needs_approval(self):
        """
        Tests that journalist articles linked to a publication should
        need editor approval before they're published.
        """
        self.client.login(email="jdvance@test.com", password="pass123")
        data = {
            "title": "Submitted Article",
            "type": "article",
            "content": "<p>Publication linked article.</p>",
            "publication": self.publication.id,
        }
        response = self.client.post(reverse("article_create"),
                                    data, follow=True
                                    )
        self.assertEqual(response.status_code, 200)
        article = Article.objects.last()
        self.assertEqual(article.status, "pending_approval")

    def test_journalist_sees_articles_in_dashboard_sections(self):
        """
        Tests that articles have correct categories in the dashboard.
        """
        Article.objects.create(title="Draft Article", author=self.journalist,
                               status="draft"
                               )
        Article.objects.create(title="Live Article", author=self.journalist,
                               status="published"
                               )
        Article.objects.create(title="Awaiting Review",
                               author=self.journalist,
                               status="pending_approval"
                               )
        self.client.login(email="jdvance@test.com", password="pass123")
        response = self.client.get(reverse("journalist_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Draft Article")
        self.assertContains(response, "Live Article")
        self.assertContains(response, "Awaiting Review")
