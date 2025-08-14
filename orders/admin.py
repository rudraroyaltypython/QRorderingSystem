from django.contrib import admin
from .models import Config, Table, Category, MenuItem, Order, OrderItem, LicenseConfig
import csv
from django.http import HttpResponse
from django.utils.timezone import now, timedelta
from django.contrib.auth import get_user_model

User = get_user_model()

# ------------------------
# LICENSE CONFIG
# ------------------------
@admin.register(LicenseConfig)
class LicenseConfigAdmin(admin.ModelAdmin):
    list_display = ('user', 'expiry_date')
    list_filter = ('expiry_date',)
    search_fields = ('user__username',)


# ------------------------
# CONFIG
# ------------------------
@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    list_display = ('server_ip', 'restaurant_name')

    def has_add_permission(self, request):
        # Allow only one config row per user
        return not Config.objects.filter(user=request.user).exists()

    def get_queryset(self, request):
        # Superuser can see all, others see only their own config
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


# ------------------------
# TABLES
# ------------------------
@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'qr_image')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(config__user=request.user)


# ------------------------
# CATEGORY
# ------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_editable = ('is_active',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(config__user=request.user)


# ------------------------
# MENU ITEMS
# ------------------------
@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'type', 'price', 'is_available')
    list_editable = ('is_available',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(category__config__user=request.user)


# ------------------------
# INLINE FOR ORDER ITEMS
# ------------------------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('item', 'qty')


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
    list_display = ('id', 'table', 'status', 'created_at', 'total_amount')
    inlines = (OrderItemInline,)
    actions = ['export_daily_sales', 'export_weekly_sales', 'export_monthly_sales']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(table__config__user=request.user)

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
