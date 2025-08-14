from django.contrib import admin
from django.utils.html import format_html
from django.utils.timezone import now, timedelta
from django.http import HttpResponse
import csv

from .models import (
    LicenseConfig, Restaurant, Config, Table, Category, MenuItem,
    Order, OrderItem
)


# ------------------------
# LICENSE CONFIG
# ------------------------
@admin.register(LicenseConfig)
class LicenseConfigAdmin(admin.ModelAdmin):
    list_display = ('user', 'expiry_date', 'status_badge')
    list_filter = ('expiry_date',)
    search_fields = ('user__username',)

    def status_badge(self, obj):
        if obj.is_active():
            return format_html('<span style="color:green;font-weight:bold;">Active</span>')
        return format_html('<span style="color:red;font-weight:bold;">Expired</span>')
    status_badge.short_description = "Status"


# ------------------------
# RESTAURANT
# ------------------------
@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'expiry_date', 'is_active', 'status_flag')
    list_filter = ('is_active', 'expiry_date')
    search_fields = ('name', 'owner__username', 'owner__email')
    actions = ['deactivate_expired']

    @admin.display(description="Status")
    def status_flag(self, obj):
        if obj.is_active_now():
            return format_html('<span style="color:green;font-weight:bold;">Active</span>')
        else:
            return format_html('<span style="color:red;font-weight:bold;">Expired/Inactive</span>')

    def deactivate_expired(self, request, queryset):
        count = queryset.filter(expiry_date__lt=now().date()).update(is_active=False)
        self.message_user(request, f"{count} restaurant(s) deactivated (expired).")
    deactivate_expired.short_description = "Deactivate expired restaurants"


# ------------------------
# CONFIG
# ------------------------
@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'server_ip', 'site_name')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(restaurant__owner=request.user)


# ------------------------
# TABLES
# ------------------------
@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'qr_image', 'restaurant')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(restaurant__owner=request.user)


# ------------------------
# CATEGORY
# ------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'restaurant')
    list_editable = ('is_active',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(restaurant__owner=request.user)


# ------------------------
# MENU ITEMS
# ------------------------
@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'type', 'price', 'is_available', 'restaurant')
    list_editable = ('is_available',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(restaurant__owner=request.user)


# ------------------------
# INLINE FOR ORDER ITEMS
# ------------------------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('item', 'qty')
    extra = 0


# ------------------------
# CSV EXPORT
# ------------------------
def export_sales_csv(queryset, title):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{title}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Table', 'Status', 'Created At', 'Total Amount'])

    total_sum = 0
    for order in queryset:
        total = order.total_amount
        total_sum += total
        writer.writerow([order.id, order.table.name if order.table else '', order.status, order.created_at, total])

    writer.writerow([])
    writer.writerow(['', '', '', 'TOTAL SALES', total_sum])
    return response


# ------------------------
# ORDERS
# ------------------------
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'table', 'status', 'created_at', 'total_amount', 'restaurant')
    inlines = (OrderItemInline,)
    actions = ['export_daily_sales', 'export_weekly_sales', 'export_monthly_sales']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(restaurant__owner=request.user)

    def export_daily_sales(self, request, queryset):
        today = now().date()
        qs = queryset.filter(created_at__date=today, status='PAID')
        return export_sales_csv(qs, f"daily_sales_{today}")
    export_daily_sales.short_description = "Export Daily Sales (Paid Orders)"

    def export_weekly_sales(self, request, queryset):
        start = now().date() - timedelta(days=7)
        qs = queryset.filter(created_at__date__gte=start, status='PAID')
        return export_sales_csv(qs, f"weekly_sales_{start}_to_{now().date()}")
    export_weekly_sales.short_description = "Export Weekly Sales (Paid Orders)"

    def export_monthly_sales(self, request, queryset):
        start = now().date().replace(day=1)
        qs = queryset.filter(created_at__date__gte=start, status='PAID')
        return export_sales_csv(qs, f"monthly_sales_{start}")
    export_monthly_sales.short_description = "Export Monthly Sales (Paid Orders)"
