# OceanRemote Own-Hosting

Self-host your own cold-chain temperature monitoring server on **PythonAnywhere** - free tier works.

The companion **WPF desktop client** (OceanMonitor2) connects to any server built from this repo.

## What you get

- Django backend (Oceamic_app + oceamic_monitor) with REST API
- Login, device management, history charts, alerts, automation rules
- Web dashboard + admin panel
- PWA + Web Push
- Firmware-compatible with ESP8266, ESP32, Pico W
- Setup wizard that generates your .env and WSGI file

## Prerequisites

- A free [PythonAnywhere](https://www.pythonanywhere.com/) account
- A GitHub account (to fork this repo, or just clone it directly)
- Python 3.10+

## 5-minute setup

### 1. On your computer - generate config

    git clone https://github.com/<your-github>/oceanremote-own-hosting.git
    cd oceanremote-own-hosting
    python -m venv .venv
    source .venv/bin/activate    # Windows: .venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python wizard.py

The wizard asks:

- Your PythonAnywhere username
- A repo folder name
- A virtualenv name
- A superuser username + email

It generates:

- `.env` - secrets + allowed hosts
- `deploy/pythonanywhere_wsgi.py` - WSGI to paste into PythonAnywhere
- `deploy/PA_CHECKLIST.md` - step-by-step deploy guide


### 2. On PythonAnywhere - deploy

Follow `deploy/PA_CHECKLIST.md` step by step. Roughly:

1. Open a Bash console
2. `git clone` this repo
3. Create a virtualenv, `pip install -r requirements.txt`
4. `python wizard.py` (same answers as step 1)
5. `python manage.py migrate`
6. `python manage.py createsuperuser`
7. `python manage.py collectstatic --noinput`
8. Create the Web app in the PythonAnywhere dashboard
9. Paste the WSGI file
10. Add static mapping
11. Reload

Full details in `deploy/PA_CHECKLIST.md`.

## Environment variables

See `.env.example`. The important ones:

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated https origins |
| `DEBUG` | False in production |


## Connecting the WPF client

In the desktop client Settings, set Server URL to:

    https://<your-username>.pythonanywhere.com

Log in with your superuser credentials.

## Firmware

Firmware for ESP8266, ESP32, and Pico W is generated from the web dashboard. Flash it, enter your WiFi credentials via the captive portal, and the device registers automatically.

## License

MIT

