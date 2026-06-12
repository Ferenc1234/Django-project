import re
from decimal import Decimal
from decimal import InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CatalogFilterForm, FilamentForm, SpoolForm
from .models import Filament, SPOOL_STATUS_EMPTY, Spool

HEX_COLOR_RE = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')

COLOR_ALIASES = {
    'aqua blue': '#00b7eb',
    'baby blue': '#89cff0',
    'burgundy': '#800020',
    'chartreuse': '#7fff00',
    'gold': '#ffd700',
    'grey': '#808080',
    'light blue': '#add8e6',
    'lime green': '#32cd32',
    'mint': '#3eb489',
    'navy blue': '#000080',
    'olive green': '#808000',
    'sky blue': '#87ceeb',
    'teal': '#008080',
    'violet': '#8f00ff',
}

PLACEHOLDER_COLORS = {'gradient', 'n/a', 'na', 'none', '-'}


def _resolve_color_token(value):
    if not value:
        return '#64748b'
    cleaned = value.strip()
    if HEX_COLOR_RE.match(cleaned):
        return cleaned
    lowered = ' '.join(cleaned.lower().split())
    if lowered in PLACEHOLDER_COLORS:
        return '#64748b'
    if lowered in COLOR_ALIASES:
        return COLOR_ALIASES[lowered]
    if lowered.replace(' ', '') in COLOR_ALIASES:
        return COLOR_ALIASES[lowered.replace(' ', '')]
    if ' ' in lowered:
        return '#64748b'
    return lowered


def _build_progress_style(color_mode, color_tokens):
    colors = [_resolve_color_token(token) for token in color_tokens if token]
    if not colors:
        return 'background: #64748b;'
    if len(colors) == 1:
        return f'background: {colors[0]};'
    if color_mode == 'gradient':
        return f"background-image: linear-gradient(90deg, {', '.join(colors)});"

    band = 100 / len(colors)
    stops = []
    for index, color in enumerate(colors):
        start = band * index
        end = band * (index + 1)
        stops.append(f'{color} {start:.2f}%')
        stops.append(f'{color} {end:.2f}%')
    return f"background-image: linear-gradient(180deg, {', '.join(stops)});"


def _build_dot_style(color_mode, color_tokens, primary_color):
    if color_mode != 'gradient':
        return f'background: {_resolve_color_token(primary_color)};'

    colors = [_resolve_color_token(token) for token in color_tokens if token]
    if not colors:
        return 'background: #64748b;'
    if len(colors) == 1:
        return f'background: {colors[0]};'

    step = 360 / len(colors)
    color_stops = [f'{color} {index * step:.2f}deg' for index, color in enumerate(colors)]
    # Repeat the first color at 360deg so the seam closes smoothly.
    color_stops.append(f'{colors[0]} 360deg')
    ring = ', '.join(color_stops)
    return f'background: conic-gradient(from 0deg at 48% 44%, {ring});'


def _filament_palette(filament):
    base = [filament.primary_color, filament.secondary_color, filament.tertiary_color]
    colors = [
        value
        for value in base
        if value and value.strip().lower() not in PLACEHOLDER_COLORS
    ]
    if filament.color_mode == 'single':
        colors = [filament.primary_color]
    elif filament.color_mode == 'dual':
        colors = [value for value in (filament.primary_color, filament.secondary_color) if value]
    elif filament.color_mode == 'tricolor':
        colors = [value for value in (filament.primary_color, filament.secondary_color, filament.tertiary_color) if value]
    elif filament.color_mode == 'gradient':
        gradient_colors = []
        if filament.gradient_description:
            parsed = re.split(r'\bto\b|/|->|,|•', filament.gradient_description)
            gradient_colors = [token.strip() for token in parsed if token.strip()]
        colors = gradient_colors or colors

    deduped = []
    seen = set()
    for color in colors:
        key = color.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(color)
    fallback = filament.primary_color if filament.primary_color and filament.primary_color.strip().lower() not in PLACEHOLDER_COLORS else 'gray'
    return deduped or [fallback]


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

    catalog_rows = []
    for filament in filaments:
        spools = list(filament.spools.all())
        active_spools = [
            spool
            for spool in spools
            if spool.status != SPOOL_STATUS_EMPTY and (spool.remaining_weight_kg or Decimal('0')) > Decimal('0')
        ]
        spool_count = len(active_spools)

        bar_percentage = 0
        bar_status = 'empty'
        status_label = 'Out of stock'
        weight_label = '0 g left'
        weight_detail = ''

        if spool_count > 1:
            total_remaining_g = int(sum((spool.remaining_weight_kg or Decimal('0')) for spool in active_spools) * Decimal('1000'))
            bar_percentage = 100
            bar_status = 'full'
            status_label = f'{spool_count} spools available'
            weight_label = f'{total_remaining_g} g across {spool_count} spools'
        elif spool_count == 1:
            spool = active_spools[0]
            bar_percentage = spool.remaining_percentage
            bar_status = spool.status
            status_label = spool.get_status_display()
            weight_label = spool.remaining_summary
            weight_detail = f'{spool.remaining_weight_g} g left of {spool.total_weight_g} g'

        priced_spools = [spool for spool in active_spools if spool.price_per_spool is not None]
        price_label = 'N/A'
        if priced_spools:
            total_price = sum((spool.price_per_spool for spool in priced_spools), Decimal('0'))
            total_weight = sum((spool.spool_weight_kg for spool in priced_spools), Decimal('0'))
            if total_weight > 0:
                price_per_kg = (total_price / total_weight).quantize(Decimal('0.01'))
                price_label = f'{price_per_kg} / kg'

        palette = _filament_palette(filament)

        catalog_rows.append(
            {
                'filament': filament,
                'spool_count': spool_count,
                'status_label': status_label,
                'bar_percentage': bar_percentage,
                'bar_status': bar_status,
                'weight_label': weight_label,
                'weight_detail': weight_detail,
                'price_label': price_label,
                'primary_color_css': _resolve_color_token(filament.primary_color),
                'progress_style': _build_progress_style(filament.color_mode, palette),
                'dot_style': _build_dot_style(filament.color_mode, palette, filament.primary_color),
            }
        )

    return render(
        request,
        'core/home.html',
        {
            'filter_form': filter_form,
            'catalog_rows': catalog_rows,
        },
    )


