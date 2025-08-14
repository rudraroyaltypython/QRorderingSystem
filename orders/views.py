from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import Category, MenuItem, Table, Order, OrderItem, LicenseConfig, Restaurant
from .serializers import OrderSerializer
from functools import wraps
from datetime import date


# ------------------------
# LICENSE CHECK DECORATOR (for authenticated staff)
# ------------------------
def license_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return Response({'detail': 'Authentication required'}, status=401)
        try:
            license_obj = LicenseConfig.objects.get(user=user)
            if not license_obj.is_active():
                return Response({'detail': 'License expired'}, status=403)
        except LicenseConfig.DoesNotExist:
            return Response({'detail': 'No license found'}, status=403)

        restaurant = getattr(user, "restaurant_owner", None)
        if restaurant and not restaurant.is_active_now():
            return Response({'detail': 'Restaurant expired or inactive'}, status=403)

        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ------------------------
# LICENSE CHECK FOR PUBLIC ENDPOINTS (no login required)
# ------------------------
def public_license_check(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        table_code = request.GET.get('table') or request.GET.get('table_code') or request.data.get('table_code')
        if table_code:
            try:
                table = Table.objects.select_related("restaurant").get(code=table_code)
                if not table.restaurant.is_active_now():
                    return Response({'detail': 'Restaurant expired or inactive'}, status=403)
            except Table.DoesNotExist:
                return Response({'detail': 'Invalid table code'}, status=400)
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ------------------------
# ORDER VIEWSET (Browsable API)
# ------------------------
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        status_value = request.data.get("status")
        if status_value in dict(Order.STATUS_CHOICES).keys():
            instance.status = status_value
            instance.save()
            return Response({"status": "updated"})
        return Response({"error": "Invalid status"}, status=400)


# ------------------------
# FRONTEND PAGES
# ------------------------
def menu_page(request):
    return render(request, 'orders/menu.html')

def staff_page(request):
    return render(request, 'orders/staff.html')


# ------------------------
# API: Menu (Public)
# ------------------------
@api_view(['GET'])
@permission_classes([AllowAny])
@public_license_check
def menu_api(request):
    categories = Category.objects.filter(is_active=True).order_by('name')
    data = []
    for cat in categories:
        items = MenuItem.objects.filter(category=cat, is_available=True).order_by('name')
        data.append({
            "category": cat.name,
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "price": float(item.price),
                    "description": item.description,
                    "type": item.type,
                }
                for item in items
            ]
        })
    return Response(data)


# ------------------------
# API: Create Order (Public)
# ------------------------
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@public_license_check
def api_create_order(request):
    data = request.data
    table_code = data.get('table_code')
    items = data.get('items', [])
    notes = data.get('notes', '')

    if not table_code:
        return Response({'detail': 'table_code required'}, status=400)

    try:
        table = Table.objects.get(code=table_code)
    except Table.DoesNotExist:
        return Response({'detail': 'Invalid table code'}, status=400)

    order = Order.objects.create(restaurant=table.restaurant, table=table, notes=notes)

    for it in items:
        try:
            menu_item = MenuItem.objects.get(pk=it['item_id'])
        except MenuItem.DoesNotExist:
            continue
        OrderItem.objects.create(order=order, item=menu_item, qty=it.get('qty', 1))

    return Response(OrderSerializer(order).data, status=201)


# ------------------------
# API: Staff Orders (Protected)
# ------------------------
@api_view(['GET'])
@license_required
def api_staff_orders(request):
    status_q = request.GET.get('status')
    qs = Order.objects.all().order_by('-created_at')
    if status_q:
        qs = qs.filter(status=status_q)
    return Response(OrderSerializer(qs, many=True).data)


# ------------------------
# API: Customer Orders (Public)
# ------------------------
@api_view(['GET'])
@permission_classes([AllowAny])
@public_license_check
def api_customer_orders(request):
    table_code = request.GET.get('table') or request.GET.get('table_code')
    if not table_code:
        return Response({'detail': 'table query parameter required'}, status=400)
    try:
        table = Table.objects.get(code=table_code)
    except Table.DoesNotExist:
        return Response({'detail': 'Invalid table code'}, status=400)

    orders = Order.objects.filter(table=table).order_by('-created_at')
    return Response(OrderSerializer(orders, many=True).data)


# ------------------------
# API: Update Order Status (Protected)
# ------------------------
@csrf_exempt
@api_view(['PATCH'])
@license_required
def api_update_order(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    new_status = request.data.get('status')

    if new_status not in [c[0] for c in order.STATUS_CHOICES]:
        return Response({'detail': 'Invalid status'}, status=400)

    order.status = new_status
    order.save()
    return Response(OrderSerializer(order).data)


def account_expired(request):
    return render(request, 'orders/account_expired.html')
