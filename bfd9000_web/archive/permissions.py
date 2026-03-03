# pyright: reportIncompatibleMethodOverride=false

from typing import Any

from django.db.models import Model
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request


class CuratorOrSuperuserEditPermission(BasePermission):
    """Require model add/change perms for writes and auth for reads."""

    def has_permission(self, request: Request, view: Any):  # pyright: ignore[reportIncompatibleMethodOverride]
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if request.method in SAFE_METHODS:
            return True
        if request.method == "DELETE":
            return False

        qs = getattr(view, "queryset", None)
        if qs is None and hasattr(view, "get_queryset"):
            try:
                qs = view.get_queryset()
            except Exception:
                qs = None
        model: type[Model] | None = getattr(qs, "model", None)
        if model is None:
            return False

        app_label = model._meta.app_label
        model_name = model._meta.model_name
        if model_name is None:
            return False
        if request.method == "POST":
            return request.user.has_perm(f"{app_label}.add_{model_name}")
        if request.method in {"PUT", "PATCH"}:
            return request.user.has_perm(f"{app_label}.change_{model_name}")
        return False


class RecordPermission(BasePermission):
    """Allow authenticated users to read/create/update records."""

    def has_permission(self, request: Request, view: Any):  # pyright: ignore[reportIncompatibleMethodOverride]
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method == "DELETE":
            return bool(request.user.is_superuser)
        return True
