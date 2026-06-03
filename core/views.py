from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CatalogFilterForm, FilamentForm, SpoolForm
from .models import Filament, Spool


def home(request):
    spool_sizes = [
        (str(size), f'{size} kg')
        for size in (
            Spool.objects.order_by('spool_weight_kg')
            .values_list('spool_weight_kg', flat=True)
            .distinct()
        )
    ]
    filter_form = CatalogFilterForm(request.GET or None, spool_size_choices=spool_sizes)

    filaments = Filament.objects.select_related('manufacturer').all()
    spool_prefetch = Spool.objects.select_related('filament', 'filament__manufacturer').all()

    if filter_form.is_valid():
        cleaned = filter_form.cleaned_data
        if cleaned.get('manufacturer'):
            filaments = filaments.filter(manufacturer=cleaned['manufacturer'])
        if cleaned.get('material'):
            filaments = filaments.filter(material__icontains=cleaned['material'])
        if cleaned.get('color_mode'):
            filaments = filaments.filter(color_mode=cleaned['color_mode'])
        if cleaned.get('color'):
            color_query = cleaned['color']
            filaments = filaments.filter(
                Q(primary_color__icontains=color_query)
                | Q(secondary_color__icontains=color_query)
                | Q(tertiary_color__icontains=color_query)
                | Q(gradient_description__icontains=color_query)
            )
        if cleaned.get('spool_size'):
            filaments = filaments.filter(spools__spool_weight_kg=Decimal(cleaned['spool_size']))
            spool_prefetch = spool_prefetch.filter(spool_weight_kg=Decimal(cleaned['spool_size']))
        if cleaned.get('spool_status'):
            filaments = filaments.filter(spools__status=cleaned['spool_status'])
            spool_prefetch = spool_prefetch.filter(status=cleaned['spool_status'])

    filaments = filaments.distinct().prefetch_related(Prefetch('spools', queryset=spool_prefetch))

    return render(
        request,
        'core/home.html',
        {
            'filter_form': filter_form,
            'filaments': filaments,
        },
    )


@login_required
def filament_create(request):
    if request.method == 'POST':
        form = FilamentForm(request.POST)
        if form.is_valid():
            filament = form.save(commit=False)
            filament.created_by = request.user
            filament.save()
            messages.success(request, 'Filament created.')
            return redirect('home')
    else:
        form = FilamentForm()
    return render(request, 'core/filament_form.html', {'form': form, 'page_title': 'Add filament'})


@login_required
def filament_edit(request, pk):
    filament = get_object_or_404(Filament, pk=pk)
    if request.method == 'POST':
        form = FilamentForm(request.POST, instance=filament)
        if form.is_valid():
            updated_filament = form.save(commit=False)
            updated_filament.created_by = filament.created_by or request.user
            updated_filament.save()
            messages.success(request, 'Filament updated.')
            return redirect('home')
    else:
        form = FilamentForm(instance=filament, initial={'manufacturer_name': filament.manufacturer.name})
    return render(request, 'core/filament_form.html', {'form': form, 'page_title': 'Edit filament'})


@login_required
def spool_create(request, filament_id):
    filament = get_object_or_404(Filament, pk=filament_id)
    if request.method == 'POST':
        form = SpoolForm(request.POST)
        if form.is_valid():
            spool = form.save(commit=False)
            spool.filament = filament
            spool.created_by = request.user
            spool.save()
            messages.success(request, 'Another spool was added.')
            return redirect('home')
    else:
        form = SpoolForm(initial={'spool_weight_kg': None, 'remaining_weight_kg': None, 'status': 'full'})
    return render(
        request,
        'core/spool_form.html',
        {'form': form, 'filament': filament, 'page_title': f'Add spool for {filament}'},
    )


@login_required
def spool_edit(request, pk):
    spool = get_object_or_404(Spool.objects.select_related('filament', 'filament__manufacturer'), pk=pk)
    if request.method == 'POST':
        form = SpoolForm(request.POST, instance=spool)
        if form.is_valid():
            updated_spool = form.save(commit=False)
            updated_spool.created_by = spool.created_by or request.user
            updated_spool.save()
            messages.success(request, 'Spool updated.')
            return redirect('home')
    else:
        form = SpoolForm(instance=spool)
    return render(request, 'core/spool_form.html', {'form': form, 'filament': spool.filament, 'page_title': 'Edit spool'})
