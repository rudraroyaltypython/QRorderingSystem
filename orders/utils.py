import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings
from .models import Config
import socket


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # This doesn't send data
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def generate_qr_for_table(table_code):
    config = Config.objects.first()
    server_ip = config.server_ip if (config and config.server_ip) else get_local_ip()

    url = f"http://{server_ip}:8000/menu/?table={table_code}"
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format='PNG')
    return ContentFile(buf.getvalue(), name=f"qr_{table_code}.png")
