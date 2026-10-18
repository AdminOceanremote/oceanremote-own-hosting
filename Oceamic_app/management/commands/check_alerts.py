# oceamic_app/management/commands/check_alerts.py
from django.core.management.base import BaseCommand
from Oceamic_app.views import check_temperature_alerts

class Command(BaseCommand):
    help = 'Check temperature alerts and send notifications'

    def handle(self, *args, **kwargs):
        check_temperature_alerts()
