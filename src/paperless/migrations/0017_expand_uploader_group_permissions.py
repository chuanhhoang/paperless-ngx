from django.contrib.auth.management import create_permissions
from django.db import migrations

UPLOADER_ADDITIONAL_PERMISSIONS = {
    "add_sharelinkbundle",
    "view_sharelinkbundle",
    "delete_sharelinkbundle",
    "view_savedview",
}


def expand_uploader_group_permissions(apps, schema_editor):
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permissions = Permission.objects.filter(
        content_type__app_label="documents",
        codename__in=UPLOADER_ADDITIONAL_PERMISSIONS,
    )
    found_permissions = set(permissions.values_list("codename", flat=True))
    missing_permissions = UPLOADER_ADDITIONAL_PERMISSIONS - found_permissions
    if missing_permissions:
        raise RuntimeError(
            f"Unable to expand Uploader group; missing permissions: "
            f"{', '.join(sorted(missing_permissions))}",
        )

    group, _ = Group.objects.get_or_create(name="Uploader")
    group.permissions.add(*permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("paperless", "0016_create_uploader_group"),
    ]

    operations = [
        migrations.RunPython(
            expand_uploader_group_permissions,
            migrations.RunPython.noop,
        ),
    ]
