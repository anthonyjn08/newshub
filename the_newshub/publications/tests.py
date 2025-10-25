from django.test import TestCase
from django.urls import reverse
from users.models import User
from articles.models import Article
from publications.models import Publication, JoinRequest


class EditorFlowTests(TestCase):
    """
    Tests editor functions including approving articles,
    managing publications, and processing journalist join requests.
    """
    def setUp(self):
        # Create users and publication
        self.journalist = User.objects.create_user(
            email="goku@test.com",
            first_name="Son",
            last_name="Goku",
            password="pass123",
            role="journalist",
        )
        self.editor = User.objects.create_user(
            email="vegeta@test.com",
            first_name="Prince",
            last_name="Vegeta",
            password="pass123",
            role="editor",
        )
        self.publication = Publication.objects.create(
            name="Planet Vegta News",
            description="News for the great warrior race."
        )
        self.publication.editors.add(self.editor)
        self.publication.journalists.add(self.journalist)

        # Article setup
        self.article = Article.objects.create(
            title="Pending Approval",
            author=self.journalist,
            publication=self.publication,
            status="pending_approval",
            content="<p>It's over 9000!.</p>",
        )

    def test_editor_dashboard_loads(self):
        """
        Editor dashboard should display publications and pending articles.
        """
        self.client.login(email="vegeta@test.com", password="pass123")
        response = self.client.get(reverse("editor_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Publications")
        self.assertContains(response, "Pending Approval")

    def test_editor_can_approve_article(self):
        """
        Editors should be able to approve submitted articles.
        """
        self.client.login(email="vegeta@test.com", password="pass123")
        response = self.client.post(
            reverse("editor_approve_article", args=[self.article.pk]),
            follow=True
            )
        self.assertEqual(response.status_code, 200)
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, "published")

    def test_editor_can_reject_article(self):
        """
        Editors should be able to reject articles with feedback.
        """
        self.client.login(email="vegeta@test.com", password="pass123")
        response = self.client.post(
            reverse("editor_reject_article", args=[self.article.pk]),
            {"feedback": "You're weak!"},
            follow=True,
            )
        self.assertEqual(response.status_code, 200)
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, "rejected")
        self.assertIn("weak", self.article.feedback)

    def test_journalist_can_request_to_join_publication(self):
        """
        Journalists should be able to submit join requests.
        """
        self.client.login(email="goku@test.com", password="pass123")
        response = self.client.post(
            reverse("join_publication", args=[self.publication.pk]),
            {"message": "I'd love to work for you."}, follow=True,
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            JoinRequest.objects.filter(
                user=self.journalist, publication=self.publication
                ).exists()
            )

    def test_editor_can_approve_join_request(self):
        """
        Editors can approve join requests from journalists.
        """
        join_req = JoinRequest.objects.create(
            user=self.journalist, publication=self.publication,
            status="pending"
            )
        self.client.login(email="vegeta@test.com", password="pass123")
        response = self.client.post(
            reverse("approve_join_request", args=[join_req.pk]),
            follow=True
            )
        self.assertEqual(response.status_code, 200)
        join_req.refresh_from_db()
        self.assertEqual(join_req.status, "approved")

    def test_editor_can_reject_join_request(self):
        """
        Editors can reject join requests with feedback.
        """
        join_req = JoinRequest.objects.create(
            user=self.journalist, publication=self.publication,
            status="pending"
            )
        self.client.login(email="vegeta@test.com", password="pass123")
        response = self.client.post(
            reverse("reject_join_request", args=[join_req.pk]),
            {"feedback": "Currently not accepting new writers."},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        join_req.refresh_from_db()
        self.assertEqual(join_req.status, "rejected")
        self.assertIn("not accepting", join_req.feedback)
