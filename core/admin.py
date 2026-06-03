from django.contrib import admin

from .models import Filament, Manufacturer, Spool


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
	list_display = ['name']
	search_fields = ['name']


class SpoolInline(admin.TabularInline):
	model = Spool
	extra = 0


@admin.register(Filament)
class FilamentAdmin(admin.ModelAdmin):
	list_display = ['manufacturer', 'product_name', 'material', 'color_mode', 'created_at']
	list_filter = ['manufacturer', 'material', 'color_mode']
	search_fields = ['product_name', 'manufacturer__name', 'primary_color', 'secondary_color', 'tertiary_color']
	inlines = [SpoolInline]


@admin.register(Spool)
class SpoolAdmin(admin.ModelAdmin):
	list_display = ['filament', 'spool_weight_kg', 'remaining_weight_kg', 'status', 'created_at']
	list_filter = ['status', 'filament__manufacturer', 'filament__material']
	search_fields = ['filament__product_name', 'filament__manufacturer__name', 'notes']
