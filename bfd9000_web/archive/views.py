from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    return render(request, "archive/index.html")

@login_required
def subjects(request):
    return render(request, "archive/subjects.html")


@login_required
def records(request):
    return render(request, "archive/records.html")
