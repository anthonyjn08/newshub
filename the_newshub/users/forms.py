from django.contrib.auth.forms import UserCreationForm
from .models import User


class ReaderSignUpForm(UserCreationForm):
    """
    Signup form for Readers.
    """
    class Meta:
        model = User
        fields = [
            "email", "first_name", "last_name", "display_name",
            "password1", "password2"
            ]


class JournalistSignUpForm(UserCreationForm):
    """
    Signup form for Journalists.
    """
    class Meta:
        model = User
        fields = [
            "email", "first_name", "last_name", "display_name",
            "password1", "password2"
            ]


class EditorSignUpForm(UserCreationForm):
    """
    Signup form for Editors.
    """
    class Meta:
        model = User
        fields = [
            "email", "first_name", "last_name", "display_name",
            "password1", "password2"
            ]
