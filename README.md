# Barcode employee attendance (Django)

Demo system: scan a **QR code** containing the employee’s barcode value with the phone camera. First scan of the day checks in; second scan checks out. Invalid or unknown codes show an error.

## Requirements

- Python 3.10+
- Modern mobile browser (camera needs a **secure context**: **HTTPS** or **http://localhost**)

## Setup

```bash
cd /path/to/attendance
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open **http://127.0.0.1:8000/** for the scanner and **http://127.0.0.1:8000/dashboard/** for attendance. Use **http://127.0.0.1:8000/admin/** to add employees (name, employee ID, unique barcode string).

### QR codes for testing

Generate a QR code whose **payload** is exactly the same string as the employee’s **barcode** field in admin (e.g. `EMP001`). Scan it with the scanner page.

## HTTPS on a phone

Mobile browsers usually block camera access on plain `http://` except for `localhost`. To test on your phone on the same Wi‑Fi:

- Run the dev server bound to all interfaces: `python manage.py runserver 0.0.0.0:8000`
- Serve over HTTPS (e.g. reverse proxy with TLS, or a tunnel tool), **or** use your machine’s hostname/IP only if the browser allows (many phones require HTTPS).

Set `CSRF_TRUSTED_ORIGINS` when using a public origin, for example:

```bash
export DJANGO_CSRF_TRUSTED_ORIGINS="https://your-host.example"
```

## Configuration (optional)

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Secret key in production |
| `DJANGO_DEBUG` | `false` in production |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts |
| `DJANGO_TIME_ZONE` | e.g. `Africa/Nairobi` (late check-in uses 9:00 AM in this zone) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | HTTPS origins for CSRF |

## API

`POST /scan-barcode/` with JSON body:

```json
{ "barcode": "YOUR_BARCODE_STRING" }
```

Include the CSRF token (cookie + `X-CSRFToken` header) as the scanner page does.

Response examples:

- Check-in: `{"status": "success", "action": "check-in", "employee_name": "...", "message": "..."}`
- Check-out: `{"status": "success", "action": "check-out", ...}`
- Error: `{"status": "error", "message": "...", ...}`

## Project layout

- `employees/` — models, views, URLs
- `templates/` — scanner and dashboard
- `static/` — CSS and JavaScript (Html5-QRCode loaded from CDN in the scanner template)
