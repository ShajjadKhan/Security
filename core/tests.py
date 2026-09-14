from django.test import TestCase
from django.urls import reverse

from core.models import Property, User
from gatepass.models import GatePass
from lostfound.models import LostFoundItem
from visitors.models import Visitor


class PropertyAccessTests(TestCase):
    def setUp(self):
        self.alpha = Property.objects.create(name='Alpha Hotel', code='ALPHA')
        self.beta = Property.objects.create(name='Beta Hotel', code='BETA')
        self.director = User.objects.create_user(
            username='director',
            password='pass12345',
            role='director',
            assigned_property=self.alpha,
        )
        self.director.cluster_properties.add(self.alpha)
        self.officer = User.objects.create_user(
            username='officer',
            password='pass12345',
            role='officer',
            assigned_property=self.alpha,
        )
        self.unassigned = User.objects.create_user(
            username='unassigned',
            password='pass12345',
            role='officer',
        )

    def test_unassigned_non_owner_has_no_property_access(self):
        self.assertEqual(self.unassigned.get_accessible_properties().count(), 0)

    def test_property_switch_requires_accessible_property(self):
        self.client.force_login(self.officer)
        response = self.client.get(reverse('property_switch', args=[self.beta.pk]))
        self.assertEqual(response.status_code, 404)

    def test_director_cannot_collect_saas_fee(self):
        self.client.force_login(self.director)
        response = self.client.post(reverse('collect_fee', args=[self.alpha.pk]), {'amount': '9999'})
        self.assertEqual(response.status_code, 302)
        self.alpha.refresh_from_db()
        self.assertEqual(self.alpha.invoices.count(), 0)

    def test_operational_lists_are_limited_to_accessible_properties(self):
        Visitor.objects.create(
            property=self.alpha,
            full_name='Allowed Visitor',
            phone='111',
            id_number='A1',
            purpose='Meeting',
            checked_in_by=self.officer,
        )
        Visitor.objects.create(
            property=self.beta,
            full_name='Hidden Visitor',
            phone='222',
            id_number='B1',
            purpose='Meeting',
        )
        GatePass.objects.create(
            property=self.alpha,
            sender_name='Engineering',
            destination_entity='Workshop',
            carrier_name='Allowed Carrier',
            carrier_phone='111',
            authorized_by_manager='Manager',
        )
        GatePass.objects.create(
            property=self.beta,
            sender_name='Engineering',
            destination_entity='Workshop',
            carrier_name='Hidden Carrier',
            carrier_phone='222',
            authorized_by_manager='Manager',
        )
        LostFoundItem.objects.create(
            property=self.alpha,
            title='Allowed Item',
            category='electronics',
            description='Phone',
            found_location='Lobby',
        )
        LostFoundItem.objects.create(
            property=self.beta,
            title='Hidden Item',
            category='electronics',
            description='Laptop',
            found_location='Lobby',
        )

        self.client.force_login(self.officer)

        visitor_response = self.client.get(reverse('visitor_list'))
        self.assertContains(visitor_response, 'Allowed Visitor')
        self.assertNotContains(visitor_response, 'Hidden Visitor')

        gatepass_response = self.client.get(reverse('gatepass_list'))
        self.assertContains(gatepass_response, 'Allowed Carrier')
        self.assertNotContains(gatepass_response, 'Hidden Carrier')

        lostfound_response = self.client.get(reverse('lostfound_list'))
        self.assertContains(lostfound_response, 'Allowed Item')
        self.assertNotContains(lostfound_response, 'Hidden Item')

# Create your tests here.
