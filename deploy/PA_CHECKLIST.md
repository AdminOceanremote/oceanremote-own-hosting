# PythonAnywhere Deployment Checklist

Target: **https://testu.pythonanywhere.com**

## 1. Open a Bash console
https://www.pythonanywhere.com/user/testu/consoles/

## 2. Clone this repo
```
git clone https://github.com/<your-github>/oceanremote-own-hosting.git
cd oceanremote-own-hosting
```

## 3. Virtualenv
```
mkvirtualenv --python=/usr/bin/python3.10 oceanremote-env
pip install -r requirements.txt
```

## 4. Run the wizard on PythonAnywhere
```
python wizard.py
```
This creates `.env` with your secrets. Answer the same questions (same username).

## 5. Migrate
```
python manage.py migrate
```

## 6. Superuser
```
python manage.py createsuperuser
```
Username: `admin`
Email: `mus@hshsh.com`
Password: `En4V2VRN_vJE-ONiNsvBKQ`

## 7. Collect static
```
python manage.py collectstatic --noinput
```

## 8. Web app
https://www.pythonanywhere.com/user/testu/webapps/
- Manual config -> Python 3.10
- Source: `/home/testu/oceanremote-own-hosting`
- Virtualenv: `/home/testu/.virtualenvs/oceanremote-env`

## 9. WSGI file
Open `/var/www/testu_pythonanywhere_com_wsgi.py` and paste the contents of `deploy/pythonanywhere_wsgi.py`. Save.

## 10. Static mapping
- URL: `/static/`
- Dir: `/home/testu/oceanremote-own-hosting/staticfiles`

## 11. Reload & verify
- https://testu.pythonanywhere.com/accounts/login/
- https://testu.pythonanywhere.com/admin/
