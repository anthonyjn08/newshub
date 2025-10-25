from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from .models import Publication, JoinRequest


class PublicationForm(forms.ModelForm):
    class Meta:
        model = Publication
        fields = ["name", "description"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.add_input(Submit("submit", "Save"))


class JoinRequestForm(forms.ModelForm):
    """
    Form for journalists to request to join a publication.
    """

    class Meta:
        model = JoinRequest
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": ("Write a brief message to the "
                                    "editor (optional)..."
                                    ),
                    "class": "form-control",
                }
            ),
        }
        labels = {
            "message": "Message to the Editor",
        }
        help_texts = {
            "message": ("Explain briefly why you'd like to join "
                        "this publication."
                        ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # optional crispy-forms helper setup if you’re using crispy
        self.fields["message"].required = False
