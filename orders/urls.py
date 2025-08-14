from django.urls import path
from . import views

urlpatterns = [
    # Frontend pages
    path('menu/', views.menu_page, name='menu_page'),
    path('staff/', views.staff_page, name='staff_page'),
    path('expired/', views.account_expired, name='account_expired'),  # NEW expired page

    # API endpoints
    path('api/menu/', views.menu_api, name='menu_api'),
    path('api/orders/', views.api_create_order, name='api_create_order'),
    path('api/orders/<int:order_id>/', views.api_update_order, name='api_update_order'),
    path('api/staff/orders/', views.api_staff_orders, name='api_staff_orders'),
    path('api/customer/orders/', views.api_customer_orders, name='api_customer_orders'),
]
