from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_FILE_EXTENSIONS = ['txt', 'pdf', 'png', 'jpg', 'jpeg']


def validate_file_size(file):
    if file.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError('File size exceeds the maximum allowed size of 5MB.')


class UploadedFile(models.Model):
    file = models.FileField(
        upload_to='uploads/',
        validators=[FileExtensionValidator(ALLOWED_FILE_EXTENSIONS), validate_file_size],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name
