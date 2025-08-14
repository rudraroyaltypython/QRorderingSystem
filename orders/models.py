from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.core.files import File
from django.db.models import Sum, F, DecimalField
from io import BytesIO
import qrcode
from datetime import date


# -----------------------------
# LICENSE CONFIG
# -----------------------------
class LicenseConfig(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="license")
    expiry_date = models.DateField(null=True, blank=True)  # allow None for unlimited license

    class Meta:
        verbose_name = "License Configuration"
        verbose_name_plural = "License Configuration"

    def __str__(self):
        return f"License for {self.user.username} - Expires {self.expiry_date}"

    def is_active(self):
        # active if expiry_date is None or today/future
        return (self.expiry_date is None) or (self.expiry_date >= date.today())


# -----------------------------
# TENANT / RESTAURANT
# -----------------------------
class Restaurant(models.Model):
    name = models.CharField(max_length=200)
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="restaurant_owner")
    expiry_date = models.DateField(null=True, blank=True)  # optional
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def is_expired(self):
        return (self.expiry_date is not None) and (self.expiry_date < date.today())

    def is_active_now(self):
        """Check both manual toggle and expiry date."""
        return self.is_active and (self.expiry_date is None or self.expiry_date >= date.today())


# -----------------------------
# SITE / BRAND CONFIG
# -----------------------------
def upload_logo_path(instance, filename):
    return f"branding/{instance.restaurant_id}/logo/{filename}"

def upload_favicon_path(instance, filename):
    return f"branding/{instance.restaurant_id}/favicon/{filename}"

def upload_beep_path(instance, filename):
    return f"branding/{instance.restaurant_id}/beep/{filename}"

class Config(models.Model):
    restaurant = models.OneToOneField(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="config",
        default=1  # TEMP default for migration
    )
    server_ip = models.CharField(max_length=200, help_text="Domain or public IP for QR links")
    site_name  = models.CharField(max_length=120, default="QR Order")
    logo       = models.ImageField(upload_to=upload_logo_path, blank=True, null=True)
    favicon    = models.ImageField(upload_to=upload_favicon_path, blank=True, null=True)
    beep_audio = models.FileField(upload_to=upload_beep_path, blank=True, null=True)

    class Meta:
        verbose_name = "Configuration"
        verbose_name_plural = "Configuration"

    def __str__(self):
        return f"{self.restaurant.name} — {self.server_ip}"


# -----------------------------
# MENU / CATEGORIES
# -----------------------------
class Category(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="categories",
        default=1  # TEMP default for migration
    )
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("restaurant", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"


class MenuItem(models.Model):
    TYPE_CHOICES = [
        ("VEG", "Veg"),
        ("NONVEG", "Non-Veg"),
        ("OTHER", "Other"),
    ]
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="menu_items",
        default=1  # TEMP default for migration
    )
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="items")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="VEG")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_available = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ("restaurant", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"


# -----------------------------
# TABLES + QR
# -----------------------------
class Table(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="tables",
        default=1  # TEMP default for migration
    )
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20, default="TEMP")
    qr_image = models.ImageField(upload_to="qrcodes/", blank=True, null=True)

    class Meta:
        unique_together = ("restaurant", "code")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"

    def _qr_base_url(self):
        scheme = getattr(settings, "SITE_SCHEME", "http")
        server_ip = getattr(self.restaurant, "config", None).server_ip if hasattr(self.restaurant, "config") else None
        host = server_ip or "localhost"
        if getattr(settings, "DEBUG", False):
            return f"{scheme}://{host}:8000"
        return f"{scheme}://{host}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        base = self._qr_base_url()
        qr_url = f"{base}/menu/?table={self.code}"
        img = qrcode.make(qr_url)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        file_name = f"qr_{self.restaurant_id}_{self.code}.png"
        self.qr_image.save(file_name, File(buffer), save=False)
        super().save(*args, **kwargs)


# -----------------------------
# ORDERS
# -----------------------------
class Order(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("IN_PROGRESS", "In Progress"),
        ("SERVED", "Served"),
        ("PAID", "Paid"),
        ("CANCELLED", "Cancelled"),
    ]
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="orders",
        default=1  # TEMP default for migration
    )
    table = models.ForeignKey(Table, null=True, on_delete=models.SET_NULL, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} - {self.status} ({self.restaurant.name})"

    @property
    def total_amount(self):
        return self.items.aggregate(
            total=Sum(F("qty") * F("item__price"), output_field=DecimalField(max_digits=12, decimal_places=2))
        )["total"] or 0


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    qty = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.item.name} x {self.qty} (Order #{self.order_id})"

    def line_total(self):
        return self.qty * self.item.price
