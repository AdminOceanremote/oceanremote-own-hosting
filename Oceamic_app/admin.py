from django.contrib import admin
from django.utils import timezone
from datetime import timedelta
from django.db import models
from .models import (
    UserActivity,
    Device,
    TemperatureReading,
    HumidityReading,
    TemperatureAlertSetting,
    TemperatureAlert,
    DailyNominalTemperature,
    Notification,
    PushSubscription
)

# --- Admin Classes ---

class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'last_login', 'last_activity', 'page_views', 'is_active')
    list_filter = ('last_activity',)
    search_fields = ('user__username',)
    readonly_fields = ('last_login', 'last_activity', 'page_views')
    ordering = ('-last_activity',)

    def is_active(self, obj):
        # Activity in the last 30 minutes
        return obj.last_activity > timezone.now() - timedelta(minutes=30)
    is_active.boolean = True
    is_active.short_description = 'Status'

class DeviceAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'name', 'nominal_temperature', 'temperature_offset')
    search_fields = ('device_id', 'name')
    list_editable = ('temperature_offset',)  # Edit directly in list view

class TemperatureReadingAdmin(admin.ModelAdmin):
    list_display = ('device', 'temperature', 'timestamp')
    list_filter = ('device', 'timestamp')
    search_fields = ('device__device_id',)

class TemperatureAlertSettingAdmin(admin.ModelAdmin):
    list_display = ('device', 'threshold', 'alert_triggered', 'last_alert_sent', 'alert_frequency')
    list_filter = ('alert_triggered', 'device')
    search_fields = ('device__device_id',)

class TemperatureAlertAdmin(admin.ModelAdmin):
    list_display = ('device', 'temperature', 'threshold', 'timestamp', 'acknowledged', 'acknowledged_by')
    list_filter = ('acknowledged', 'device', 'timestamp')
    search_fields = ('device__device_id', 'notes')
    actions = ['mark_acknowledged']

    def mark_acknowledged(self, request, queryset):
        queryset.update(
            acknowledged=True,
            acknowledged_by=request.user,
            acknowledged_at=timezone.now()
        )
    mark_acknowledged.short_description = "Acknowledge selected alerts"

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'message', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'message')

class DailyNominalTemperatureAdmin(admin.ModelAdmin):
    list_display = ('device', 'date', 'nominal_temperature')
    list_filter = ('device', 'date')

# --- Registration ---

admin.site.register(Device, DeviceAdmin)
admin.site.register(TemperatureReading, TemperatureReadingAdmin)
admin.site.register(HumidityReading, admin.ModelAdmin)
admin.site.register(TemperatureAlertSetting, TemperatureAlertSettingAdmin)
admin.site.register(TemperatureAlert, TemperatureAlertAdmin)
admin.site.register(DailyNominalTemperature, DailyNominalTemperatureAdmin)
admin.site.register(UserActivity, UserActivityAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(PushSubscription, admin.ModelAdmin)

# --- Customization ---

admin.site.site_header = "Oceamic Control Center"
admin.site.site_title = "Oceamic Admin"
admin.site.index_title = "System Telemetry & Notifications"