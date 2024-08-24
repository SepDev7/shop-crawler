from django.urls import path
from .views import UserCreate, UserLogin, UserLogout, ProductListView, AddToCartView, CartDetailView, UpdateCartItemView, CheckoutView

urlpatterns = [
    path('signup/', UserCreate.as_view(), name='user-create'),
    path('login/', UserLogin.as_view(), name='user-login'),
    path('logout/', UserLogout.as_view(), name='user-logout'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('cart/add/<int:product_id>/', AddToCartView.as_view(), name='add-to-cart'),
    path('cart/', CartDetailView.as_view(), name='cart-detail'),
    path('cart/item/update/<int:item_id>/', UpdateCartItemView.as_view(), name='update-cart-item'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
]
