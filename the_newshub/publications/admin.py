from django.contrib import admin
from .models import Publication


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    filter_horizontal = ("editors", "journalists")
