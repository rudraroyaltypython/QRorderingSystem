from django.shortcuts import redirect
from django.utils import timezone
from .models import Restaurant

class LicenseCheckMiddleware:
    """
    Blocks access to restaurant features if license/expiry is over.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and hasattr(user, "restaurant_owner"):
            restaurant = user.restaurant_owner
            if restaurant.expiry_date and restaurant.expiry_date < timezone.now().date():
                return redirect("/license-expired/")  # You can make a template for this
        return self.get_response(request)
