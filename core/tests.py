from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import UploadedFile


class HomeViewTests(TestCase):
    def test_home_page_displays_hello_world(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hello World!')

    def test_upload_saves_file_record(self):
        file = SimpleUploadedFile('hello.txt', b'hello world')

        response = self.client.post(reverse('home'), {'file': file})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(UploadedFile.objects.count(), 1)
        self.assertContains(response, 'File saved')
