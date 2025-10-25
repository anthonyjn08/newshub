from django.contrib.auth.models import AbstractUser, BaseUserManager, Group
from django.db.utils import OperationalError, ProgrammingError
from django.core.exceptions import ObjectDoesNotExist
from django.db import models


class UserManager(BaseUserManager):
    """
    Manager for CustomUser model.

    Provides helper methods to create regular users and superusers
    with email as the unique identifier instead of username.

    - param: BaseUserManager, provides Django's base user management methods.
    - return: custom user manager for the User model.
    """
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        """
        Creates and saves a regular user with the given email and password.

        - param: email, user's email address (required).
        - param: password, user's chosen password.
        - param: **extra_fields, additional fields to set on the user.
        - return: created user instance.
        """
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        extra_fields.setdefault("role", "reader")
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Creates and saves a superuser admin with full access.

        - param: email, admin's email address.
        - param: password, admin's password.
        - param: **extra_fields, optional extra attributes for the user.
        - return: created superuser instance.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "editor")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model for readers, journalists and editors.

    Fields:
        - username: None, email will become username and used for login.
        - role: EmailField, users email address.
        - first_name: CharField, a users first name.
        - last_name: CharField, a users last name.
        - display_name: CharfField, a uses choosen display name, will
          be used as name when leaving comments.
    """
    ROLE_CHOICES = [
        ("reader", "Reader"),
        ("journalist", "Journalist"),
        ("editor", "Editor")
        ]
    username = None
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default="reader"
        )
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    display_name = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Optional name for comments")
    subscribed_publishers = models.ManyToManyField(
        "publications.Publication", related_name="subscribed_readers",
        blank=True,  help_text="Publishers this reader follows",
        )
    subscribed_journalists = models.ManyToManyField(
        "self", symmetrical=False, related_name="reader_followers",
        blank=True, help_text="Journalists this reader follows",
        )
    independent_articles = models.ManyToManyField(
        "articles.Article", related_name="independent_authors",
        blank=True,
        help_text="Articles published independently by this journalist",
        )

    # Make Email login field
    USERNAME_FIELD = 'email'

    # Require firsst and last name fields for articles
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    @property
    def full_name(self):
        """
        Returns full name for journalists wjem creating articles.
        """
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def effective_display_name(self):
        """
        Returns display name which is used for article comments.
        """
        return self.display_name if self.display_name else self.full_name

    def save(self, *args, **kwargs):
        """
        Ensure mutual exclusivity of reader vs journalist fields.
        """
        super().save(*args, **kwargs)
        if self.role == "journalist":
            # Clear reader-only fields
            self.subscribed_publishers.clear()
            self.subscribed_journalists.clear()
        elif self.role == "reader":
            # Clear journalist-only fields
            self.independent_articles.clear()

        # Assign the user to the proper role group
        try:
            group, _ = Group.objects.get_or_create(name=self.role.capitalize())
            self.groups.clear()
            self.groups.add(group)
        except (OperationalError, ProgrammingError, ObjectDoesNotExist):
            # Failsafe for errors that may happen during initial migration.
            pass
