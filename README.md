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

## Static files (production / PythonAnywhere)

With `DEBUG=false`, CSS and JS are served from the collected bundle via **WhiteNoise**. After pulling code or changing static assets, run:

```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
```

Then reload the web app. Ensure `DJANGO_DEBUG=false` on the server. The `staticfiles/` directory is generated (add it to `.gitignore` if you do not commit it).

### PythonAnywhere checklist

1. Set environment variables: `DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` as needed.
2. Install dependencies and run migrations and `collectstatic` as above.
3. Point the WSGI file at your project’s `config.wsgi` (as in Django’s PA guide).
4. **Reload** the web app.

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
