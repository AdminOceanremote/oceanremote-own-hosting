from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    # --- 1. SERVICE WORKER & PWA (THE PRIORITY) ---
    # These paths force the browser to use your custom sw-v4.js logic
    path('service-worker.js', views.service_worker, name='service-worker.js'),
    path('sw.js', views.service_worker),

    path('manifest.json', TemplateView.as_view(
        template_name="manifest.json",
        content_type='application/json'
    ), name='manifest.json'),

    # 🚨 DISABLED TO PREVENT INTERFERENCE WITH THE FALLBACK LOGIC
    # path('', include('pwa.urls')),

    path('firebase-messaging-sw.js', views.firebase_service_worker, name='firebase_service_worker'),

    # --- 2. AUTHENTICATION ---
    path('login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='/login/'), name='logout'),

    # --- 3. MAIN SITE VIEWS ---
    path('', views.home, name='home'),
    path('home2/', views.home2, name='home2'),
    path('choice/', views.choice, name='choice'),
    path('access_denied/', views.access_denied, name='access_denied'),

    # --- 4. CRONS & BACKGROUND TASKS ---
    path('cron/daily-reset/', views.daily_cron_reset, name='daily_cron_reset'),
    path('cron/virtual-humidity/', views.virtual_humidity_cron, name='virtual_humidity'),

    # --- 5. DEVICE MANAGEMENT ---
    path('add_device/', views.add_device, name='add_device'),
    path('delete_device/', views.delete_device, name='delete_device'),


    path('api/public/latest-temperatures/', views.public_api_latest, name='public_api_latest'),
    path('api/get_latest_readings/', views.get_latest_readings, name='latest_readings_api'),

    # --- 6. DATA UPDATES ---
    path('update_temperature/', views.update_temperature, name='update_temperature'),
    path('update_humidity/', views.update_humidity, name='update_humidity'),
    path('update_nominal_temperatures/', views.update_nominal_temperatures, name='update_nominal_temperatures'),
    path('special_character/', views.special_character, name='special_character'),

    # --- 7. ALERT SYSTEM ---
    path('trigger_check/', views.trigger_check, name='trigger_check'),
    path('manage_alerts/<str:device_id>/', views.manage_alerts, name='manage_alerts'),
    path('set_alert/', views.set_alert, name='set_alert'),
    path('delete_alert/<str:device_id>/', views.delete_alert, name='delete_alert'),
    path('toggle_alert/<str:device_id>/', views.toggle_alert, name='toggle_alert'),
    path('alerts_declarations/<str:device_id>/', views.alerts_declarations, name='alerts_declarations'),

    # --- 8. CHARTG & TEMPERATURE ANALYSIS ---
    path('device/<str:device_id>/chart/', views.device_chart, name='device_chart'),
    path('device/<str:device_id>/list/', views.device_list, name='device_list'),
    path('device/<str:device_id>/analysis/', views.device_analysis, name='device_analysis'),
    path('bar_chart/<str:device_id>/', views.bar_chart_view, name='bar_chart_view'),
    path('g_chart/<str:device_id>/', views.g_chart, name='g_chart'),
    path('temperature_by_date/', views.temperature_by_date, name='temperature_by_date'),
    path('detailed-status/', views.detailed_status, name='detailed_status'),

    # --- 9. MULTI-DATE CHARTS ---
    path('device/<str:device_id>/multi_chart/', views.multi_device_chart, name='multi_device_chart'),
    path('new_multi_chart/<str:device_id>/', views.new_multi_device_chart, name='new_multi_device_chart'),
    path('multi_g_chart/<str:device_id>/', views.multi_g_chart, name='multi_g_chart'),

    # --- 10. HUMIDITY VIEWS ---
    path('humidity_list/<str:device_id>/', views.humidity_list, name='humidity_list'),
    path('humidity_chart/<str:device_id>/', views.humidity_chart, name='humidity_chart'),
    path('multi_humidity_chart/<str:device_id>/', views.multi_humidity_chart, name='multi_humidity_chart'),
    path('humidity_bar_chart/<str:device_id>/', views.humidity_bar_chart, name='humidity_bar_chart'),
    path('multi_humidity_bar_chart/<str:device_id>/', views.multi_humidity_bar_chart, name='multi_humidity_bar_chart'),
    path('humidity_google_chart/<str:device_id>/', views.humidity_google_chart, name='humidity_google_chart'),

    # --- 11. NOMINAL TEMPERATURE ---
    path('nominal_chart/', views.nominal_chart, name='nominal_chart'),
    path('nominal_chart/<str:device_id>/', views.nominal_chart, name='nominal_chart_device'),
    path('get_nominal_temperatures/<str:device_id>/', views.get_nominal_temperatures, name='get_nominal_temperatures'),

    # --- 12. NOTIFICATION SYSTEM ---
    path('notifications/get/', views.get_notifications, name='get_notifications'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('notifications/all/', views.notifications_all, name='notifications_all'),
    path('notifications/get_unread/', views.get_unread_notifications, name='get_unread_notifications'),
    path('notifications/<int:pk>/', views.notification_detail, name='notification_detail'),

    path('get-latest-notifications/', views.get_latest_notifications, name='get_latest_notifications'),

    # Add this to your urlpatterns in urls.py
    path('run_maintenance/', views.clean_and_thin_database, name='run_maintenance'),


    # --- 13. WEBPUSH SYSTEM ---
    path('save_subscription/', views.save_subscription, name='save_subscription'),
    path('webpush/', include('webpush.urls')),
]