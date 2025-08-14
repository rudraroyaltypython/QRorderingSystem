# orders/models.py
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.core.files import File
from django.db.models import Sum, F, DecimalField
from io import BytesIO
import qrcode

# -----------------------------
# TENANT / RESTAURANT
# -----------------------------
class Restaurant(models.Model):
    name = models.CharField(max_length=200)
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="restaurant_owner")
    expiry_date = models.DateField(null=True, blank=True)  # optional; if empty -> no expiry
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# -----------------------------
# SITE / BRAND CONFIG (what your templates use as site_config.*)
# One row per restaurant (use Admin -> add/edit)
# -----------------------------
def upload_logo_path(instance, filename):
    return f"branding/{instance.restaurant_id}/logo/{filename}"

def upload_favicon_path(instance, filename):
    return f"branding/{instance.restaurant_id}/favicon/{filename}"

def upload_beep_path(instance, filename):
    return f"branding/{instance.restaurant_id}/beep/{filename}"

class Config(models.Model):
    restaurant = models.OneToOneField(Restaurant, on_delete=models.CASCADE, related_name="config")

    # used to build QR links (domain or public IP; e.g. mybrand.com)
    server_ip = models.CharField(
        max_length=200,
        help_text="Domain or public IP for QR links (e.g. example.com)."
    )

    # branding used by templates
    site_name  = models.CharField(max_length=120, default="QR Order")
    logo       = models.ImageField(upload_to=upload_logo_path, blank=True, null=True)
    favicon    = models.ImageField(upload_to=upload_favicon_path, blank=True, null=True)

    # optional beep audio playable in templates/JS
    beep_audio = models.FileField(
        upload_to=upload_beep_path, blank=True, null=True,
        help_text="Upload beep.mp3 to play on new orders."
    )

    class Meta:
        verbose_name = "Configuration"
        verbose_name_plural = "Configuration"

    def __str__(self):
        return f"{self.restaurant.name} — {self.server_ip}"


# -----------------------------
# MENU / CATEGORIES
# -----------------------------
class Category(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="categories")
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
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="menu_items")
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
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="tables")
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20, default="TEMP")
    qr_image = models.ImageField(upload_to="qrcodes/", blank=True, null=True)

    class Meta:
        unique_together = ("restaurant", "code")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"

    def _qr_base_url(self) -> str:
        """
        Build the base URL using Config.server_ip.
        Avoid hardcoding ports; add :8000 only if DEBUG and you want local dev behavior.
        """
        # default scheme http; override by settings if provided
        scheme = getattr(settings, "SITE_SCHEME", "http")
        server_ip = getattr(self.restaurant, "config", None).server_ip if hasattr(self.restaurant, "config") else None
        host = server_ip or "localhost"

        # optional: only append :8000 in DEBUG (you can change this to suit)
        if getattr(settings, "DEBUG", False):
            return f"{scheme}://{host}:8000"
        return f"{scheme}://{host}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # ensure we have a pk for image path
        # Generate QR code with the table code
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
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="orders")
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


# -----------------------------
# BILLING (optional)
# -----------------------------
class Bill(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="bills")
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    items = models.TextField(help_text="Store JSON or CSV of items at billing time")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("paid", "Paid")],
        default="pending",
    )

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"Bill for Order #{self.order.id} - {self.customer.username} ({self.restaurant.name})"

    def save(self, *args, **kwargs):
        # if paid, mark order PAID (business rule — adjust if needed)
        super().save(*args, **kwargs)
        if self.status == "paid" and self.order.status != "PAID":
            self.order.status = "PAID"
            self.order.save(update_fields=["status"])
