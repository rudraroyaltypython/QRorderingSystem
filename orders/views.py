from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
from .models import Category, MenuItem, Table, Order, OrderItem
from .serializers import OrderSerializer


# ==========================================================
# ORDER VIEWSET (For Django REST Framework Browsable API)
# ==========================================================
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer

    def partial_update(self, request, *args, **kwargs):
        """Allow partial updates to order status"""
        instance = self.get_object()
        status_value = request.data.get("status")

        if status_value in dict(Order.STATUS_CHOICES).keys():
            instance.status = status_value
            instance.save()
            return Response({"status": "updated"})
        return Response({"error": "Invalid status"}, status=400)


# ==========================================================
# API: Get Customer Orders by Table Code
# ==========================================================
@api_view(['GET'])
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


# ==========================================================
# FRONTEND PAGES
# ==========================================================
def menu_page(request):
    """Customer-facing menu page"""
    return render(request, 'orders/menu.html')

def staff_page(request):
    """Staff dashboard page"""
    return render(request, 'orders/staff.html')


# ==========================================================
# API: Menu (Grouped by Active Categories)
# ==========================================================
@api_view(['GET'])
def menu_api(request):
    """
    Returns menu grouped by active categories.
    Only items marked as available are included.
    """
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
                    "type": item.type,  # VEG, NONVEG, OTHER
                }
                for item in items
            ]
        })

    return Response(data)


# ==========================================================
# API: Create New Order
# ==========================================================
@csrf_exempt
@api_view(['POST'])
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

    # Create Order
    order = Order.objects.create(table=table, notes=notes)

    # Add Ordered Items
    for it in items:
        try:
            menu_item = MenuItem.objects.get(pk=it['item_id'])
        except MenuItem.DoesNotExist:
            continue
        OrderItem.objects.create(order=order, item=menu_item, qty=it.get('qty', 1))

    return Response(OrderSerializer(order).data, status=201)


# ==========================================================
# API: Get Orders for Staff (with optional status filter)
# ==========================================================
@api_view(['GET'])
def api_staff_orders(request):
    status_q = request.GET.get('status')
    qs = Order.objects.all().order_by('-created_at')
    if status_q:
        qs = qs.filter(status=status_q)
    return Response(OrderSerializer(qs, many=True).data)


# ==========================================================
# API: Update Order Status
# ==========================================================
@csrf_exempt
@api_view(['PATCH'])
def api_update_order(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    new_status = request.data.get('status')

    if new_status not in [c[0] for c in order.STATUS_CHOICES]:
        return Response({'detail': 'Invalid status'}, status=400)

    order.status = new_status
    order.save()
    return Response(OrderSerializer(order).data)
