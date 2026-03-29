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

Open **http://127.0.0.1:8000/** for the scanner and **http://127.0.0.1:8000/dashboard/** for attendance. Use **http://127.0.0.1:8000/admin/** to add employees.

### Employees (barcode + QR image)

When you add an employee, enter **name** and **employee ID** only. Leave **barcode** empty to **auto-generate** a unique code and a **PNG QR image** (same encoding the phone scanner uses). After saving, open the employee again: use **Preview** and **Download PNG** to print or attach to an ID card.

You can still set **barcode** manually when creating a user if you need a specific value; a matching QR image is generated on save.

### QR codes for testing

You can use the **admin-generated QR image**, or any QR whose **payload** equals the employee’s **barcode** string. Scan it on the scanner page.

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

### Media files (QR images in `/media/`)

Uploaded QR images are stored under **`MEDIA_ROOT`** (project `media/` folder). With **`DEBUG=true`**, Django serves `/media/` automatically. With **`DEBUG=false`** (production), configure your host to serve that URL:

- **PythonAnywhere:** Web tab → **Static files** → URL `/media/` → Directory `/home/yourusername/path/to/project/media` (match your `MEDIA_ROOT`).

### PythonAnywhere checklist

1. Set environment variables: `DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` as needed.
2. Install dependencies and run migrations and `collectstatic` as above.
3. Map **`/media/`** to your project’s `media` folder so admin QR downloads and previews work.
4. Point the WSGI file at your project’s `config.wsgi` (as in Django’s PA guide).
5. **Reload** the web app.

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
{ "barcode": "YOUR_BARCODE_STRING", "mode": "check-in" }
```

Use `"mode": "check-in"` to record arrival, or `"mode": "check-out"` to record departure. The server rejects check-in if the employee already checked in (or completed the day), and rejects check-out if there was no check-in or they already checked out.

Include the CSRF token (cookie + `X-CSRFToken` header) as the scanner page does.

Response examples:

- Check-in: `{"status": "success", "action": "check-in", "employee_name": "...", "message": "..."}`
- Check-out: `{"status": "success", "action": "check-out", ...}`
- Error: `{"status": "error", "message": "...", ...}`

## Project layout

- `employees/` — models, views, URLs
- `templates/` — scanner and dashboard
- `static/` — CSS and JavaScript (Html5-QRCode loaded from CDN in the scanner template)
