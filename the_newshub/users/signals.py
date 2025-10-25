from django.db.models.signals import post_save
from django.contrib.auth.models import Group, Permission, ContentType
from django.dispatch import receiver
from .models import User
from articles.models import Article


def setup_default_groups():
    """
    Ensures that the user groups and permissions exist.
    """
    content_type = ContentType.objects.get_for_model(Article)

    # Reader group
    reader_group, _ = Group.objects.get_or_create(name="Reader")
    reader_perms = Permission.objects.filter(
        content_type=content_type,
        codename__startswith="view_",
    )
    reader_group.permissions.set(reader_perms)

    # Journalist group
    journalist_group, _ = Group.objects.get_or_create(name="Journalist")
    journalist_perms = Permission.objects.filter(
        content_type=content_type,
        codename__in=[
            f"add_{Article._meta.model_name}",
            f"change_{Article._meta.model_name}",
            f"delete_{Article._meta.model_name}",
            f"view_{Article._meta.model_name}",
        ],
    )
    journalist_group.permissions.set(journalist_perms)

    # Editor group
    editor_group, _ = Group.objects.get_or_create(name="Editor")
    editor_perms = Permission.objects.filter(
        content_type=content_type,
        codename__in=[
            f"change_{Article._meta.model_name}",
            f"delete_{Article._meta.model_name}",
            f"view_{Article._meta.model_name}",
        ],
    )
    editor_group.permissions.set(editor_perms)


@receiver(post_save, sender=User)
def assign_user_group(sender, instance, created, **kwargs):
    """
    Assigns users to the correct group, after checking
    that the group alreadys exists.
    """
    if created:
        setup_default_groups()
        role_map = {
            "reader": "Reader",
            "journalist": "Journalist",
            "editor": "Editor",
        }
        group_name = role_map.get(instance.role)
        if group_name:
            group = Group.objects.get(name=group_name)
            instance.groups.add(group)
