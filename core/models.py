from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.core.validators import MinValueValidator
from django.db import models
from decimal import Decimal

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_FILE_EXTENSIONS = ['txt', 'pdf', 'png', 'jpg', 'jpeg']


def validate_file_size(file):
    if file.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError('File size exceeds the maximum allowed size of 5MB.')

COLOR_MODE_SINGLE = 'single'
COLOR_MODE_DUAL = 'dual'
COLOR_MODE_TRICOLOR = 'tricolor'
COLOR_MODE_GRADIENT = 'gradient'
COLOR_MODE_CUSTOM = 'custom'

COLOR_MODE_CHOICES = [
    (COLOR_MODE_SINGLE, 'Single color'),
    (COLOR_MODE_DUAL, 'Dual color'),
    (COLOR_MODE_TRICOLOR, 'Tri-color'),
    (COLOR_MODE_GRADIENT, 'Gradient'),
    (COLOR_MODE_CUSTOM, 'Custom / other'),
]

SPOOL_STATUS_FULL = 'full'
SPOOL_STATUS_IN_USE = 'in_use'
SPOOL_STATUS_LOW = 'low'
SPOOL_STATUS_EMPTY = 'empty'
SPOOL_STATUS_ORDERED = 'ordered'

SPOOL_STATUS_CHOICES = [
    (SPOOL_STATUS_FULL, 'Full'),
    (SPOOL_STATUS_IN_USE, 'In use'),
    (SPOOL_STATUS_LOW, 'Low stock'),
    (SPOOL_STATUS_EMPTY, 'Empty'),
    (SPOOL_STATUS_ORDERED, 'Ordered'),
]


class Manufacturer(models.Model):
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Filament(models.Model):
    manufacturer = models.ForeignKey(
        Manufacturer,
        on_delete=models.PROTECT,
        related_name='filaments',
    )
    product_name = models.CharField(max_length=160)
    material = models.CharField(max_length=80)
    color_mode = models.CharField(max_length=20, choices=COLOR_MODE_CHOICES, default=COLOR_MODE_SINGLE)
    primary_color = models.CharField(max_length=80)
    secondary_color = models.CharField(max_length=80, blank=True)
    tertiary_color = models.CharField(max_length=80, blank=True)
    gradient_description = models.CharField(max_length=160, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_filaments',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['manufacturer__name', 'product_name']

    def __str__(self):
        return f'{self.manufacturer.name} {self.product_name}'

    @property
    def color_summary(self):
        colors = [self.primary_color]
        if self.secondary_color:
            colors.append(self.secondary_color)
        if self.tertiary_color:
            colors.append(self.tertiary_color)
        if self.gradient_description:
            colors.append(self.gradient_description)
        return ' • '.join(colors)


class Spool(models.Model):
    filament = models.ForeignKey(Filament, on_delete=models.CASCADE, related_name='spools')
    spool_weight_kg = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0.01)])
    remaining_weight_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=SPOOL_STATUS_CHOICES, default=SPOOL_STATUS_FULL)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_spools',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def clean(self):
        super().clean()
        if self.remaining_weight_kg is not None and self.remaining_weight_kg > self.spool_weight_kg:
            raise ValidationError({'remaining_weight_kg': 'Remaining weight cannot exceed the total spool weight.'})

    def save(self, *args, **kwargs):
        if self.remaining_weight_kg is None:
            self.remaining_weight_kg = self.spool_weight_kg
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.filament} ({self.spool_weight_kg} kg)'

    @property
    def remaining_percentage(self):
        if not self.spool_weight_kg:
            return 0
        percentage = (self.remaining_weight_kg / self.spool_weight_kg) * 100
        return max(0, min(100, int(percentage)))

    @property
    def remaining_label(self):
        return f'{self.remaining_weight_kg} / {self.spool_weight_kg} kg'

    @property
    def remaining_weight_g(self):
        return int((self.remaining_weight_kg or Decimal('0')) * Decimal('1000'))

    @property
    def total_weight_g(self):
        return int(self.spool_weight_kg * Decimal('1000'))

    @property
    def remaining_summary(self):
        return f'{self.remaining_weight_g} g left · {self.remaining_percentage}%'
