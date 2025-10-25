from django.contrib import admin
from .models import Article, Comment, Rating


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    list_display = (
        "title", "publication", "author", "status", "published_at"
        )


admin.site.register(Comment)
admin.site.register(Rating)
