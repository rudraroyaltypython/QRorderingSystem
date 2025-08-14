from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# DRF Router for OrderViewSet
router = DefaultRouter()
router.register(r'orders', views.OrderViewSet, basename='order')

urlpatterns = [
    # DRF API Routes
    path('api/', include(router.urls)),

    # API Endpoints
    path('api/menu/', views.menu_api, name='menu_api'),
    path('api/orders/create/', views.api_create_order, name='api_create_order'),
    path('api/orders/customer/', views.api_customer_orders, name='api_customer_orders'),
    path('api/orders/staff/', views.api_staff_orders, name='api_staff_orders'),
    path('api/orders/<int:order_id>/update/', views.api_update_order, name='api_update_order'),

    # Frontend Pages
    path('', views.menu_page, name='menu_page'),
    path('staff/', views.staff_page, name='staff_page'),
]
