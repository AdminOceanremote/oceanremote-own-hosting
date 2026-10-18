from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from webpush.models import PushInformation
from webpush.models import Group as WebPushGroup  # Explicit import to avoid conflict


class PushSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    endpoint = models.URLField(max_length=500)
    auth = models.CharField(max_length=100)
    p256dh = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'endpoint']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user.username}'s subscription"


@receiver(post_save, sender=User)
def subscribe_staff_to_alerts(sender, instance, created, **kwargs):
    """Automatically subscribe staff users to webpush alerts group"""
    if instance.is_staff:
        try:
            # Use WebPush's Group model explicitly
            group, _ = WebPushGroup.objects.get_or_create(name="alerts")
            group.users.add(instance)  # WebPush Group uses 'users' relation

            # Ensure a PushInformation record exists
            PushInformation.objects.get_or_create(
                user=instance,
                group=group,
                defaults={'subscription': {}}
            )
        except Exception as e:
            # Log error but don't crash
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error subscribing {instance} to alerts: {str(e)}")


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        ALERT = 'ALERT', 'Temperature Alert'
        WARNING = 'WARN', 'Warning'
        INFO = 'INFO', 'Information'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    alert = models.ForeignKey('TemperatureAlert', on_delete=models.CASCADE, null=True, blank=True)
    device = models.ForeignKey('Device', on_delete=models.CASCADE, null=True, blank=True)
    notification_type = models.CharField(
        max_length=5,
        choices=NotificationType.choices,
        default=NotificationType.ALERT
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['device', 'created_at']),
            models.Index(fields=['notification_type']),
        ]

    def __str__(self):
        return f"{self.get_notification_type_display()} for {self.user.username}"


class UserActivity(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    last_login = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    page_views = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['last_activity']),
        ]

    def __str__(self):
        return f"{self.user.username}'s activity"


class Device(models.Model):
    device_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    nominal_temperature = models.FloatField(null=True, blank=True)
    temperature_offset = models.FloatField(
        default=0.0,
        help_text="Offset applied to incoming readings (e.g., -1 means subtract 1°C)"
    )

    class Meta:
        indexes = [
            models.Index(fields=['device_id']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name

    def get_latest_reading(self):
        """Optimized method to get latest temperature reading"""
        return self.temperaturereading_set.order_by('-timestamp').first()

    def get_latest_humidity(self):
        """Optimized method to get latest humidity reading"""
        return self.humidityreading_set.order_by('-timestamp').first()

    def get_today_average(self):
        """Optimized method to get today's average temperature"""
        today = timezone.now().date()
        result = self.temperaturereading_set.filter(
            timestamp__date=today,
            temperature__isnull=False
        ).aggregate(avg_temp=models.Avg('temperature'))
        return result.get('avg_temp')


class TemperatureReading(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    timestamp = models.DateTimeField()

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', '-timestamp']),
            models.Index(fields=['device', 'timestamp']),
            models.Index(fields=['timestamp']),
            # Remove timestamp__date - not valid for index
        ]

    def __str__(self):
        return f"Device: {self.device.device_id}, Temp: {self.temperature}°C at {self.timestamp}"


class HumidityReading(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    humidity = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', '-timestamp']),
            models.Index(fields=['device', 'timestamp']),
            models.Index(fields=['timestamp']),
            # Remove timestamp__date - not valid for index
        ]

    def __str__(self):
        val = self.humidity if self.humidity is not None else "-"
        return f"{self.device.device_id} | {val}% | {self.timestamp.strftime('%H:%M')}"


class TemperatureAlertSetting(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    threshold = models.FloatField()
    alert_triggered = models.BooleanField(default=False)
    last_alert_sent = models.DateTimeField(null=True, blank=True)
    alert_frequency = models.IntegerField(default=60)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['device']),
            models.Index(fields=['alert_triggered']),
            models.Index(fields=['device', 'alert_triggered']),
        ]

    def __str__(self):
        return f"{self.device.device_id} - {self.threshold}°C - Triggered: {self.alert_triggered}"


class TemperatureAlert(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    temperature = models.DecimalField(max_digits=5, decimal_places=2)
    threshold = models.FloatField()
    timestamp = models.DateTimeField(default=timezone.now)
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', '-timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['device', 'acknowledged']),
        ]

    def __str__(self):
        return f"Device: {self.device.device_id}, Temp: {self.temperature}°C, Threshold: {self.threshold}°C, at {self.timestamp}"


