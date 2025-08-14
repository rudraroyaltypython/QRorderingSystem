# orders/serializers.py
from rest_framework import serializers
from .models import MenuItem, Order, OrderItem, Table


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'price', 'is_available', 'description', 'category']


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
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'table', 'status', 'created_at', 'items', 'notes', 'total_amount']

    def get_table(self, obj) -> str:
        # Return the table code (used in QR)
        return obj.table.code if obj.table else None

    def get_total_amount(self, obj) -> float:
        total = sum((it.qty * it.item.price) for it in obj.items.all())
        return round(float(total), 2)
