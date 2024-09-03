from unittest import TestCase
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token  # Ensure this is correctly imported
from .models import Car, Cart, CartItem
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from django.db import transaction
from asgiref.sync import sync_to_async
from aioresponses import aioresponses
import aiohttp
from .models import Car
from .tasks import fetch_page, scrape_page, save_to_db

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user():
    return User.objects.create_user(username='testuser', password='testpass')

@pytest.fixture
def authenticated_client(api_client, user):
    api_client.login(username='testuser', password='testpass')
    return api_client

@pytest.fixture
def car():
    return Car.objects.create(title='Test Car', price='10000', image_url='http://example.com/car.jpg')

@pytest.fixture
def cart(user):
    return Cart.objects.create(user=user)

@pytest.fixture
def cart_item(cart, car):
    return CartItem.objects.create(cart=cart, product=car, quantity=1)

# Test UserCreate View
@pytest.mark.django_db
def test_user_create_view(api_client):
    url = reverse('user-create')
    data = {'username': 'newuser', 'password': 'newpass'}
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_201_CREATED
    assert User.objects.filter(username='newuser').exists()

# Test UserLogin View
@pytest.mark.django_db
def test_user_login_view(api_client, user):
    url = reverse('user-login')
    data = {'username': 'testuser', 'password': 'testpass'}
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_200_OK
    assert 'token' in response.data

@pytest.mark.django_db
def test_user_login_invalid_credentials(api_client):
    url = reverse('user-login')
    data = {'username': 'wronguser', 'password': 'wrongpass'}
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'error' in response.data

# Test UserLogout View
@pytest.mark.django_db
def test_user_logout_view(authenticated_client, user):
    url = reverse('user-logout')
    token = Token.objects.create(user=user)
    authenticated_client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
    response = authenticated_client.post(url)
    assert response.status_code == status.HTTP_200_OK
    assert not Token.objects.filter(user=user).exists()

# Test CarListView
@pytest.mark.django_db
def test_car_list_view(api_client, car):
    url = reverse('car-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]['title'] == car.title

# Test AddToCartView
@pytest.mark.django_db
def test_add_to_cart_view():
    user = User.objects.create_user(username='testuser', password='password')
    car = Car.objects.create(title='Test Car', price='10000', image_url='http://example.com/car.jpg')

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse('add-to-cart', args=[car.id])  # This passes Car_id, not product_id
    response = client.post(url, {})

    assert response.status_code == 200
    assert CartItem.objects.filter(cart__user=user, product=car).exists()

@pytest.mark.django_db
def test_add_to_cart_invalid_car():
    user = User.objects.create_user(username='testuser', password='password')

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse('add-to-cart', args=[999])  # Invalid Car_id
    response = client.post(url, {})

    assert response.status_code == 404

@pytest.mark.django_db
def test_cart_detail_view():
    user = User.objects.create_user(username='testuser', password='password')
    cart = Cart.objects.create(user=user)
    car = Car.objects.create(title='Test Car', price='10000', image_url='http://example.com/car.jpg')
    CartItem.objects.create(cart=cart, product=car, quantity=1)
    
    client = APIClient()
    client.force_authenticate(user=user)
    
    url = reverse('cart-detail')
    response = client.get(url)
    
    assert response.status_code == 200
    assert response.data['items'][0]['product']['title'] == 'Test Car'

# Test UpdateCartItemView
# @pytest.mark.django_db
# def test_update_cart_item_view(authenticated_client, cart_item):
#     url = reverse('update-cart-item', args=[cart_item.id])
#     data = {'quantity': 2}
#     response = authenticated_client.post(url, data)
#     assert response.status_code == status.HTTP_200_OK
#     cart_item.refresh_from_db()
#     assert cart_item.quantity == 2


@pytest.mark.django_db
def test_update_cart_item_view():
    user = User.objects.create_user(username='testuser', password='password')
    car = Car.objects.create(title='Test Car', price='10000', image_url='http://example.com/car.jpg')
    cart = Cart.objects.create(user=user)
    cart_item = CartItem.objects.create(cart=cart, product=car, quantity=1)
    
    client = APIClient()
    client.force_authenticate(user=user)
    
    url = reverse('update-cart-item', args=[cart_item.id])
    response = client.post(url, {'quantity': 2})
    
    assert response.status_code == 200
    cart_item.refresh_from_db()
    assert cart_item.quantity == 2
    
    # Test with an invalid quantity (e.g., a string)
    response = client.post(url, {'quantity': 'invalid'})
    assert response.status_code == 400


@pytest.mark.django_db
def test_checkout_view():
    user = User.objects.create_user(username='testuser', password='password')
    car = Car.objects.create(title='Test Car', price='10000', image_url='http://example.com/car.jpg')
    cart = Cart.objects.create(user=user)
    CartItem.objects.create(cart=cart, product=car, quantity=1)
    
    client = APIClient()
    client.force_authenticate(user=user)
    
    url = reverse('checkout')
    response = client.post(url)
    
    assert response.status_code == 200
    assert not CartItem.objects.filter(cart=cart).exists()

@pytest.mark.django_db
def test_checkout_empty_cart():
    user = User.objects.create_user(username='testuser', password='password')
    Cart.objects.create(user=user)
    
    client = APIClient()
    client.force_authenticate(user=user)
    
    url = reverse('checkout')
    response = client.post(url)
    
    assert response.status_code == 200


@pytest.mark.django_db
class CrawlerTests(TestCase):

    @pytest.mark.asyncio
    async def test_fetch_page_html(self):
        mock_response = """
        <html>
            <head><script type="application/json">{"data": {"ads": [{"detail": {"title": "Car Title", "image": "http://example.com/image.jpg"}, "price": {"price": "10000"}}]}}</script></head>
            <body></body>
        </html>
        """
        with aioresponses() as mock:
            mock.get('https://example.com', body=mock_response, headers={'Content-Type': 'text/html'})
            async with aiohttp.ClientSession() as session:
                data = await fetch_page(session, 'https://example.com')
                self.assertIsNotNone(data)
                self.assertEqual(data['data']['ads'][0]['detail']['title'], 'Car Title')
                self.assertEqual(data['data']['ads'][0]['price']['price'], '10000')

    @pytest.mark.asyncio
    async def test_scrape_page(self):
        mock_response = {
            "data": {
                "ads": [
                    {
                        "detail": {
                            "title": "Car Title",
                            "image": "http://example.com/image.jpg"
                        },
                        "price": {
                            "price": "10000"
                        }
                    }
                ]
            }
        }
        with patch('crawler.tasks.fetch_page', return_value=mock_response) as mock_fetch_page:
            # Use AsyncMock for the save_to_db function to handle await
            with patch('crawler.tasks.save_to_db', new_callable=AsyncMock) as mock_save_to_db:
                async with aiohttp.ClientSession() as session:
                    semaphore = asyncio.Semaphore(10)
                    await scrape_page(session, 'https://example.com', semaphore)
                    
                    # Ensure save_to_db is called once
                    mock_save_to_db.assert_called_once()

    def save_to_db(cars):
        session = create_session() # type: ignore
        session.bulk_insert_mappings(Car, cars)
        session.commit()

    @pytest.mark.asyncio
    async def test_save_to_db(self):
        cars = [{'title': 'Car Title', 'price': '10000', 'image_url': 'http://example.com/image.jpg'}]
        
        # Pass only the cars list
        await sync_to_async(save_to_db)(cars)