class DailyNominalTemperature(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    date = models.DateField()
    nominal_temperature = models.FloatField()

    class Meta:
        unique_together = ('device', 'date')
        indexes = [
            models.Index(fields=['device', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['device']),
        ]

    def calculate_nominal_temperature(self):
        """Optimized using database aggregation"""
        result = TemperatureReading.objects.filter(
            device=self.device,
            timestamp__date=self.date,
            temperature__isnull=False
        ).aggregate(avg_temp=models.Avg('temperature'))

        avg_val = result.get('avg_temp')
        self.nominal_temperature = float(avg_val) if avg_val is not None else 0.0

    def save(self, *args, **kwargs):
        self.calculate_nominal_temperature()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.device.device_id} - {self.date} - {self.nominal_temperature}°C"


# ============================================================================
# HELPER FUNCTIONS FOR OPTIMIZED QUERIES
# ============================================================================

def get_device_with_latest_readings(device_id):
    """
    Optimized helper to get device with latest readings in one query
    Use this in views instead of multiple queries
    """
    try:
        device = Device.objects.prefetch_related(
            models.Prefetch(
                'temperaturereading_set',
                queryset=TemperatureReading.objects.order_by('-timestamp')[:1],
                to_attr='latest_temp'
            ),
            models.Prefetch(
                'humidityreading_set',
                queryset=HumidityReading.objects.order_by('-timestamp')[:1],
                to_attr='latest_hum'
            )
        ).get(device_id=device_id)
        return device
    except Device.DoesNotExist:
        return None


def get_all_devices_with_latest_readings():
    """
    Optimized helper to get all devices with latest readings
    Uses prefetch_related to minimize database queries
    """
    devices = Device.objects.prefetch_related(
        models.Prefetch(
            'temperaturereading_set',
            queryset=TemperatureReading.objects.order_by('-timestamp')[:1],
            to_attr='latest_temp'
        ),
        models.Prefetch(
            'humidityreading_set',
            queryset=HumidityReading.objects.order_by('-timestamp')[:1],
            to_attr='latest_hum'
        )
    ).all()
    return devices


# ============================================================================
# SIGNALS FOR PERFORMANCE - UPDATE CACHE ON SAVE
# ============================================================================

@receiver(post_save, sender=TemperatureReading)
def clear_temperature_cache(sender, instance, **kwargs):
    """Clear relevant caches when new temperature is saved"""
    try:
        from django.core.cache import cache
        # Clear home page cache
        cache.delete('home_page_data')
        # Clear device-specific cache
        cache.delete(f'device_data_{instance.device.device_id}')
        # Clear API cache
        cache.delete('api_latest_data')
    except Exception:
        pass  # Cache might not be available


@receiver(post_save, sender=HumidityReading)
def clear_humidity_cache(sender, instance, **kwargs):
    """Clear relevant caches when new humidity is saved"""
    try:
        from django.core.cache import cache
        cache.delete('home_page_data')
        cache.delete(f'device_humidity_{instance.device.device_id}')
    except Exception:
        pass


# ============================================================================
# DATABASE FUNCTIONS FOR PERFORMANCE
# ============================================================================

def batch_get_temperature_stats(device_ids, start_date=None, end_date=None):
    """
    Get temperature stats for multiple devices in a single query
    """
    from django.db.models import Avg, Max, Min, Count
    
    if start_date is None:
        start_date = timezone.now().date()
    if end_date is None:
        end_date = timezone.now().date()

    result = TemperatureReading.objects.filter(
        device__device_id__in=device_ids,
        timestamp__date__range=[start_date, end_date],
        temperature__isnull=False
    ).values('device__device_id').annotate(
        avg_temp=Avg('temperature'),
        max_temp=Max('temperature'),
        min_temp=Min('temperature'),
        count=Count('temperature')
    )

    return {item['device__device_id']: item for item in result}


def get_latest_readings_batch(device_ids):
    """
    Get latest readings for multiple devices in a single query
    """
    from django.db.models import OuterRef, Subquery
    
    latest_temps = TemperatureReading.objects.filter(
        device=OuterRef('pk')
    ).order_by('-timestamp')

    latest_hums = HumidityReading.objects.filter(
        device=OuterRef('pk')
    ).order_by('-timestamp')

    devices = Device.objects.filter(device_id__in=device_ids).annotate(
        latest_temp=Subquery(latest_temps.values('temperature')[:1]),
        latest_temp_time=Subquery(latest_temps.values('timestamp')[:1]),
        latest_hum=Subquery(latest_hums.values('humidity')[:1]),
        latest_hum_time=Subquery(latest_hums.values('timestamp')[:1])
    )

    return devices