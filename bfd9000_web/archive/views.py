import logging
from typing import cast

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, TemplateView

from .forms import RecordForm
from .models import Encounter, Record, Subject


logger = logging.getLogger(__name__)


class StaffOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin ensuring the user is authenticated and marked as staff."""

    login_url = "login"

    def test_func(self):
        request = getattr(self, "request", None)
        user = getattr(request, "user", None)
        return bool(user and user.is_staff)

    def handle_no_permission(self):
        request = getattr(self, "request", None)
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            raise PermissionDenied("Staff access required")
        return super().handle_no_permission()


class SubjectListView(StaffOnlyMixin, ListView):
    model = Subject
    template_name = "archive/home.html"
    context_object_name = "subjects"
    paginate_by = 25

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .order_by("humanname_family", "humanname_given")
            .select_related("address")
            .prefetch_related("identifiers")
            .annotate(encounter_count=Count("encounters", distinct=True))
        )
        query = self.request.GET.get("q")
        if query:
            queryset = queryset.filter(
                Q(humanname_family__icontains=query)
                | Q(humanname_given__icontains=query)
                | Q(identifiers__value__icontains=query)
            ).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["active_nav"] = "subjects"
        return context


class SubjectDetailView(StaffOnlyMixin, DetailView):
    model = Subject
    context_object_name = "subject"
    template_name = "archive/subject_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subject = cast(Subject, context.get("subject") or self.get_object())
        context["records"] = (
            Record.objects.filter(encounter__subject=subject)
            .select_related(
                "encounter",
                "collection",
                "imaging_study",
                "physical_location",
            )
            .prefetch_related("identifiers")
        )
        context["encounters"] = (
            Encounter.objects.filter(subject=subject).select_related("procedure_code")
        )
        context["active_nav"] = "subjects"
        return context


class RecordCreateView(StaffOnlyMixin, CreateView):
    form_class = RecordForm
    template_name = "archive/record_form.html"

    @property
    def subject(self):
        if not hasattr(self, "_subject"):
            self._subject = get_object_or_404(Subject, pk=self.kwargs["subject_pk"])
        return self._subject

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["subject"] = self.subject
        return kwargs

    def form_valid(self, form):
        record = form.save(commit=False)
        if record.encounter.subject_id != self.subject.pk:
            form.add_error(
                "encounter",
                "Selected encounter does not belong to this subject.",
            )
            return self.form_invalid(form)

        record.save()
        form.save_m2m()

        upload = form.cleaned_data.get("upload")
        ingestion_mode = form.cleaned_data.get("ingestion_mode")
        if upload:
            logger.info(
                "Received upload '%s' for subject %s via %s (integration TODO)",
                upload.name,
                self.subject.pk,
                ingestion_mode,
            )
            # Placeholder: in future we will persist this file and link to ImagingStudy.
        self.object = record
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("archive:subject-detail", args=[self.subject.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["subject"] = self.subject
        context["active_nav"] = "subjects"
        context["ingestion_choices"] = RecordForm.INGESTION_CHOICES
        return context


class ReportsTodoView(StaffOnlyMixin, TemplateView):
    template_name = "archive/reports_todo.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_nav"] = "reports"
        return context
