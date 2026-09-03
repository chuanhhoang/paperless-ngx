from importlib import import_module

import pytest
from django.apps import apps
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

from documents.models import Document


@pytest.mark.django_db
def test_create_uploader_group_assigns_minimal_permissions() -> None:
    migration = import_module("paperless.migrations.0016_create_uploader_group")

    migration.create_uploader_group(apps, None)

    group = Group.objects.get(name="Uploader")
    permissions = set(group.permissions.values_list("codename", flat=True))
    assert permissions == migration.UPLOADER_PERMISSIONS


@pytest.mark.django_db
def test_uploader_can_view_and_share_only_owned_documents() -> None:
    migration = import_module("paperless.migrations.0016_create_uploader_group")
    migration.create_uploader_group(apps, None)
    uploader = User.objects.create_user("uploader")
    uploader.groups.add(Group.objects.get(name="Uploader"))
    other_user = User.objects.create_user("other-user")
    owned_document = Document.objects.create(
        title="Owned",
        mime_type="application/pdf",
        owner=uploader,
    )
    other_document = Document.objects.create(
        title="Other",
        mime_type="application/pdf",
        owner=other_user,
    )
    client = APIClient()
    client.force_authenticate(uploader)

    assert uploader.has_perm("documents.add_document")
    assert not uploader.has_perm("documents.change_document")
    documents_response = client.get("/api/documents/")
    assert documents_response.status_code == status.HTTP_200_OK
    visible_ids = {item["id"] for item in documents_response.data["results"]}
    assert owned_document.pk in visible_ids
    assert other_document.pk not in visible_ids

    own_link_response = client.post(
        "/api/share_links/",
        {"document": owned_document.pk, "file_version": "original"},
        format="json",
    )
    assert own_link_response.status_code == status.HTTP_201_CREATED
    other_link_response = client.post(
        "/api/share_links/",
        {"document": other_document.pk, "file_version": "original"},
        format="json",
    )
    assert other_link_response.status_code == status.HTTP_403_FORBIDDEN
