from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django_ckeditor_5.widgets import CKEditor5Widget
from django.utils.html import escape
from .models import Article


class ArticleForm(forms.ModelForm):
    """
    Form to create articles.
    """
    class Meta:
        model = Article
        fields = ["title", "type", "publication", "content"]
        help_texts = {
            "content": escape(
                "Use HTML elements for structure (e.g. <h2>, <p>, <strong>). "
                "You can also embed images, videos, and links directly."
            ),
        }
        widgets = {
            "content": CKEditor5Widget(config_name="default"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.include_media = False
        self.helper.disable_csrf = True
        self.helper.add_input(Submit("submit", "Save Article",
                              css_class="btn btn-primary w-100 mt-3")
                              )


class CommentForm(forms.Form):
    """
    Form to let readers add comments to artcles.
    """
    text = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}), label="Comment"
        )


class RatingForm(forms.Form):
    """
    Form to let readers rate articles.
    """
    score = forms.IntegerField(min_value=1, max_value=5, label="Rating (1-5)")
