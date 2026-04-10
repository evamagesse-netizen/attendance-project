import secrets
from io import BytesIO

from django.core.files.base import ContentFile


def generate_unique_barcode():
    """Return a unique numeric barcode string."""
    from .models import Employee

    for _ in range(128):
        candidate = str(secrets.randbelow(10**12)).zfill(12)
        if not Employee.objects.filter(barcode=candidate).exists():
            return candidate
    raise RuntimeError("Could not generate a unique barcode.")


def qr_png_content_file(payload: str, filename: str) -> ContentFile:
    """Build a PNG QR image encoding `payload` (same value scanned at check-in)."""
    import qrcode

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return ContentFile(buf.getvalue(), name=filename)
