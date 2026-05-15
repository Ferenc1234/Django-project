from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models


def validate_file_size(file):
    max_size = 5 * 1024 * 1024
    if file.size > max_size:
        raise ValidationError('File size must be 5MB or less.')


class UploadedFile(models.Model):
    file = models.FileField(
        upload_to='uploads/',
        validators=[FileExtensionValidator(['txt', 'pdf', 'png', 'jpg', 'jpeg']), validate_file_size],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name
