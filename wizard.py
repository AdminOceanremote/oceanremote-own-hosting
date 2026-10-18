"""OceanRemote Own-Hosting Wizard"""
import re
import secrets
import sys
from pathlib import Path

try:
    import questionary
    from rich.console import Console
    from rich.panel import Panel
except ImportError:
    print("Missing deps. Run: pip install questionary rich")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent
DEPLOY = ROOT / "deploy"
DEPLOY.mkdir(exist_ok=True)
ENV_FILE = ROOT / ".env"
console = Console()


def banner():
    console.print(Panel.fit(
        "[bold cyan]OceanRemote Own-Hosting Wizard[/bold cyan]\n"
        "Set up your own server on PythonAnywhere.",
        border_style="cyan",
    ))


def ask_all():
    a = {}
    a["username"] = questionary.text("PythonAnywhere username:", validate=lambda v: bool(re.match(r"^[a-zA-Z0-9_]{3,}$", v)) or "3+ chars").ask()
    a["repo_name"] = questionary.text("Repo folder name:", default="oceanremote-own-hosting").ask()
    a["venv_name"] = questionary.text("Virtualenv name:", default="oceanremote-env").ask()
    a["superuser"] = questionary.text("Django superuser username:", default="admin").ask()
    a["superuser_email"] = questionary.text("Django superuser email:", validate=lambda v: "@" in v or "invalid").ask()
    if not a.get("username") or not a.get("superuser_email"):
        console.print("[red]Aborted.[/red]")
        sys.exit(1)
    return a

def make_secret_key():
    return secrets.token_urlsafe(50)


def make_superuser_password():
    return secrets.token_urlsafe(16)


def write_env(a, secret_key):
    host = a["username"] + ".pythonanywhere.com"
    origin = "https://" + host
    content = (
        "DEBUG=False\n"
        'DJANGO_SECRET_KEY="' + secret_key + '"\n'
        'DJANGO_ALLOWED_HOSTS="' + host + ',127.0.0.1,localhost"\n'
        'DJANGO_CSRF_TRUSTED_ORIGINS="' + origin + '"\n'
    )
    ENV_FILE.write_text(content, encoding="utf-8")
    return ENV_FILE


def build_wsgi(a):
    return (
        "import os\nimport sys\n\n"
        "project_home = '/home/" + a["username"] + "/" + a["repo_name"] + "'\n"
        "if project_home not in sys.path:\n    sys.path.insert(0, project_home)\n\n"
        "os.environ['DJANGO_SETTINGS_MODULE'] = 'oceamic_monitor.settings'\n\n"
        "activate_env = '/home/" + a["username"] + "/.virtualenvs/" + a["venv_name"] + "/bin/activate_this.py'\n"
        "with open(activate_env) as f:\n    exec(f.read(), dict(__file__=activate_env))\n\n"
        "from django.core.wsgi import get_wsgi_application\napplication = get_wsgi_application()\n"
    )


def write_wsgi(a):
    path = DEPLOY / "pythonanywhere_wsgi.py"
    path.write_text(build_wsgi(a), encoding="utf-8")
    return path

def build_checklist(a, su_password):
    host = a["username"] + ".pythonanywhere.com"
    wsgi_path = "/var/www/" + a["username"] + "_pythonanywhere_com_wsgi.py"
    L = []
    L.append("# PythonAnywhere Deployment Checklist")
    L.append("")
    L.append("Target: **https://" + host + "**")
    L.append("")
    L.append("## 1. Open a Bash console")
    L.append("https://www.pythonanywhere.com/user/" + a["username"] + "/consoles/")
    L.append("")
    L.append("## 2. Clone this repo")
    L.append("```")
    L.append("git clone https://github.com/<your-github>/oceanremote-own-hosting.git")
    L.append("cd " + a["repo_name"])
    L.append("```")
    L.append("")
    L.append("## 3. Virtualenv")
    L.append("```")
    L.append("mkvirtualenv --python=/usr/bin/python3.10 " + a["venv_name"])
    L.append("pip install -r requirements.txt")
    L.append("```")
    L.append("")
    L.append("## 4. Run the wizard on PythonAnywhere")
    L.append("```")
    L.append("python wizard.py")
    L.append("```")
    L.append("This creates `.env` with your secrets. Answer the same questions (same username).")
    L.append("")
    L.append("## 5. Migrate")
    L.append("```")
    L.append("python manage.py migrate")
    L.append("```")
    L.append("")
    L.append("## 6. Superuser")
    L.append("```")
    L.append("python manage.py createsuperuser")
    L.append("```")
    L.append("Username: `" + a["superuser"] + "`")
    L.append("Email: `" + a["superuser_email"] + "`")
    L.append("Password: `" + su_password + "`")
    L.append("")
    L.append("## 7. Collect static")
    L.append("```")
    L.append("python manage.py collectstatic --noinput")
    L.append("```")
    L.append("")
    L.append("## 8. Web app")
    L.append("https://www.pythonanywhere.com/user/" + a["username"] + "/webapps/")
    L.append("- Manual config -> Python 3.10")
    L.append("- Source: `/home/" + a["username"] + "/" + a["repo_name"] + "`")
    L.append("- Virtualenv: `/home/" + a["username"] + "/.virtualenvs/" + a["venv_name"] + "`")
    L.append("")
    L.append("## 9. WSGI file")
    L.append("Open `" + wsgi_path + "` and paste the contents of `deploy/pythonanywhere_wsgi.py`. Save.")
    L.append("")
    L.append("## 10. Static mapping")
    L.append("- URL: `/static/`")
    L.append("- Dir: `/home/" + a["username"] + "/" + a["repo_name"] + "/staticfiles`")
    L.append("")
    L.append("## 11. Reload & verify")
    L.append("- https://" + host + "/accounts/login/")
    L.append("- https://" + host + "/admin/")
    L.append("")
    return "\n".join(L)


def write_checklist(a, su_password):
    path = DEPLOY / "PA_CHECKLIST.md"
    path.write_text(build_checklist(a, su_password), encoding="utf-8")
    return path


def print_summary(a, su_password, env_path, wsgi_path, checklist_path):
    console.print()
    console.print(Panel.fit(
        "[bold green]Done[/bold green]\n\n"
        + str(env_path) + "\n"
        + str(wsgi_path) + "\n"
        + str(checklist_path),
        border_style="green",
    ))
    console.print()
    console.print("[bold yellow]Superuser (save now):[/bold yellow]")
    console.print("  username: [cyan]" + a["superuser"] + "[/cyan]")
    console.print("  email:    [cyan]" + a["superuser_email"] + "[/cyan]")
    console.print("  password: [cyan]" + su_password + "[/cyan]")
    console.print()


def main():
    banner()
    a = ask_all()
    sk = make_secret_key()
    su = make_superuser_password()
    console.print("\n[cyan]Writing .env...[/cyan]")
    env_path = write_env(a, sk)
    console.print("[cyan]Writing WSGI...[/cyan]")
    wsgi_path = write_wsgi(a)
    console.print("[cyan]Writing checklist...[/cyan]")
    checklist_path = write_checklist(a, su)
    print_summary(a, su, env_path, wsgi_path, checklist_path)


if __name__ == "__main__":
    main()
