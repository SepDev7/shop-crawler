from django.contrib.auth import authenticate, login, logout
from rest_framework.authtoken.models import Token
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Car, Cart, CartItem
from .serializers import CarSerializer, CartSerializer, CartItemSerializer, UserSerializer
from django.shortcuts import get_object_or_404
from rest_framework.throttling import ScopedRateThrottle
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class UserCreate(APIView):
    @swagger_auto_schema(
        operation_description="Create a new user",
        request_body=UserSerializer,
        responses={201: UserSerializer, 400: 'Bad Request'}
    )
    def post(self, request, format=None):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLogin(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'user_login'

    @swagger_auto_schema(
        operation_description="Login a user with username and password",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=['username', 'password'],
        ),
        responses={200: openapi.Schema(type=openapi.TYPE_OBJECT, properties={
            'token': openapi.Schema(type=openapi.TYPE_STRING)
        }), 400: 'Bad Request'}
    )
    def post(self, request, format=None):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid Credentials'}, status=status.HTTP_400_BAD_REQUEST)
    
class UserLogout(APIView):
    @swagger_auto_schema(
        operation_description="Logout the current user"
    )
    def post(self, request, format=None):
        request.user.auth_token.delete()
        logout(request)
        return Response(status=status.HTTP_200_OK)
    
class CarListView(generics.ListAPIView):
    queryset = Car.objects.all()
    serializer_class = CarSerializer

    @swagger_auto_schema(
        operation_description="Retrieve a list of available cars",
        responses={200: CarSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class AddToCartView(APIView):
    @swagger_auto_schema(
        operation_description="Add a car to the user's cart",
        responses={200: 'Added to cart', 404: 'Car not found'}
    )
    def post(self, request, Car_id):
        car = get_object_or_404(Car, id=Car_id)
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=car)
        if not created:
            cart_item.quantity += 1
        cart_item.save()
        return Response({'status': 'Added to cart'}, status=status.HTTP_200_OK)

class CartDetailView(generics.RetrieveAPIView):
    serializer_class = CartSerializer

    @swagger_auto_schema(
        operation_description="Get details of the current user's cart",
        responses={200: CartSerializer}
    )
    def get_object(self):
        return get_object_or_404(Cart, user=self.request.user)

class UpdateCartItemView(APIView):
    @swagger_auto_schema(
        operation_description="Update a cart item quantity",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
            },
            required=['quantity'],
        ),
        responses={200: 'Cart updated', 400: 'Invalid quantity', 404: 'Item not found'}
    )
    def post(self, request, item_id):
        cart_item = get_object_or_404(CartItem, id=item_id)
        
        try:
            quantity = int(request.data.get('quantity', cart_item.quantity))
        except ValueError:
            return Response({'error': 'Invalid quantity'}, status=status.HTTP_400_BAD_REQUEST)
        
        if quantity <= 0:
            cart_item.delete()
        else:
            cart_item.quantity = quantity
            cart_item.save()
        
        return Response({'status': 'Cart updated'}, status=status.HTTP_200_OK)

class CheckoutView(APIView):
    @swagger_auto_schema(
        operation_description="Checkout the current user's cart",
        responses={200: 'Checkout successful', 404: 'Cart not found'}
    )
    def post(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        cart.items.all().delete()  
        return Response({'status': 'Checkout successful'}, status=status.HTTP_200_OK)
