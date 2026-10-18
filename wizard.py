"""
OceanRemote Own-Hosting Wizard
Full-auto setup for PythonAnywhere.
"""
import os
import secrets
import subprocess
import sys
from pathlib import Path

try:
    import questionary
    from rich.console import Console
    from rich.panel import Panel
except ImportError:
    print("Missing deps. Run: pip install -r requirements.txt")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent
DEPLOY = ROOT / "deploy"
DEPLOY.mkdir(exist_ok=True)
console = Console()


def banner():
    console.print(Panel.fit(
        "[bold cyan]OceanRemote Own-Hosting Wizard[/bold cyan]\n"
        "Full-auto setup for PythonAnywhere.",
        border_style="cyan",
    ))


def detect_username():
    user = os.environ.get("USER") or os.environ.get("USERNAME")
    if user and user.lower() not in ("root", "admin"):
        console.print(f"[green]Detected username:[/green] {user}")
        return user
    return questionary.text(
        "PythonAnywhere username:",
        validate=lambda v: bool(v) or "required",
    ).ask()


def ask_user():
    return {
        "superuser": questionary.text(
            "Superuser username:",
            default="admin",
        ).ask(),
        "email": questionary.text(
            "Superuser email:",
            validate=lambda v: "@" in v or "invalid email",
        ).ask(),
        "password": questionary.password(
            "Superuser password:",
            validate=lambda v: len(v) >= 6 or "min 6 characters",
        ).ask(),
    }
def write_env(username, secret_key):
    host = username + ".pythonanywhere.com"
    origin = "https://" + host
    content = (
        "DEBUG=False\n"
        'DJANGO_SECRET_KEY="' + secret_key + '"\n'
        'DJANGO_ALLOWED_HOSTS="' + host + ',127.0.0.1,localhost"\n'
        'DJANGO_CSRF_TRUSTED_ORIGINS="' + origin + '"\n'
    )
    (ROOT / ".env").write_text(content, encoding="utf-8")
    console.print("[green]Wrote .env[/green]")


def run(cmd, env=None):
    console.print(f"[cyan]$ {' '.join(cmd)}[/cyan]")
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        console.print(f"[red]FAILED ({r.returncode})[/red]")
        console.print(r.stdout)
        console.print(r.stderr)
        sys.exit(1)


def run_migrations():
    run([sys.executable, "manage.py", "migrate", "--noinput"])
    console.print("[green]Migrations applied[/green]")


def run_collectstatic():
    run([sys.executable, "manage.py", "collectstatic", "--noinput"])
    console.print("[green]Static collected[/green]")


def create_superuser(user_data):
    env = os.environ.copy()
    env["DJANGO_SUPERUSER_USERNAME"] = user_data["superuser"]
    env["DJANGO_SUPERUSER_EMAIL"] = user_data["email"]
    env["DJANGO_SUPERUSER_PASSWORD"] = user_data["password"]
    r = subprocess.run(
        [sys.executable, "manage.py", "createsuperuser", "--noinput"],
        env=env, capture_output=True, text=True,
    )
    if r.returncode == 0:
        console.print("[green]Superuser created[/green]")
    elif "already exists" in (r.stderr + r.stdout).lower():
        console.print("[yellow]Superuser already exists, skipped[/yellow]")
    else:
        console.print(f"[red]Superuser creation failed[/red]\n{r.stderr}")
        sys.exit(1)


def build_wsgi(username):
    return (
        "import os\nimport sys\n\n"
        "path = '/home/" + username + "/oceanremote-own-hosting'\n"
        "if path not in sys.path:\n    sys.path.insert(0, path)\n\n"
        "os.environ['DJANGO_SETTINGS_MODULE'] = 'oceamic_monitor.settings'\n\n"
        "activate_env = '/home/" + username + "/.virtualenvs/oceanremote-env/bin/activate_this.py'\n"
        "with open(activate_env) as f:\n    exec(f.read(), dict(__file__=activate_env))\n\n"
        "from django.core.wsgi import get_wsgi_application\napplication = get_wsgi_application()\n"
    )


def write_wsgi(username):
    path = Path(f"/var/www/{username.lower()}_pythonanywhere_com_wsgi.py")
    try:
        path.write_text(build_wsgi(username), encoding="utf-8")
        console.print(f"[green]Wrote {path}[/green]")
    except PermissionError:
        console.print(f"[red]Cannot write {path} - permission denied[/red]")
        sys.exit(1)


def touch_wsgi(username):
    import time
    path = Path(f"/var/www/{username.lower()}_pythonanywhere_com_wsgi.py")
    if not path.exists():
        console.print(f"[yellow]WSGI not found at {path}, skipping touch[/yellow]")
        return
    path.touch()
    time.sleep(2)
    try:
        from pythonanywhere_core.webapp import Webapp
        Webapp(username.lower() + ".pythonanywhere.com").reload()
        console.print("[green]Final reload triggered[/green]")
    except Exception as e:
        console.print(f"[yellow]Final reload skipped: {e}[/yellow]")

def create_or_reload_webapp(username):
    token = os.environ.get("API_TOKEN")
    if not token:
        console.print("[red]API_TOKEN missing.[/red]")
        console.print("Go to PythonAnywhere -> Account -> API Token -> Create a new API token.")
        console.print("Then close this console, open a NEW Bash console, and run bootstrap.sh again.")
        sys.exit(1)

    try:
        from pythonanywhere_core.webapp import Webapp
    except ImportError:
        console.print("[red]pythonanywhere-core not installed.[/red]")
        console.print("Run: pip install pythonanywhere")
        sys.exit(1)

    domain = username + ".pythonanywhere.com"
    console.print(f"[cyan]Creating webapp {domain}...[/cyan]")
    app = Webapp(domain)
    try:
        app.create(
            python_version="3.10",
            virtualenv_path=Path(f"/home/{username}/.virtualenvs/oceanremote-env"),
            project_path=Path(f"/home/{username}/oceanremote-own-hosting"),
            nuke=False,
        )
    except Exception as e:
        msg = str(e)
        if "already exists" in msg.lower() or "409" in msg:
            console.print("[yellow]Webapp already exists, reloading[/yellow]")
        else:
            console.print(f"[red]Webapp create failed: {e}[/red]")
            sys.exit(1)

    console.print("[cyan]Reloading...[/cyan]")
    app.reload()
    console.print("[green]Webapp ready[/green]")


def print_summary(username, user_data):
    url = "https://" + username + ".pythonanywhere.com"
    console.print()
    console.print(Panel.fit(
        "[bold green]Done[/bold green]\n\n"
        "URL:       " + url + "\n"
        "Admin:     " + url + "/admin/\n"
        "Login:     " + url + "/accounts/login/\n"
        "Superuser: " + user_data["superuser"] + "\n"
        "Password:  (the one you typed)",
        border_style="green",
    ))
    console.print()


def main():
    banner()

    username = detect_username()
    user_data = ask_user()

    console.print()
    console.print("[bold]Starting full setup...[/bold]")
    console.print()

    secret_key = secrets.token_urlsafe(50)
    write_env(username, secret_key)
    run_migrations()
    run_collectstatic()
    create_superuser(user_data)
    create_or_reload_webapp(username)
    write_wsgi(username)
    touch_wsgi(username)

    print_summary(username, user_data)


if __name__ == "__main__":
    main()