def filament_detail(request, pk):
    filament = get_object_or_404(
        Filament.objects.select_related('manufacturer').prefetch_related('spools'),
        pk=pk,
    )
    spools = list(filament.spools.all())
    active_spools = [
        spool
        for spool in spools
        if spool.status != SPOOL_STATUS_EMPTY and (spool.remaining_weight_kg or Decimal('0')) > Decimal('0')
    ]
    total_remaining_g = int(sum((spool.remaining_weight_kg or Decimal('0')) for spool in active_spools) * Decimal('1000'))
    total_spool_weight_g = int(sum((spool.spool_weight_kg for spool in spools), Decimal('0')) * Decimal('1000'))

    return render(
        request,
        'core/filament_detail.html',
        {
            'filament': filament,
            'spools': spools,
            'active_spools': active_spools,
            'total_remaining_g': total_remaining_g,
            'total_spool_weight_g': total_spool_weight_g,
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


@login_required
@require_POST
def spool_delete(request, pk):
    spool = get_object_or_404(Spool.objects.select_related('filament', 'filament__manufacturer'), pk=pk)
    filament_label = str(spool.filament)
    spool.delete()
    messages.success(request, f'Spool removed from {filament_label}.')
    return HttpResponseRedirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or '/')


@login_required
@require_POST
def spool_quick_use(request, filament_id):
    filament = get_object_or_404(Filament.objects.select_related('manufacturer').prefetch_related('spools'), pk=filament_id)
    grams_raw = (request.POST.get('grams_used') or '').strip()

    try:
        grams_used = Decimal(grams_raw)
    except (InvalidOperation, TypeError):
        messages.error(request, 'Enter a valid number of grams to subtract.')
        return HttpResponseRedirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or '/')

    if grams_used <= 0:
        messages.error(request, 'Usage must be greater than 0 grams.')
        return HttpResponseRedirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or '/')

    usage_kg = grams_used / Decimal('1000')
    target_spool = (
        filament.spools.exclude(status=SPOOL_STATUS_EMPTY)
        .filter(remaining_weight_kg__gt=0)
        .order_by('-remaining_weight_kg', '-created_at', '-id')
        .first()
    )

    if not target_spool:
        messages.error(request, 'No spool with remaining filament was found for this row.')
        return HttpResponseRedirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or '/')

    new_remaining = (target_spool.remaining_weight_kg or Decimal('0')) - usage_kg
    if new_remaining <= 0:
        target_spool.delete()
        messages.success(request, f'Used {grams_used} g. The spool reached 0 g and was removed.')
    else:
        rounded_remaining = new_remaining.quantize(Decimal('0.01'))
        target_spool.remaining_weight_kg = rounded_remaining
        low_threshold = target_spool.spool_weight_kg * Decimal('0.10')
        if rounded_remaining <= low_threshold:
            target_spool.status = 'low'
        elif rounded_remaining < target_spool.spool_weight_kg:
            target_spool.status = 'in_use'
        else:
            target_spool.status = 'full'
        target_spool.save()
        messages.success(request, f'Used {grams_used} g from {filament}.')

    return HttpResponseRedirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or '/')
