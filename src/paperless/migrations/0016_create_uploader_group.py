from django.contrib.auth.management import create_permissions
from django.db import migrations

UPLOADER_PERMISSIONS = {
    "add_document",
    "view_document",
    "add_sharelink",
    "view_sharelink",
    "delete_sharelink",
    "view_paperlesstask",
    "view_uisettings",
}


def create_uploader_group(apps, schema_editor):
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permissions = Permission.objects.filter(
        content_type__app_label="documents",
        codename__in=UPLOADER_PERMISSIONS,
    )
    found_permissions = set(permissions.values_list("codename", flat=True))
    missing_permissions = UPLOADER_PERMISSIONS - found_permissions
    if missing_permissions:
        raise RuntimeError(
            f"Unable to create Uploader group; missing permissions: "
            f"{', '.join(sorted(missing_permissions))}",
        )

    group, _ = Group.objects.get_or_create(name="Uploader")
    group.permissions.add(*permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0025_workflowaction_apply_ai_suggestions"),
        ("paperless", "0015_applicationconfiguration_remote_ocr_mode"),
    ]

    operations = [
        migrations.RunPython(create_uploader_group, migrations.RunPython.noop),
    ]
