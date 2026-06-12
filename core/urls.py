from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    filament_create,
    filament_detail,
    filament_edit,
    home,
    spool_create,
    spool_delete,
    spool_edit,
    spool_quick_use,
)

urlpatterns = [
    path('', home, name='home'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='core/login.html'),
        name='login',
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(next_page='login'),
        name='logout',
    ),
    path('filaments/<int:pk>/', filament_detail, name='filament_detail'),
    path('filaments/new/', filament_create, name='filament_create'),
    path('filaments/<int:pk>/edit/', filament_edit, name='filament_edit'),
    path('filaments/<int:filament_id>/spools/new/', spool_create, name='spool_create'),
    path('filaments/<int:filament_id>/spools/use/', spool_quick_use, name='spool_quick_use'),
    path('spools/<int:pk>/edit/', spool_edit, name='spool_edit'),
    path('spools/<int:pk>/delete/', spool_delete, name='spool_delete'),
]
