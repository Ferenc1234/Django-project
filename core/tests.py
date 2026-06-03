from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Filament, Manufacturer, Spool


class CatalogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='secret12345')
        self.sun = Manufacturer.objects.create(name='Sunlu')
        self.prusament = Manufacturer.objects.create(name='Prusament')
        self.petg = Filament.objects.create(
            manufacturer=self.sun,
            product_name='PLA Matte Black',
            material='PLA',
            color_mode='single',
            primary_color='Black',
        )
        self.gradient = Filament.objects.create(
            manufacturer=self.prusament,
            product_name='Galaxy Gradient',
            material='PLA',
            color_mode='gradient',
            primary_color='Blue',
            gradient_description='Blue to violet shift',
        )
        self.petg_spool = Spool.objects.create(
            filament=self.petg,
            spool_weight_kg=Decimal('1.00'),
            remaining_weight_kg=Decimal('0.70'),
            status='in_use',
        )
        self.gradient_spool = Spool.objects.create(
            filament=self.gradient,
            spool_weight_kg=Decimal('2.00'),
            remaining_weight_kg=Decimal('2.00'),
            status='full',
        )

    def test_catalog_is_public(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Filament catalog')
        self.assertContains(response, 'PLA Matte Black')
        self.assertContains(response, 'Galaxy Gradient')

    def test_manufacturer_filter_limits_results(self):
        response = self.client.get(reverse('home'), {'manufacturer': self.sun.pk})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PLA Matte Black')
        self.assertNotContains(response, 'Galaxy Gradient')

    def test_spool_progress_is_rendered(self):
        response = self.client.get(reverse('home'))

        self.assertContains(response, 'style="width: 70%;"')
        self.assertContains(response, '700 g left · 70%')
        self.assertContains(response, '700 g left of 1000 g')

    def test_login_required_for_filament_creation(self):
        response = self.client.get(reverse('filament_create'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_authenticated_user_can_add_filament(self):
        self.client.login(username='tester', password='secret12345')

        response = self.client.post(
            reverse('filament_create'),
            {
                'manufacturer': '',
                'manufacturer_name': 'Polymaker',
                'product_name': 'PolyTerra Green',
                'material': 'PLA',
                'color_mode': 'single',
                'primary_color': 'Green',
                'secondary_color': '',
                'tertiary_color': '',
                'gradient_description': '',
                'notes': 'Matte finish',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Filament.objects.filter(product_name='PolyTerra Green').count(), 1)

    def test_authenticated_user_can_buy_another_spool(self):
        self.client.login(username='tester', password='secret12345')

        response = self.client.post(
            reverse('spool_create', kwargs={'filament_id': self.petg.pk}),
            {
                'spool_weight_kg': '0.75',
                'remaining_weight_kg': '',
                'status': 'full',
                'notes': 'New spare spool',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Spool.objects.filter(filament=self.petg).count(), 2)
        new_spool = Spool.objects.filter(filament=self.petg, spool_weight_kg=Decimal('0.75')).latest('id')
        self.assertEqual(new_spool.remaining_weight_kg, Decimal('0.75'))
