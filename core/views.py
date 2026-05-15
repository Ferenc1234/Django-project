from django.http import HttpResponse
from django.shortcuts import render

from .models import UploadedFile


def home(request):
    if request.method == 'POST' and request.FILES.get('file'):
        UploadedFile.objects.create(file=request.FILES['file'])
        return HttpResponse('Hello World! File saved.')
    return render(request, 'core/home.html')
