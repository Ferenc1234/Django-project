from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import render

from .models import UploadedFile


def home(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = UploadedFile(file=request.FILES['file'])
        try:
            uploaded_file.full_clean()
        except ValidationError:
            return HttpResponse('Invalid file upload.', status=400)
        uploaded_file.save()
        return HttpResponse('Hello World! File saved.')
    return render(request, 'core/home.html')
