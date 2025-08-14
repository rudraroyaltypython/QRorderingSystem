# orders/serializers.py
from rest_framework import serializers
from django.db.models import Sum, F, DecimalField
from .models import MenuItem, Order, OrderItem, Table


class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'type', 'price', 'is_available',
            'description', 'category', 'category_name'
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    item = MenuItemSerializer(read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'item', 'qty', 'line_total']

    def get_line_total(self, obj) -> float:
        return round(float(obj.qty * obj.item.price), 2)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    table = serializers.SerializerMethodField()
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'restaurant_name', 'table', 'status',
            'created_at', 'items', 'notes', 'total_amount'
        ]

    def get_table(self, obj) -> str:
        # Return the table code (used in QR)
        return obj.table.code if obj.table else None

    def get_total_amount(self, obj) -> float:
        total = obj.items.aggregate(
            total=Sum(F('qty') * F('item__price'), output_field=DecimalField(max_digits=12, decimal_places=2))
        )['total'] or 0
        return round(float(total), 2)
