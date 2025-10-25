from django.test import TestCase
from django.urls import reverse
from users.models import User
from publications.models import Publication
from articles.models import Article
from subscriptions.models import Subscription


class ReaderFlowTests(TestCase):
    """
    Tests reader dashboard functionality, including subscription
    listings and unsubscribe functionality.
    """

    def setUp(self):
        # Create users and publication
        self.reader = User.objects.create_user(
            email="bumblebee@test.com",
            first_name="Bumble",
            last_name="Bee",
            password="pass123",
            role="reader",
        )
        self.journalist = User.objects.create_user(
            email="optimus@test.com",
            first_name="Optimus",
            last_name="Prime",
            password="pass123",
            role="journalist",
        )
        self.publication = Publication.objects.create(
            name="Cybertron Daily",
            description="Latest Cybertonian news."
        )

        self.article = Article.objects.create(
            title="Decipticons Attack", author=self.journalist,
            publication=self.publication, status="published",
            content="<p>Transform and roll out</p>"
            )

        # Create subscriptions
        self.pub_sub = Subscription.objects.create(
            subscriber=self.reader, publication=self.publication
            )
        self.jour_sub = Subscription.objects.create(
            subscriber=self.reader, journalist=self.journalist
            )

    def test_reader_dashboard_loads_with_subscriptions(self):
        """
        Reader dashboard should display both types of subscriptions.
        """
        self.client.login(email="bumblebee@test.com", password="pass123")
        response = self.client.get(reverse("reader_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Publication Subscriptions")
        self.assertContains(response, "Cybertron Daily")
        self.assertContains(response, "Optimus Prime")

    def test_reader_can_unsubscribe_from_publication(self):
        """
        Reader should be able to unsubscribe from a publication.
        """
        self.client.login(email="bumblebee@test.com", password="pass123")
        response = self.client.post(
            reverse("unsubscribe_publication", args=[self.publication.pk]),
            follow=True
            )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Subscription.objects.filter(
            subscriber=self.reader, publication=self.publication).exists())

    def test_reader_can_unsubscribe_from_journalist(self):
        """
        Reader should be able to unsubscribe from a journalist.
        """
        self.client.login(email="bumblebee@test.com", password="pass123")
        response = self.client.post(reverse(
            "unsubscribe_journalist", args=[self.journalist.pk]), follow=True
            )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Subscription.objects.filter(
                subscriber=self.reader, journalist=self.journalist
                ).exists()
                )

    def test_dashboard_requires_login(self):
        """
        Unauthenticated users should be redirected to login page.
        """
        response = self.client.get(reverse("reader_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_dashboard_pagination_works(self):
        """
        Dashboard should correctly paginate long subscription lists.
        """
        # Create additional publication subscriptions
        for i in range(15):
            pub = Publication.objects.create(name=f"TestPub{i}")
            Subscription.objects.create(subscriber=self.reader,
                                        publication=pub
                                        )

        self.client.login(email="bumblebee@test.com", password="pass123")
        response = self.client.get(reverse("reader_dashboard") + "?page=2")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TestPub")
