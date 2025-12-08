from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    return render(request, "archive/index.html")

@login_required
def subjects(request):
    return render(request, "archive/subjects.html")


@login_required
def subject_create(request):
    return render(request, "archive/subject_create.html")


@login_required
def encounters(request):
    return render(request, "archive/encounters.html")


@login_required
def records(request):
    return render(request, "archive/records.html")


@login_required
def record_detail(request, record_id):
    return render(request, "archive/record_detail.html", {"record_id": record_id})
