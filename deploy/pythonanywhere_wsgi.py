import os
import sys

project_home = '/home/testu/oceanremote-own-hosting'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ['DJANGO_SETTINGS_MODULE'] = 'oceamic_monitor.settings'

activate_env = '/home/testu/.virtualenvs/oceanremote-env/bin/activate_this.py'
with open(activate_env) as f:
    exec(f.read(), dict(__file__=activate_env))

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
