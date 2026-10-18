import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from Oceamic_app.models import Device, TemperatureReading

class Command(BaseCommand):
    help = 'Generate custom temperature data for device1 on 12/01/2025'

    def handle(self, *args, **kwargs):
        # Set the device
        device_id = 'device1'
        device, created = Device.objects.get_or_create(device_id=device_id)

        # Set the start date and time
        start_datetime = datetime(2025, 1, 12, 0, 0, 0)

        # Generate temperature data for each 5 minutes
        temperature_readings = []
        current_temp = -24

        for minute in range(0, 24 * 60, 5):  # Every 5 minutes for 24 hours
            timestamp = start_datetime + timedelta(minutes=minute)

            if 0 <= minute < 360:  # 00:00 to 06:00
                current_temp = random.uniform(-24, -20)
            elif 360 <= minute < 420:  # 06:00 to 07:00 (Defrost)
                current_temp = -20 + ((minute - 360) / 60) * (2 + 20)
            elif 420 <= minute < 460:  # 07:00 to 07:40
                current_temp = 2 - ((minute - 420) / 40) * (2 + 24)
            elif 460 <= minute < 840:  # 07:40 to 14:00
                current_temp = random.uniform(-23, -18)
            elif 840 <= minute < 900:  # 14:00 to 15:00 (Defrost)
                current_temp = -23 + ((minute - 840) / 60) * (2 + 23)
            elif 900 <= minute <= 1440:  # 15:00 to 00:00
                current_temp = random.uniform(-24, -18)

            temperature_readings.append(TemperatureReading(
                device=device,
                temperature=current_temp,
                timestamp=timezone.make_aware(timestamp)
            ))

        # Save the temperature readings
        TemperatureReading.objects.bulk_create(temperature_readings)

        self.stdout.write(self.style.SUCCESS('Successfully generated and saved custom temperature data for device1 on 09/01/2025'))
