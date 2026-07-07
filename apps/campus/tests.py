from django.test import RequestFactory, TestCase

from apps.campus.BBL.Queries.listing import ListingQuery
from apps.campus.models import Category, CampusHotspot, Listing
from apps.users.models import User


class ListingQueryTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='seller@example.com',
            password='testpass123',
            first_name='Jane',
            last_name='Doe',
            visibility=False,
        )
        self.category = Category.objects.create(name='Electronics', slug='electronics', icon='📱')
        self.hotspot = CampusHotspot.objects.create(name='Independence Hall')
        self.listing = Listing.objects.create(
            user=self.user,
            category=self.category,
            title='HP Laptop Core i5 / 8GB RAM',
            description='Great condition',
            price='145000',
            badge='FEATURED',
        )
        self.listing.hotspots.add(self.hotspot)

    def test_listing_details_hides_private_seller_fields_when_visibility_is_disabled(self):
        request = self.factory.get('/api/listings/1/')

        result = ListingQuery.listing_details(request=request, user=self.user, listing_id=self.listing.id)

        self.assertEqual(result.status_code, 200)
        self.assertIn('seller', result.data)

        seller = result.data['seller']
        self.assertEqual(seller['visibility'], False)
        self.assertIsNone(seller['email'])
        self.assertIsNone(seller['phone'])
        self.assertIsNone(seller['profile_picture'])
        self.assertIsNone(seller['level'])
        self.assertIsNone(seller['matric_no'])
        self.assertIsNone(seller['name'])
