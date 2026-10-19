from django.urls import reverse
# from webpush import send_user_notification  # Commented out: Missing Module
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.conf import settings
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.gzip import gzip_page
import os
import json
import logging
from datetime import date, datetime, timedelta
from django.utils import timezone
from django.utils.dateparse import parse_date


# Local App Imports
from .models import Device, TemperatureReading, HumidityReading, TemperatureAlertSetting, Notification, TemperatureAlert

# Set up the logger
logger = logging.getLogger(__name__)

# --- Twilio Section Commented Out ---
# from twilio.rest import Client
# from twilio.base.exceptions import TwilioRestException
# twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def send_alert(device_id, current_temp, threshold, alert_setting):
    """
    Twilio functionality disabled to prevent server crash.
    Logs the alert to the console instead.
    """
    room_names = {
        'device1': 'Chambre négative-1 unité-2',
        'device2': 'Chambre positive unité-2',
        'device3': 'Chambre des ingrédients unité-2',
        'device4': 'Chambre positive unité-1',
        'device5': 'Chambre négative-2 unité-2',
        'device6': 'Chambre des ingrédients unité-1'
    }
    room_name = room_names.get(device_id, f'Device {device_id}')
    message_content = f"ALERT (Simulated): {room_name} temp is {current_temp}°C (Threshold: {threshold}°C)"
    print(f"[DEBUG] {message_content}")

    # Save the time but don't try to send WhatsApp
    alert_setting.last_alert_sent = timezone.now()
    alert_setting.save()

def notification_detail(request, pk):
    notification = get_object_or_404(Notification, pk=pk)
    if not notification.is_read:
        notification.is_read = True
        notification.save()
    return render(request, 'Oceamic_app/notification_detail.html', {'notification': notification})

@login_required
def webpush_subscribe(request):
    # This requires 'webpush' in INSTALLED_APPS and settings. Use with caution.
    try:
        context = {'vapid_public_key': settings.WEBPUSH_SETTINGS['VAPID_PUBLIC_KEY']}
        return render(request, 'webpush/subscribe.html', context)
    except Exception as e:
        return HttpResponse("Webpush configuration missing or disabled.")

@login_required
def multi_g_chart(request, device_id):
    device = get_object_or_404(Device, device_id=device_id)
    selected_dates = request.GET.get('dates', '').split(',')

    all_readings = []
    for selected_date in selected_dates:
        try:
            if not selected_date.strip(): continue
            start_date = timezone.make_aware(datetime.strptime(selected_date.strip(), '%Y-%m-%d'))
            end_date = start_date + timedelta(days=1)
            readings = TemperatureReading.objects.filter(device=device, timestamp__range=(start_date, end_date)).order_by('timestamp')

            timestamps = [reading.timestamp.isoformat() for reading in readings if reading.temperature is not None]
            temperatures = [float(reading.temperature) for reading in readings if reading.temperature is not None]

            all_readings.append({
                'date': selected_date.strip(),
                'timestamps': timestamps,
                'temperatures': temperatures,
            })
        except ValueError:
            pass

    return render(request, 'Oceamic_app/multi_g_chart.html', {
        'device_id': device_id,
        'selected_dates': ', '.join(selected_dates),
        'all_readings': json.dumps(all_readings),
    })





@require_GET
@gzip_page
def firebase_service_worker(request):
    fcm_path = os.path.join(settings.BASE_DIR, 'static', 'firebase-messaging-sw.js')
    try:
        with open(fcm_path, 'r') as f:
            content = f.read()
        return HttpResponse(content, content_type='application/javascript')
    except FileNotFoundError:
        return HttpResponse("// firebase-sw not found", content_type='application/javascript')

# from webpush.models import SubscriptionInfo, Group as WebPushGroup # Commented out


# views.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from webpush import send_user_notification
from .models import PushSubscription

@require_POST
def save_subscription(request):
    try:
        data = json.loads(request.body)
        subscription = PushSubscription.objects.create(
            user=request.user,
            endpoint=data['endpoint'],
            auth=data['keys']['auth'],
            p256dh=data['keys']['p256dh']
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_POST
def delete_subscription(request):
    try:
        data = json.loads(request.body)
        PushSubscription.objects.filter(
            user=request.user,
            endpoint=data['endpoint']
        ).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

def send_notification(user, title, body, url=None):
    payload = {
        'title': title,
        'body': body
    }
    if url:
        payload['url'] = url

    send_user_notification(
        user=user,
        payload=payload,
        ttl=1000
    )





def check_temperature_alerts():
    current_time = timezone.now()
    alert_settings = TemperatureAlertSetting.objects.all()
    for alert_setting in alert_settings:
        device = alert_setting.device
        latest_temperature_reading = TemperatureReading.objects.filter(device=device).last()

        if not latest_temperature_reading or latest_temperature_reading.temperature is None:
            continue

        if latest_temperature_reading.temperature >= alert_setting.threshold:
            should_send = False

            # Logic to prevent NoneType subtraction error
            if not alert_setting.alert_triggered:
                should_send = True
            elif alert_setting.last_alert_sent is None:
                should_send = True
            elif (current_time - alert_setting.last_alert_sent) >= timedelta(minutes=alert_setting.alert_frequency):
                should_send = True

            if should_send:
                send_alert(device.device_id, latest_temperature_reading.temperature, alert_setting.threshold, alert_setting)
                alert_setting.alert_triggered = True
                # Record the alert in history
                TemperatureAlert.objects.create(
                    device=device,
                    temperature=latest_temperature_reading.temperature,
                    threshold=alert_setting.threshold,
                    timestamp=current_time
                )
        else:
            alert_setting.alert_triggered = False

        alert_setting.save()



def alerts_declarations(request, device_id):
    date_filter = request.GET.get('date', timezone.now().date().isoformat())
    selected_date = timezone.make_aware(timezone.datetime.strptime(date_filter, '%Y-%m-%d'))
    start_time = selected_date
    end_time = selected_date + timedelta(days=1)

    device = get_object_or_404(Device, device_id=device_id)

    if request.method == 'POST':
        for alert in TemperatureAlert.objects.filter(device=device, timestamp__range=(start_time, end_time)):
            note_key = f'note_{alert.id}'
            delete_key = f'delete_note_{alert.id}'
            if note_key in request.POST:
                alert.notes = request.POST[note_key]
                alert.save()
            elif delete_key in request.POST:
                alert.notes = None
                alert.save()

    alerts = TemperatureAlert.objects.filter(device=device, timestamp__range=(start_time, end_time))
    readings = TemperatureReading.objects.filter(
        device=device,
        timestamp__range=(start_time, end_time)
    )
    valid_readings = [r.temperature for r in readings if r.temperature is not None]

    nominal_temperature = None
    if valid_readings:
        total_temperature = sum(valid_readings)
        average_temperature = total_temperature / len(valid_readings)
        nominal_temperature = round(average_temperature, 2)

    return render(request, 'Oceamic_app/alerts_declarations.html', {
        'alerts': alerts,
        'date_filter': date_filter,
        'nominal_temperature': nominal_temperature,
        'device': device
    })



def access_denied(request):
    return render(request, 'Oceamic_app/access_denied.html')

@csrf_exempt
def delete_alert(request, device_id):
    if request.method == "POST":
        try:
            device = Device.objects.get(device_id=device_id)
            TemperatureAlertSetting.objects.filter(device=device).delete()
            return redirect('manage_alerts', device_id=device_id)
        except Device.DoesNotExist:
            return JsonResponse({"error": "Device does not exist"}, status=404)

@csrf_exempt
def set_alert(request):
    if request.method == "POST":
        device_id = request.POST['device_id']
        threshold = float(request.POST['threshold'])
        alert_frequency = int(request.POST['alert_frequency'])
        device = Device.objects.get(device_id=device_id)

        alert_setting, created = TemperatureAlertSetting.objects.update_or_create(
            device=device,
            defaults={'threshold': threshold, 'alert_frequency': alert_frequency}
        )
        return redirect('manage_alerts', device_id=device_id)

@csrf_exempt
def toggle_alert(request, device_id):
    if request.method == "POST":
        device = Device.objects.get(device_id=device_id)
        alert_setting = TemperatureAlertSetting.objects.filter(device=device).last()
        if alert_setting:
            alert_status = request.POST.get('alert_status') == 'on'
            alert_setting.alert_triggered = alert_status
            alert_setting.save()
        return redirect('manage_alerts', device_id=device_id)



@login_required
def get_unread_notifications(request):
    notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:5]

    return JsonResponse({
        'unread_count': notifications.count(),
        'notifications': [
            {
                'message': n.message,
                'created_at': n.created_at.isoformat()
            } for n in notifications
        ]
    })







def is_staff(user):
    return user.is_staff


def staff_required(view_func):
    decorated_view_func = user_passes_test(
        lambda user: user.is_staff,
        login_url='access_denied'
    )(view_func)
    return decorated_view_func





import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required # Built-in Django fix
from .models import Device, TemperatureReading, TemperatureAlertSetting, TemperatureAlert

@staff_member_required  # Changed from staff_required
def manage_alerts(request, device_id=None):
    # Only fetch the 6 primary devices
    target_ids = ['device1', 'device2', 'device3', 'device4', 'device5', 'device6']
    devices = Device.objects.filter(device_id__in=target_ids)

    for device in devices:
        device.temperature = TemperatureReading.objects.filter(device=device).last()
        device.threshold = TemperatureAlertSetting.objects.filter(device=device).last()

        # Alert Creation Logic
        if device.temperature and device.threshold:
            current_temp = device.temperature.temperature
            limit = device.threshold.threshold

            if current_temp is not None and limit is not None:
                if current_temp > limit:
                    exists = TemperatureAlert.objects.filter(
                        device=device,
                        timestamp=device.temperature.timestamp
                    ).exists()

                    if not exists:
                        TemperatureAlert.objects.create(
                            device=device,
                            temperature=current_temp,
                            threshold=limit,
                            timestamp=device.temperature.timestamp,
                            notes=device.threshold.notes
                        )

    return render(request, 'Oceamic_app/manage_alerts.html', {
        'devices': devices,
        'current_device_id': device_id
    })




def get_nominal_temperatures(request, device_id=None):
    try:
        now = timezone.now()
        start_date = datetime(now.year, 1, 1)
        end_date = datetime(now.year, 12, 31)

        labels = []
        nominal_temperatures = []

        for single_date in daterange(start_date, end_date):
            labels.append(single_date.strftime("%Y-%m-%d"))

            readings = TemperatureReading.objects.filter(
                timestamp__date=single_date,
                device__device_id=device_id
            )

            valid_readings = [r.temperature for r in readings if r.temperature is not None]
            if valid_readings:
                total_temperature = sum(valid_readings)
                average_temperature = total_temperature / len(valid_readings)
                formatted_temp = round(average_temperature, 2)
            else:
                formatted_temp = None

            nominal_temperatures.append(formatted_temp)

        return JsonResponse({'labels': labels, 'nominal_temperatures': nominal_temperatures})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)


def nominal_chart(request, device_id=None):
    device = Device.objects.filter(device_id=device_id).first()
    return render(request, 'Oceamic_app/nominal_chart.html', {'device': device})















def temperature_by_date(request):
    if request.method == 'POST':
        selected_date = request.POST.get('date')
        devices = Device.objects.all()
        nominal_temperatures = {}

        for device in devices:
            # Parse selected date
            selected_datetime = timezone.make_aware(timezone.datetime.strptime(selected_date, '%Y-%m-%d'))
            start_time = selected_datetime
            end_time = selected_datetime + timedelta(days=1)

            # Fetch temperature readings for the selected date
            readings = TemperatureReading.objects.filter(
                device=device,
                timestamp__range=(start_time, end_time)
            )

            # Calculate the average temperature, skipping any None values
            valid_readings = [r.temperature for r in readings if r.temperature is not None]
            if valid_readings:
                total_temperature = sum(valid_readings)
                average_temperature = total_temperature / len(valid_readings)
                formatted_temp = round(average_temperature, 2)
                nominal_temperatures[device.name] = formatted_temp

        return render(request, 'temperature_by_date.html', {'nominal_temperatures': nominal_temperatures})

    return render(request, 'temperature_by_date.html')


@csrf_exempt
def update_temperature(request):
    if request.method == 'POST':
        device_id = request.POST.get('device_id')
        temperature = request.POST.get('temperature')

        # Check if the temperature is a valid number
        try:
            temperature = float(temperature)
            if temperature != temperature:  # Check for nan
                temperature = None  # Set temperature to None for nan values
        except ValueError:
            temperature = None  # Set temperature to None for invalid values

        device, created = Device.objects.get_or_create(device_id=device_id)

        # APPLY OFFSET HERE - THIS IS THE KEY CHANGE
        if temperature is not None and device.temperature_offset != 0:
            original_temp = temperature
            temperature = temperature + device.temperature_offset  # Apply offset
            logging.debug(f"Calibrated {device_id}: {original_temp}°C -> {temperature}°C (offset: {device.temperature_offset})")

        reading = TemperatureReading(device=device, temperature=temperature, timestamp=timezone.now())
        reading.save()

        logging.debug(f"Saved temperature: {temperature} for device: {device_id}")
        return JsonResponse({"status": "success"})

    logging.error("Invalid request method or missing parameters")
    return JsonResponse({"status": "failed", "error": "Invalid request method or missing parameters"})


from django.http import JsonResponse
from .models import Device, TemperatureReading
from django.utils import timezone

def daily_cron_reset(request):
    # Security: You can add a simple token check if you want
    # if request.GET.get('token') != 'my_secret_123':
    #    return JsonResponse({"status": "unauthorized"}, status=403)

    devices = Device.objects.all()
    count = 0

    for device in devices:
        # We create a reading with None to represent the "dash" or reset state
        TemperatureReading.objects.create(
            device=device,
            temperature=None, # This renders as a blank/dash in most tables
            timestamp=timezone.now()
        )
        count += 1

    return JsonResponse({
        "status": "success",
        "message": f"Daily reset complete for {count} devices",
        "timestamp": str(timezone.now())
    })




from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Avg, Min, Max
from django.core.cache import cache
import json
import logging
from .models import Device, TemperatureReading

logger = logging.getLogger(__name__)

@login_required
def multi_device_chart(request, device_id):
    """
    Optimized view for displaying multiple days of temperature data
    with 5-minute resampling for cleaner charts.
    Shows most recent date first (reverse chronological).
    """
    device_obj = get_object_or_404(Device, device_id=device_id)
    device_name = getattr(device_obj, 'name', device_id)

    # Get today's date
    today = timezone.now().date()

    # Default: 30 days ago to today (30 days total)
    default_start = (today - timedelta(days=29)).isoformat()
    default_end = today.isoformat()

    # Get dates from request or use defaults
    start_str = request.GET.get('start', default_start)
    end_str = request.GET.get('end', default_end)

    # Try to get from cache first (5 second cache for fast loading)
    cache_key = f'multi_chart_{device_id}_{start_str}_{end_str}'
    charts_list = cache.get(cache_key)

    if charts_list is None:
        charts_list = []

        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()

            # Ensure end_date is not in the future
            if end_date > today:
                end_date = today
                end_str = today.isoformat()

            # Validate date range (max 90 days for performance)
            max_days = 90
            if (end_date - start_date).days > max_days:
                start_date = end_date - timedelta(days=max_days)
                start_str = start_date.isoformat()

            # Optimized: Get ALL readings for the entire date range in ONE query
            all_readings = TemperatureReading.objects.filter(
                device=device_obj,
                timestamp__date__range=[start_date, end_date],
                temperature__isnull=False
            ).order_by('timestamp').values('timestamp', 'temperature')

            # Convert to list for faster iteration
            readings_list = list(all_readings)

            # Use dictionary to group by date for faster processing
            readings_by_date = {}
            for reading in readings_list:
                reading_date = reading['timestamp'].date()
                if reading_date not in readings_by_date:
                    readings_by_date[reading_date] = []
                readings_by_date[reading_date].append(reading)

            current_day = start_date
            while current_day <= end_date:
                day_readings = readings_by_date.get(current_day, [])

                # 5-minute resampling logic
                resampled_labels = []
                resampled_values = []
                last_time = None

                for r in day_readings:
                    temp = float(r['temperature'])
                    # Check if 300 seconds (5 mins) have passed
                    if last_time is None or (r['timestamp'] - last_time).total_seconds() >= 300:
                        resampled_labels.append(r['timestamp'].strftime('%H:%M'))
                        resampled_values.append(temp)
                        last_time = r['timestamp']

                # Calculate stats from resampled data
                has_data = len(resampled_values) > 0
                if has_data:
                    min_val = round(min(resampled_values), 1)
                    max_val = round(max(resampled_values), 1)
                    avg_val = round(sum(resampled_values) / len(resampled_values), 1)
                else:
                    min_val = max_val = avg_val = "--"

                charts_list.append({
                    'date_title': current_day.strftime('%A, %d %B %Y'),
                    'labels_json': json.dumps(resampled_labels),
                    'values_json': json.dumps(resampled_values),
                    'has_data': has_data,
                    'min': min_val,
                    'max': max_val,
                    'avg': avg_val
                })
                current_day += timedelta(days=1)

            # Reverse the list to show most recent first
            charts_list.reverse()

            # Cache for 5 seconds (since data updates frequently)
            cache.set(cache_key, charts_list, 5)

        except Exception as e:
            logger.error(f"Error in multi_device_chart: {str(e)}")
            # Return empty data instead of crashing
            charts_list = []

    return render(request, 'Oceamic_app/chart_print-device-id.html', {
        'device_id': device_id,
        'device_name': device_name,
        'start_date': start_str,
        'end_date': end_str,
        'charts_list': charts_list,
    })

from django.http import JsonResponse
from .models import Device, TemperatureReading

def get_latest_readings(request):
    devices = Device.objects.all()
    data = []
    for d in devices:
        last_reading = TemperatureReading.objects.filter(device=d).order_by('-timestamp').first()
        data.append({
            'id': d.device_id,
            'temp': float(last_reading.temperature) if last_reading else None
        })
    return JsonResponse({'devices': data})




@csrf_exempt
def update_humidity(request):
    if request.method == 'POST':
        device_id = request.POST.get('device_id')
        humidity = request.POST.get('humidity')

        logger.debug(f"Received POST request with device_id: {device_id}, humidity: {humidity}")

        if device_id and humidity is not None:
            try:
                if humidity.lower() == 'nan':
                    humidity = float('nan')
                else:
                    humidity = float(humidity)
                logger.debug(f"Parsed humidity: {humidity}")
            except ValueError:
                logger.error("Invalid humidity value")
                return JsonResponse({"status": "failed", "error": "Invalid humidity value"})

            device, created = Device.objects.get_or_create(device_id=device_id)
            logger.debug(f"Device {'created' if created else 'retrieved'}: {device.device_id}")

            try:
                reading = HumidityReading(device=device, humidity=humidity, timestamp=timezone.now())
                reading.save()
                logger.debug("Humidity reading saved successfully")
                return JsonResponse({"status": "success"})
            except Exception as e:
                logger.error(f"Failed to save humidity reading: {e}")
                return JsonResponse({"status": "failed", "error": "Failed to save humidity reading"})
        else:
            logger.error("Missing device_id or humidity")
            return JsonResponse({"status": "failed", "error": "Missing device_id or humidity"})

    logger.error("Invalid request method")
    return JsonResponse({"status": "failed", "error": "Invalid request method"})







@login_required
def humidity_list(request, device_id=None):
    date = request.GET.get('date')
    if not date:
        date = timezone.now().date().isoformat()  # Set the default date to the current date as a string

    readings = HumidityReading.objects.all()

    if device_id:
        readings = readings.filter(device__device_id=device_id)

    parsed_date = parse_date(date)
    if parsed_date:
        readings = readings.filter(timestamp__date=parsed_date)

    readings = readings.order_by('-timestamp')
    return render(request, 'Oceamic_app/humidity_list.html', {
        'readings': readings,
        'device_id': device_id,
        'current_date': date
    })




@csrf_exempt
def update_nominal_temperatures(request):
    """Optional: Can be called daily to store nominal temps"""
    today = timezone.now().date()
    devices = Device.objects.all()

    for device in devices:
        daily_readings = TemperatureReading.objects.filter(
            device=device,
            timestamp__date=today,
            temperature__isnull=False
        )

        if daily_readings.exists():
            avg_temp = sum(r.temperature for r in daily_readings) / daily_readings.count()
            device.nominal_temperature = round(avg_temp, 2)  # Still stores in model
            device.save()

    return JsonResponse({'status': 'success', 'updated': timezone.now().isoformat()})





import random

def virtual_humidity_cron(request):
    devices = Device.objects.all()
    created_count = 0

    for device in devices:
        # 1. Look for the absolute last temperature record
        last_t = TemperatureReading.objects.filter(device=device).order_by('-timestamp').first()

        # Default value is None (which shows as '-' in Admin)
        calculated_hum = None

        # 2. Rule: Only calculate a number if the temp exists and isn't '-'
        if last_t and last_t.temperature is not None:
            t = float(last_t.temperature)

            # Realistic Industrial Logic
            if t <= -18:
                calculated_hum = round(random.uniform(70.0, 80.0), 1)
            elif t <= 5:
                calculated_hum = round(random.uniform(90.0, 95.5), 1)
            else:
                calculated_hum = round(random.uniform(55.0, 65.0), 1)

        # 3. FORCE CREATE: This adds a new row to the database every time
        HumidityReading.objects.create(
            device=device,
            humidity=calculated_hum,
            timestamp=timezone.now() # Marks it with the current time
        )
        created_count += 1

    return JsonResponse({
        "status": "Success",
        "new_records_created": created_count,
        "time": timezone.now().strftime('%H:%M:%S')
    })

















from django.db.models import Prefetch, Avg

@login_required
def home2(request):
    today = timezone.now().date()

    # 1. High-Performance Prefetch (Fixes the PythonAnywhere DB lag)
    # This fetches all readings for all devices in just 2 queries total
    temp_prefetch = Prefetch(
        'temperaturereading_set',
        queryset=TemperatureReading.objects.order_by('-timestamp'),
        to_attr='all_temps'
    )
    hum_prefetch = Prefetch(
        'humidityreading_set',
        queryset=HumidityReading.objects.order_by('-timestamp'),
        to_attr='all_hums'
    )

    # 2. Get Devices (Only 1 query)
    devices = Device.objects.prefetch_related(temp_prefetch, hum_prefetch).all()

    # 3. Batch calculate averages (Only 1 query)
    avg_data = TemperatureReading.objects.filter(
        timestamp__date=today
    ).values('device_id').annotate(day_avg=Avg('temperature'))
    avg_map = {item['device_id']: item['day_avg'] for item in avg_data}

    devices_data = []
    for d in devices:
        # Get the first item from the prefetched list (the latest)
        last_t_obj = d.all_temps[0] if d.all_temps else None
        last_h_obj = d.all_hums[0] if d.all_hums else None

        curr_t = round(last_t_obj.temperature, 1) if (last_t_obj and last_t_obj.temperature is not None) else "--"
        curr_h = round(last_h_obj.humidity, 1) if (last_h_obj and last_h_obj.humidity is not None) else "--"

        raw_avg = avg_map.get(d.id)
        nominal = round(raw_avg, 1) if raw_avg is not None else "--"

        devices_data.append({
            'device_id': d.device_id,
            'name': d.name or d.device_id,
            'current_temp': curr_t,
            'current_hum': curr_h,
            'nominal_temperature': nominal,
        })

    # Total database queries: 4 (Previously it was N+1 or slow Subqueries)
    return render(request, 'Oceamic_app/home2.html', {'devices': devices_data})


























from django.db.models import OuterRef, Subquery, Avg, Max
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from datetime import timedelta
import traceback
import json

@login_required
def home(request):
    try:
        # Check if this is an AJAX request for live data
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            devices = Device.objects.all()

            # Get today's date range ONCE
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

            # Get all readings in ONE query for ALL devices
            all_readings = TemperatureReading.objects.filter(
                timestamp__gte=today_start
            ).select_related('device')

            # Calculate averages in Python (faster than DB)
            from collections import defaultdict
            device_temps = defaultdict(list)
            for reading in all_readings:
                if reading.temperature is not None:
                    device_temps[reading.device.id].append(float(reading.temperature))

            device_avgs = {}
            for device_id, temps in device_temps.items():
                if temps:
                    device_avgs[device_id] = round(sum(temps) / len(temps), 2)

            # Get latest readings in ONE query
            latest_temps = {}
            latest_temps_qs = TemperatureReading.objects.filter(
                device=OuterRef('pk')
            ).order_by('-timestamp')

            devices_with_latest = Device.objects.annotate(
                latest_temp_id=Subquery(latest_temps_qs.values('id')[:1])
            ).select_related('latest_temp')

            data = []
            for d in devices:
                # Get latest temperature
                latest_temp = TemperatureReading.objects.filter(device=d).order_by('-timestamp').first()
                temp_value = float(latest_temp.temperature) if latest_temp and latest_temp.temperature is not None else None

                # Get latest humidity
                latest_hum = HumidityReading.objects.filter(device=d).order_by('-timestamp').first()
                hum_value = float(latest_hum.humidity) if latest_hum and latest_hum.humidity is not None else None

                # Get today's average from our pre-calculated dict
                today_avg = device_avgs.get(d.id, None)

                data.append({
                    'id': d.device_id,
                    'temp': temp_value,
                    'hum': hum_value,
                    'today_avg': today_avg,
                })

            return JsonResponse({'devices': data})

        # Regular page render - use caching!
        cache_key = 'home_page_data'
        devices_data = cache.get(cache_key)

        if devices_data is None:
            # Same optimized queries for initial page load
            devices = Device.objects.all()
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

            # Batch fetch all data
            all_temps = TemperatureReading.objects.filter(
                timestamp__gte=today_start
            ).select_related('device')

            from collections import defaultdict
            device_avgs = defaultdict(list)
            for reading in all_temps:
                if reading.temperature is not None:
                    device_avgs[reading.device.id].append(float(reading.temperature))

            device_avg_values = {}
            for device_id, temps in device_avgs.items():
                if temps:
                    device_avg_values[device_id] = round(sum(temps) / len(temps), 2)

            devices_data = []
            for d in devices:
                latest_temp = TemperatureReading.objects.filter(device=d).order_by('-timestamp').first()
                latest_hum = HumidityReading.objects.filter(device=d).order_by('-timestamp').first()

                devices_data.append({
                    'device_id': d.device_id,
                    'name': d.name or d.device_id,
                    'temperature': latest_temp,
                    'humidity': latest_hum,
                    'today_avg': device_avg_values.get(d.id, None),
                })

            # Cache for 5 seconds (since data updates every 3 seconds)
            cache.set(cache_key, devices_data, 5)

        return render(request, 'Oceamic_app/home.html', {'devices': devices_data})

    except Exception as e:
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': str(e)}, status=500)
        else:
            raise

























from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Max, Min, Avg
from .models import Device, TemperatureReading

@login_required
def choice(request):
    all_devices = Device.objects.all().order_by('device_id')
    today = timezone.now().date()

    # --- AJAX UPDATE LOGIC (For the live gauges) ---
    # FIX: Check for both header AND accept JSON response type
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.accepts('application/json'):
        data = []
        for d in all_devices:
            try:
                latest = TemperatureReading.objects.filter(device=d).latest('timestamp')
                data.append({
                    'id': d.device_id,
                    'val': float(latest.temperature) if latest.temperature else None  # Use None instead of 0
                })
            except TemperatureReading.DoesNotExist:
                # Handle case with no readings
                data.append({
                    'id': d.device_id,
                    'val': None  # Use None for no data
                })
        return JsonResponse({'devices': data})

    # --- MAIN PAGE RENDER LOGIC ---
    devices_data = []
    for device in all_devices:
        # Get Latest
        try:
            latest_reading = TemperatureReading.objects.filter(device=device).latest('timestamp')
            current_temp = latest_reading.temperature if latest_reading else None  # Use None instead of 0
        except TemperatureReading.DoesNotExist:
            latest_reading = None
            current_temp = None  # Use None instead of 0

        # Calculate Today's Stats
        readings_today = TemperatureReading.objects.filter(device=device, timestamp__date=today)
        stats = readings_today.aggregate(
            max_t=Max('temperature'),
            min_t=Min('temperature'),
            avg_t=Avg('temperature')
        )

        # Chamber Health Logic
        health_status = "OPTIMAL"
        health_color = "#10b981" # Green

        if current_temp and current_temp > 45:
            health_status = "CRITICAL_HEAT"
            health_color = "#ef4444" # Red
        elif stats['max_t'] and stats['max_t'] > 40:
            health_status = "WARM"
            health_color = "#38bdf8" # Blue
        elif stats['min_t'] and stats['min_t'] < 5:
            health_status = "COOL"
            health_color = "#38bdf8" # Blue

        devices_data.append({
            'device_id': device.device_id,
            'name': device.name or device.device_id,
            'current_temp': round(float(current_temp), 2) if current_temp else None,  # Use None for no data
            'min_today': round(stats['min_t'], 2) if stats['min_t'] else None,  # Use None instead of 0
            'max_today': round(stats['max_t'], 2) if stats['max_t'] else None,  # Use None instead of 0
            'avg_today': round(stats['avg_t'], 2) if stats['avg_t'] else None,  # Use None instead of 0
            'health': health_status,
            'health_color': health_color,
            'status': "ONLINE" if latest_reading and (timezone.now() - latest_reading.timestamp).total_seconds() < 300 else "OFFLINE",
            'last_seen': latest_reading.timestamp if latest_reading else None
        })

    return render(request, 'Oceamic_app/choice.html', {'devices': devices_data})


@login_required
def add_device(request):
    if request.method == 'POST':
        device_id = request.POST.get('device_id')
        nominal_temperature = request.POST.get('nominal_temperature')

        # Create a new device dictionary
        new_device = {
            'device_id': device_id,
            'nominal_temperature': nominal_temperature,
            'temperature': None,
            'humidity': None
        }

        # Save the new device in the session
        if 'new_devices' not in request.session:
            request.session['new_devices'] = []

        request.session['new_devices'].append(new_device)
        request.session.modified = True

        return redirect(reverse('home'))

@login_required
def delete_device(request):
    if request.method == 'POST':
        device_id = request.POST.get('device_id')

        new_devices = request.session.get('new_devices', [])
        new_devices = [device for device in new_devices if device['device_id'] != device_id]
        request.session['new_devices'] = new_devices
        request.session.modified = True

        return JsonResponse({'status': 'success'})







import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Device, TemperatureReading
from django.db.models import Avg, Max, Min

@login_required
def device_chart(request, device_id):
    device = Device.objects.get(device_id=device_id)
    # friendly name like "Chambre positive unité-1"
    device_name = getattr(device, 'name', device_id)

    selected_date = request.GET.get('date', timezone.now().date().isoformat())

    start_date = timezone.datetime.strptime(selected_date, '%Y-%m-%d')
    if timezone.is_aware(timezone.now()):
        start_date = timezone.make_aware(start_date)

    end_date = start_date + timezone.timedelta(days=1)

    all_readings = TemperatureReading.objects.filter(
        device=device,
        timestamp__range=(start_date, end_date),
        temperature__isnull=False
    ).order_by('timestamp')

    stats = all_readings.aggregate(
        min_temp=Min('temperature'),
        max_temp=Max('temperature'),
        avg_temp=Avg('temperature')
    )

    timestamps = []
    temperatures = []
    last_added_time = None

    for reading in all_readings:
        if last_added_time is None or (reading.timestamp - last_added_time).total_seconds() >= 300:
            timestamps.append(reading.timestamp.isoformat())
            temperatures.append(float(reading.temperature))
            last_added_time = reading.timestamp

    return render(request, 'Oceamic_app/device_chart.html', {
        'device_id': device_id,
        'device_name': device_name,
        'selected_date': selected_date,
        'timestamps': json.dumps(timestamps),
        'temperatures': json.dumps(temperatures),
        'min_temp': stats['min_temp'],
        'max_temp': stats['max_temp'],
        'avg_temp': stats['avg_temp'],
    })













@login_required
def device_list(request, device_id):
    date_str = request.GET.get('date')
    if date_str:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        date = timezone.now().date()

    readings = TemperatureReading.objects.filter(device__device_id=device_id, timestamp__date=date).order_by('-timestamp')

    # Remove duplicates
    seen = set()
    unique_readings = []
    for reading in readings:
        pair = (reading.timestamp, reading.temperature)
        if pair not in seen:
            seen.add(pair)
            unique_readings.append(reading)

    context = {
        'readings': unique_readings,
        'device_id': device_id,
        'selected_date': date.strftime('%Y-%m-%d')
    }
    return render(request, 'Oceamic_app/device_list.html', context)




@login_required
def bar_chart_view(request, device_id):
    # Use device_id instead of id
    device = get_object_or_404(Device, device_id=device_id)
    selected_date = request.GET.get('date', timezone.now().date().isoformat())

    start_date = timezone.make_aware(datetime.strptime(selected_date, '%Y-%m-%d'))
    end_date = start_date + timedelta(days=1)

    readings = TemperatureReading.objects.filter(device=device, timestamp__range=(start_date, end_date)).order_by('timestamp')
    timestamps = [reading.timestamp.isoformat() for reading in readings if reading.temperature is not None]
    temperatures = [float(reading.temperature) for reading in readings if reading.temperature is not None]  # Filter out None values

    return render(request, 'Oceamic_app/bar_chart.html', {
        'device_id': device_id,
        'selected_date': selected_date,
        'timestamps': json.dumps(timestamps),
        'temperatures': json.dumps(temperatures),
    })






@login_required
def new_multi_device_chart(request, device_id):
    device = get_object_or_404(Device, device_id=device_id)
    selected_dates = request.GET.get('dates', '').split(',')

    all_readings = []
    for selected_date in selected_dates:
        try:
            start_date = timezone.make_aware(datetime.strptime(selected_date.strip(), '%Y-%m-%d'))
            end_date = start_date + timedelta(days=1)
            readings = TemperatureReading.objects.filter(device=device, timestamp__range=(start_date, end_date)).order_by('timestamp')

            timestamps = [reading.timestamp.isoformat() for reading in readings if reading.temperature is not None]
            temperatures = [float(reading.temperature) for reading in readings if reading.temperature is not None]  # Filter out None values

            all_readings.append({
                'date': selected_date.strip(),
                'timestamps': json.dumps(timestamps),
                'temperatures': json.dumps(temperatures),
            })
        except ValueError:
            pass  # Skip invalid date formats

    return render(request, 'Oceamic_app/multi_bar_chart.html', {
        'device_id': device_id,
        'selected_dates': ', '.join(selected_dates),
        'all_readings': json.dumps(all_readings),
    })


@login_required
def g_chart(request, device_id):
    selected_date = request.GET.get('date', None)
    if not selected_date:
        selected_date = timezone.now().strftime('%Y-%m-%d')

    start_date = datetime.strptime(selected_date, '%Y-%m-%d')
    end_date = start_date + timedelta(days=1)
    readings = TemperatureReading.objects.filter(device__device_id=device_id, timestamp__range=(start_date, end_date))
    timestamps = [reading.timestamp.isoformat() for reading in readings if reading.temperature is not None]
    temperatures = [float(reading.temperature) for reading in readings if reading.temperature is not None]  # Convert Decimal to float

    context = {
        'device_id': device_id,
        'selected_date': selected_date,
        'timestamps': json.dumps(timestamps),
        'temperatures': json.dumps(temperatures),
    }
    return render(request, 'Oceamic_app/g_chart.html', context)






@login_required
def humidity_chart(request, device_id):
    try:
        device = Device.objects.get(device_id=device_id)
    except Device.DoesNotExist:
        return render(request, 'Oceamic_app/humidity_chart.html', {'error': 'Device not found'})

    selected_date = request.GET.get('date', str(date.today()))  # Correct usage of date.today()
    humidity_readings = HumidityReading.objects.filter(device=device, timestamp__date=selected_date).order_by('timestamp')

    labels = []
    data = []
    for reading in humidity_readings:
        if reading.humidity is not None:
            labels.append(reading.timestamp.strftime('%H:%M'))
            data.append(reading.humidity)

    context = {
        'device_id': device_id,
        'labels': labels,
        'data': data,
        'selected_date': selected_date,
    }

    return render(request, 'Oceamic_app/humidity_chart.html', context)

@login_required
def multi_humidity_chart(request, device_id):
    try:
        device = Device.objects.get(device_id=device_id)
    except Device.DoesNotExist:
        return render(request, 'Oceamic_app/multi_humidity_chart.html', {'error': 'Device not found'})

    selected_dates_str = request.GET.get('dates', '')
    selected_dates = [d.strip() for d in selected_dates_str.split(',') if d.strip()]

    if not selected_dates:
        selected_dates = [str(date.today())]

    all_readings = []
    for selected_date in selected_dates:
        try:
            date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            return render(request, 'Oceamic_app/multi_humidity_chart.html', {'error': f'Invalid date format: {selected_date}. It must be in YYYY-MM-DD format.'})

        humidity_readings = HumidityReading.objects.filter(device=device, timestamp__date=date_obj).order_by('timestamp')

        readings = {
            'date': selected_date,
            'timestamps': [reading.timestamp.strftime('%Y-%m-%dT%H:%M:%S') for reading in humidity_readings],
            'humidities': [reading.humidity for reading in humidity_readings]
        }
        if not readings['timestamps']:
            readings['timestamps'] = ['No data available']
            readings['humidities'] = [0]
        all_readings.append(readings)

    all_readings_json = json.dumps(all_readings)

    context = {
        'device_id': device_id,
        'all_readings': all_readings_json,
        'selected_dates': selected_dates_str,
    }

    return render(request, 'Oceamic_app/multi_humidity_chart.html', context)




@login_required
def humidity_bar_chart(request, device_id):
    try:
        device = Device.objects.get(device_id=device_id)
    except Device.DoesNotExist:
        return render(request, 'Oceamic_app/humidity_bar_chart.html', {'error': 'Device not found'})

    selected_date_str = request.GET.get('date', str(datetime.today().date()))
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        return render(request, 'Oceamic_app/humidity_bar_chart.html', {'error': 'Invalid date format. It must be in YYYY-MM-DD format.'})

    humidity_readings = HumidityReading.objects.filter(device=device, timestamp__date=selected_date).order_by('timestamp')

    timestamps = [reading.timestamp.strftime('%Y-%m-%dT%H:%M:%S') for reading in humidity_readings if reading.humidity is not None]
    humidities = [reading.humidity for reading in humidity_readings if reading.humidity is not None]

    context = {
        'device_id': device_id,
        'selected_date': selected_date_str,
        'timestamps': json.dumps(timestamps),
        'humidities': json.dumps(humidities),
    }

    return render(request, 'Oceamic_app/humidity_bar_chart.html', context)



@login_required
def multi_humidity_bar_chart(request, device_id):
    try:
        device = Device.objects.get(device_id=device_id)
    except Device.DoesNotExist:
        return render(request, 'Oceamic_app/multi_humidity_bar_chart.html', {'error': 'Device not found'})

    selected_dates_str = request.GET.get('dates', '')
    selected_dates = [d.strip() for d in selected_dates_str.split(',') if d.strip()]

    if not selected_dates:
        selected_dates = [str(datetime.today().date())]

    all_readings = []
    for selected_date in selected_dates:
        try:
            date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            return render(request, 'Oceamic_app/multi_humidity_bar_chart.html', {'error': f'Invalid date format: {selected_date}. It must be in YYYY-MM-DD format.'})

        humidity_readings = HumidityReading.objects.filter(device=device, timestamp__date=date_obj).order_by('timestamp')

        readings = {
            'date': selected_date,
            'timestamps': [reading.timestamp.strftime('%Y-%m-%dT%H:%M:%S') for reading in humidity_readings if reading.humidity is not None],
            'humidities': [reading.humidity for reading in humidity_readings if reading.humidity is not None]
        }
        all_readings.append(readings)

    all_readings_json = json.dumps(all_readings)

    context = {
        'device_id': device_id,
        'all_readings': all_readings_json,
        'selected_dates': selected_dates_str,
    }

    return render(request, 'Oceamic_app/multi_humidity_bar_chart.html', context)

@login_required
def humidity_google_chart(request, device_id):
    try:
        device = Device.objects.get(device_id=device_id)
    except Device.DoesNotExist:
        return render(request, 'Oceamic_app/multi_humidity_google_chart.html', {'error': 'Device not found'})

    selected_dates_str = request.GET.get('dates', '')
    selected_dates = [d.strip() for d in selected_dates_str.split(',') if d.strip()]

    if not selected_dates:
        selected_dates = [str(datetime.today().date())]

    all_readings = []
    for selected_date in selected_dates:
        try:
            date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            return render(request, 'Oceamic_app/multi_humidity_google_chart.html', {'error': f'Invalid date format: {selected_date}. It must be in YYYY-MM-DD format.'})

        humidity_readings = HumidityReading.objects.filter(device=device, timestamp__date=date_obj).order_by('timestamp')

        readings = {
            'date': selected_date,
            'data': [["Time", "Humidity"]] + [[reading.timestamp.strftime('%Y-%m-%dT%H:%M:%S'), reading.humidity] for reading in humidity_readings if reading.humidity is not None]
        }
        all_readings.append(readings)

    context = {
        'device_id': device_id,
        'all_readings': json.dumps(all_readings),
        'selected_dates': selected_dates_str,
    }

    return render(request, 'Oceamic_app/humidity_google_chart.html', context)

























from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required

@login_required
@require_GET
def get_notifications(request):
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]

    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    return JsonResponse({
        'notifications': [
            {
                'id': n.id,
                'message': n.message,
                'is_read': n.is_read,
                'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
                'type': n.notification_type,
                'device': n.device.name if n.device else None
            } for n in notifications
        ],
        'unread_count': unread_count
    })

@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'status': 'success'})

@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})



# views.py
@csrf_exempt
def special_character(request):
    if request.method == 'GET':
        try:
            special_character = None
            devices = Device.objects.all()

            for device in devices:
                reading = TemperatureReading(
                    device=device,
                    temperature=special_character,
                    timestamp=timezone.now()
                )
                reading.save()

            # Return success response with 200 status
            return JsonResponse({
                "status": "success",
                "message": "Special character readings saved",
                "timestamp": timezone.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error in special_character: {str(e)}")
            return JsonResponse({
                "status": "error",
                "message": str(e)
            }, status=500)

    # Return 405 for non-GET requests
    return JsonResponse({
        "status": "error",
        "message": "Method not allowed"
    }, status=405)


@csrf_exempt
def trigger_check(request):
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    try:
        current_time = timezone.now()
        alert_settings = TemperatureAlertSetting.objects.select_related('device').all()
        notifications_sent = 0

        for alert_setting in alert_settings:
            device = alert_setting.device
            latest_reading = TemperatureReading.objects.filter(device=device).order_by('-timestamp').first()

            if not latest_reading or latest_reading.temperature is None:
                continue

            current_temp = float(latest_reading.temperature)
            threshold = float(alert_setting.threshold)

            if current_temp >= threshold:
                should_send = False
                if not alert_setting.alert_triggered or alert_setting.last_alert_sent is None:
                    should_send = True
                elif (current_time - alert_setting.last_alert_sent) >= timedelta(minutes=alert_setting.alert_frequency):
                    should_send = True

                if should_send:
                    # --- FIXED FIELD NAMES HERE ---
                    new_alert = TemperatureAlert.objects.create(
                        device=device,
                        temperature=current_temp, # Changed from temperature_value
                        threshold=threshold,      # Changed from threshold_value
                        timestamp=current_time
                    )

                    payload = {
                        "head": "Oceamic II",
                        "title": "Temperature Alert",
                        "body": f"🌡️ {device.name}: {current_temp}°C (Limit: {threshold}°C)",
                        "icon": "/static/images/pic2.png",
                        "badge": "/static/images/pic2.png",
                        "url": f"/device/{device.device_id}/chart/",
                        "tag": "thermal-status",
                        "actions": [
                            {"action": "open", "title": "📈 View ChartG"},
                            {"action": "close", "title": "Dismiss"}
                        ]
                    }

                    staff_users = User.objects.filter(is_staff=True)
                    for staff in staff_users:
                        Notification.objects.create(
                            user=staff,
                            device=device,
                            alert=new_alert,
                            notification_type='ALERT',
                            message=payload["body"],
                            is_read=False
                        )

                        try:
                            from webpush import send_user_notification
                            send_user_notification(user=staff, payload=payload, ttl=3600)
                            notifications_sent += 1
                        except Exception as push_err:
                            logger.error(f"Push failed: {push_err}")

                    alert_setting.last_alert_sent = current_time
                    alert_setting.alert_triggered = True
                    alert_setting.save()

        return JsonResponse({'status': 'success', 'notifications_sent': notifications_sent})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)



@require_GET
@gzip_page
def service_worker(request):
    """Forces the phone to load sw-v4.js and ignore old cached versions."""
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'js', 'sw-v4.js')
    try:
        with open(sw_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/javascript')
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            return response
    except FileNotFoundError:
        return HttpResponse("// SW not found", status=404)






def device_api_latest(request):
    devices_data = []
    # Replace with your actual logic to get latest readings
    devices = Device.objects.all()
    for d in devices:
        latest = d.get_latest_reading() # Assuming you have this method
        devices_data.append({
            "id": d.device_id,
            "temp": latest.temperature,
            "hum": latest.humidity,
            "avg": d.get_today_average() # Your average calculation
        })
    return JsonResponse(devices_data, safe=False)





from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Notification

@login_required
def notifications_all(request):
    # We use select_related('alert') to grab the temperature and threshold
    # from the linked TemperatureAlert table without changing models.
    notifications = Notification.objects.filter(
        user=request.user
    ).select_related('alert', 'device').order_by('-created_at')

    return render(request, 'notifications/all_notifications.html', {
        'notifications': notifications
    })

from django.db.models import Avg
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
import json

from django.db.models import Avg
from django.db.models.functions import TruncDate


@login_required
def device_analysis(request, device_id):
    device = get_object_or_404(Device, device_id=device_id)

    # Map IDs to Friendly Names
    name_map = {
        'device1': 'Chambre négative-1 unité-2',
        'device2': 'Chambre positive unité-2',
        'device3': 'Chambre ingrédients unité-2',
        'device4': 'Chambre positive unité-1',
        'device5': 'Chambre négative-2 unité-2',
        'device6': 'Chambre ingrédients unité-1',
    }
    friendly_name = name_map.get(device_id, device_id)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            start_date = data.get('start_date')
            end_date = data.get('end_date')

            daily_data = TemperatureReading.objects.filter(
                device=device,
                timestamp__date__range=[start_date, end_date],
                temperature__isnull=False
            ).annotate(
                day=TruncDate('timestamp')
            ).values('day').annotate(
                avg_temp=Avg('temperature')
            ).order_by('day')

            chart_data = [{'timestamp': d['day'].strftime('%Y-%m-%d'), 'temperature': round(float(d['avg_temp']), 2)} for d in daily_data]
            return JsonResponse({'chart_data': chart_data})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return render(request, 'Oceamic_app/device_analysis.html', {
        'device': device,
        'friendly_name': friendly_name
    })





from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse
# Correct imports based on your models.py
from .models import Device, TemperatureReading

def clean_and_thin_database(request):
    """
    DATA THINNING STRATEGY:
    Keeps 1 reading every 5 minutes. Deletes the 15-second 'noise'.
    """
    now = timezone.now()
    # We only clean data older than 20 minutes so we don't interfere with live alerts
    thinning_cutoff = now - timedelta(minutes=20)

    total_deleted = 0

    try:
        # Atomic transaction ensures NO data is lost if the server glitches
        with transaction.atomic():
            devices = Device.objects.all()

            for device in devices:
                # Get all readings for this specific device older than 20 mins
                readings = TemperatureReading.objects.filter(
                    device=device,
                    timestamp__lt=thinning_cutoff
                ).order_by('timestamp')

                if not readings.exists():
                    continue

                kept_ids = []
                last_kept_time = None

                for r in readings:
                    # If this is the first reading OR it's been 5+ mins since the last one we kept
                    if last_kept_time is None or (r.timestamp - last_kept_time) >= timedelta(minutes=5):
                        kept_ids.append(r.id)
                        last_kept_time = r.timestamp

                # Efficiently delete all records for this device that are NOT in the 'kept' list
                deleted_count, _ = TemperatureReading.objects.filter(
                    device=device,
                    timestamp__lt=thinning_cutoff
                ).exclude(id__in=kept_ids).delete()

                total_deleted += deleted_count

        return HttpResponse(f"SUCCESS: Removed {total_deleted} redundant records.", content_type="text/plain")

    except Exception as e:
        return HttpResponse(f"DATABASE ERROR: {str(e)}", status=500)








from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .models import Notification

def get_latest_notifications(request):
    # Calculate the time 24 hours ago
    time_threshold = timezone.now() - timedelta(hours=24)

    # Filter notifications created within the last 24 hours
    notifications = Notification.objects.filter(
        created_at__gte=time_threshold
    ).select_related('device').order_by('-created_at')[:10]

    data = []
    for n in notifications:
        time_str = timezone.localtime(n.created_at).strftime('%H:%M')
        data.append({
            "device": n.device.name if n.device else "SYS",
            "message": n.message,
            "time": time_str
        })

    return JsonResponse({"notifications": data})




























from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import Device, TemperatureReading
import math
import random
from decimal import Decimal

def r404a_saturation_temp_to_pressure(temp_c):
    """Convert temperature to saturation pressure for R404A (bar)"""
    if isinstance(temp_c, Decimal):
        temp_c = float(temp_c)

    # More accurate R404A pressure-temperature relationship
    if temp_c < -40:
        return 0.8 + (temp_c + 40) * 0.02
    elif temp_c < -30:
        return 1.2 + (temp_c + 30) * 0.04
    elif temp_c < -20:
        return 1.8 + (temp_c + 20) * 0.07
    elif temp_c < -10:
        return 2.5 + (temp_c + 10) * 0.1
    elif temp_c < 0:
        return 3.5 + temp_c * 0.12
    elif temp_c < 10:
        return 4.7 + temp_c * 0.15
    else:
        return 6.2 + (temp_c - 10) * 0.2

def calculate_thermal_params(room_temp, compressor_config):
    """
    REALISTIC calculations for R404A systems
    compressor_config: (num_compressors, hp_per_compressor)
    """
    # If room_temp is None, return None for all values
    if room_temp is None:
        return {
            'evap_temp': None,
            'cond_temp': None,
            'bp': None,
            'hp': None,
            'comp_current': None,
            'comp_power': None,
            'evap_power': None,
            'cond_power': None,
            'cop': None,
        }

    if isinstance(room_temp, Decimal):
        room_temp = float(room_temp)

    num_comps, hp_per_comp = compressor_config
    total_hp = num_comps * hp_per_comp

    # Evaporator temperature = room temp - 6K superheat
    evap_temp = room_temp - 6

    # Condenser temperature (ambient + 15K)
    cond_temp = 35  # 25°C ambient + 10°C approach (more realistic)

    # Saturation pressures
    bp = r404a_saturation_temp_to_pressure(evap_temp)

    # HP RANDOMLY BETWEEN 16-18 BAR (as requested)
    hp = round(random.uniform(16.0, 18.0), 1)

    # Base cooling capacity per hp at different evaporating temps
    if evap_temp < -20:
        capacity_per_hp = 0.65  # kW per hp at deep freeze
    elif evap_temp < -10:
        capacity_per_hp = 0.85  # kW per hp at freezer
    elif evap_temp < 0:
        capacity_per_hp = 1.05  # kW per hp at cold storage
    else:
        capacity_per_hp = 1.25  # kW per hp at cooler

    # Evaporator power (cooling capacity)
    evap_power = total_hp * capacity_per_hp

    # COP estimation based on pressure ratio (hp/bp)
    pressure_ratio = hp / bp if bp > 0 else 10

    # Realistic COP for R404A based on pressure ratio
    if pressure_ratio < 3:
        cop = 3.5
    elif pressure_ratio < 4:
        cop = 3.0
    elif pressure_ratio < 5:
        cop = 2.5
    elif pressure_ratio < 6:
        cop = 2.2
    else:
        cop = 1.8

    # Compressor power = Evaporator power / COP
    comp_power = evap_power / cop

    # Compressor current at 380V 3-phase
    voltage = 380
    comp_current = (comp_power * 1000) / (math.sqrt(3) * voltage * 0.85)

    # Condenser power = Evaporator power + Compressor power
    cond_power = evap_power + comp_power

    return {
        'evap_temp': round(evap_temp, 1),
        'cond_temp': round(cond_temp, 1),
        'bp': round(bp, 1),
        'hp': hp,  # Random between 16-18 bar
        'comp_current': round(comp_current, 1),
        'comp_power': round(comp_power, 2),
        'evap_power': round(evap_power, 2),
        'cond_power': round(cond_power, 2),
        'cop': round(cop, 2),
    }

# HARDCODED device configurations
DEVICE_CONFIGS = {
    'device1': {'name': 'NEGATIVE 1', 'compressors': 2, 'hp': 28},
    'device3': {'name': 'NEGATIVE 2', 'compressors': 2, 'hp': 33},
    'device4': {'name': 'INGREDIENTS', 'compressors': 1, 'hp': 24},
    'device2': {'name': 'POSITIVE', 'compressors': 1, 'hp': 22},
}

@login_required
def detailed_status(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        devices = Device.objects.all()
        data = []

        for device in devices:
            latest_temp = TemperatureReading.objects.filter(
                device=device
            ).order_by('-timestamp').first()

            # FIX: Don't default to 20.0, keep None if no valid temperature
            room_temp = None
            if latest_temp and latest_temp.temperature is not None:
                room_temp = float(latest_temp.temperature)

            config = DEVICE_CONFIGS.get(device.device_id,
                                       {'compressors': 1, 'hp': 20})

            params = calculate_thermal_params(
                room_temp,
                (config['compressors'], config['hp'])
            )

            seconds_ago = 0
            if latest_temp:
                delta = timezone.now() - latest_temp.timestamp
                seconds_ago = int(delta.total_seconds())

            data.append({
                'id': device.device_id,
                'room_temp': round(room_temp, 1) if room_temp is not None else None,
                'evap_temp': params['evap_temp'],
                'cond_temp': params['cond_temp'],
                'bp': params['bp'],
                'hp': params['hp'],
                'comp_current': params['comp_current'],
                'comp_power': params['comp_power'],
                'evap_power': params['evap_power'],
                'cond_power': params['cond_power'],
                'cop': params['cop'],
                'seconds_ago': seconds_ago,
            })

        return JsonResponse({'devices': data})

    # Regular page render
    devices = Device.objects.all()
    devices_data = []

    for device in devices:
        latest_temp = TemperatureReading.objects.filter(
            device=device
        ).order_by('-timestamp').first()

        # FIX: Don't default to 20.0, keep None if no valid temperature
        room_temp = None
        if latest_temp and latest_temp.temperature is not None:
            room_temp = float(latest_temp.temperature)

        config = DEVICE_CONFIGS.get(device.device_id,
                                   {'name': device.name or device.device_id,
                                    'compressors': 1, 'hp': 20})

        params = calculate_thermal_params(
            room_temp,
            (config['compressors'], config['hp'])
        )

        devices_data.append({
            'device_id': device.device_id,
            'name': config['name'],
            'compressors': config['compressors'],
            'power': config['hp'],
            'room_temp': room_temp,
            'evap_temp': params['evap_temp'],
            'cond_temp': params['cond_temp'],
            'bp': params['bp'],
            'hp': params['hp'],
            'comp_current': params['comp_current'],
            'comp_power': params['comp_power'],
            'evap_power': params['evap_power'],
            'cond_power': params['cond_power'],
            'cop': params['cop'],
        })

    return render(request, 'Oceamic_app/detailed_status.html', {'devices': devices_data})
















from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@csrf_exempt  # Allow external systems to call this without CSRF token
def public_api_latest(request):
    """
    Public API endpoint for GMAO to get latest temperatures.
    No authentication required.
    Returns JSON with all 3 device readings.
    """
    devices = Device.objects.filter(device_id__in=['device1', 'device2', 'device3', 'device4'])

    data = []
    for device in devices:
        latest = TemperatureReading.objects.filter(device=device).order_by('-timestamp').first()

        data.append({
            'device_id': device.device_id,
            'name': device.name,
            'temperature': float(latest.temperature) if latest and latest.temperature is not None else None,
            'timestamp': latest.timestamp.isoformat() if latest else None,
            'status': 'online' if latest and latest.temperature is not None else 'offline'
        })

    return JsonResponse({
        'status': 'success',
        'timestamp': timezone.now().isoformat(),
        'devices': data
    })































# ============================================================
# WINDOWS APP API — LOGIN + DEVICES + HISTORY
# ============================================================

from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.db.models import Avg, Min, Max

@csrf_exempt
@require_POST
def app_login(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return JsonResponse({'success': False, 'error': 'Missing credentials'}, status=400)

    user = authenticate(request, username=username, password=password)
    if not user:
        return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)

    if not user.is_active:
        return JsonResponse({'success': False, 'error': 'Account disabled'}, status=403)

    token, _ = Token.objects.get_or_create(user=user)

    return JsonResponse({
        'success': True,
        'token': token.key,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff,
        }
    })

def _check_app_token(request):
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Token '):
        return None
    key = auth.split(' ', 1)[1].strip()
    try:
        return Token.objects.select_related('user').get(key=key).user
    except Token.DoesNotExist:
        return None

@require_GET
def app_devices(request):
    user = _check_app_token(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

    devices = Device.objects.all().order_by('device_id')
    out = []
    for d in devices:
        latest_t = TemperatureReading.objects.filter(device=d).order_by('-timestamp').first()
        latest_h = HumidityReading.objects.filter(device=d).order_by('-timestamp').first()

        temp_val = None
        if latest_t and latest_t.temperature is not None:
            temp_val = float(latest_t.temperature)

        hum_val = None
        if latest_h and latest_h.humidity is not None:
            hum_val = float(latest_h.humidity)

        online = False
        if latest_t and (timezone.now() - latest_t.timestamp).total_seconds() < 300:
            online = True

        out.append({
            'device_id': d.device_id,
            'name': d.name or d.device_id,
            'temperature': temp_val,
            'humidity': hum_val,
            'timestamp': latest_t.timestamp.isoformat() if latest_t else None,
            'status': 'online' if online else 'offline',
        })

    return JsonResponse({'success': True, 'devices': out})

@require_GET
def app_history_day(request, device_id):
    user = _check_app_token(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

    device = get_object_or_404(Device, device_id=device_id)
    date_str = request.GET.get('date', timezone.now().date().isoformat())

    try:
        start = timezone.make_aware(datetime.strptime(date_str, '%Y-%m-%d'))
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid date format'}, status=400)

    end = start + timedelta(days=1)

    readings = TemperatureReading.objects.filter(
        device=device,
        timestamp__range=(start, end),
        temperature__isnull=False
    ).order_by('timestamp')

    timestamps, temperatures = [], []
    last_added = None
    for r in readings:
        if last_added is None or (r.timestamp - last_added).total_seconds() >= 300:
            timestamps.append(r.timestamp.isoformat())
            temperatures.append(float(r.temperature))
            last_added = r.timestamp

    stats = {
        'min': round(min(temperatures), 1) if temperatures else None,
        'max': round(max(temperatures), 1) if temperatures else None,
        'avg': round(sum(temperatures) / len(temperatures), 1) if temperatures else None,
    }

    return JsonResponse({
        'success': True,
        'device_id': device.device_id,
        'device_name': device.name or device.device_id,
        'date': date_str,
        'timestamps': timestamps,
        'temperatures': temperatures,
        'stats': stats,
    })

@require_GET
def app_history_range(request, device_id):
    user = _check_app_token(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

    device = get_object_or_404(Device, device_id=device_id)
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')

    if not start_str or not end_str:
        return JsonResponse({'success': False, 'error': 'start and end required'}, status=400)

    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid date format'}, status=400)

    daily = TemperatureReading.objects.filter(
        device=device,
        timestamp__date__range=[start_date, end_date],
        temperature__isnull=False
    ).values('timestamp__date').annotate(
        avg_temp=Avg('temperature'),
        min_temp=Min('temperature'),
        max_temp=Max('temperature')
    ).order_by('timestamp__date')

    days = []
    for row in daily:
        days.append({
            'date': row['timestamp__date'].isoformat(),
            'avg': round(float(row['avg_temp']), 1),
            'min': round(float(row['min_temp']), 1),
            'max': round(float(row['max_temp']), 1),
        })

    return JsonResponse({
        'success': True,
        'device_id': device.device_id,
        'device_name': device.name or device.device_id,
        'start': start_str,
        'end': end_str,
        'days': days,
    })

@require_GET
def app_report(request, device_id):
    user = _check_app_token(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

    device = get_object_or_404(Device, device_id=device_id)
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    if not start_str or not end_str:
        return JsonResponse({'success': False, 'error': 'start and end required'}, status=400)

    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid date'}, status=400)

    days_out = []
    cur = start_date
    while cur <= end_date:
        readings = TemperatureReading.objects.filter(
            device=device,
            timestamp__date=cur,
            temperature__isnull=False
        ).order_by('timestamp')

        timestamps, temps = [], []
        last = None
        for r in readings:
            if last is None or (r.timestamp - last).total_seconds() >= 300:
                timestamps.append(r.timestamp.isoformat())
                temps.append(float(r.temperature))
                last = r.timestamp

        if timestamps:
            days_out.append({
                'date': cur.isoformat(),
                'timestamps': timestamps,
                'temperatures': temps
            })
        cur += timedelta(days=1)

    return JsonResponse({
        'success': True,
        'device_id': device.device_id,
        'start': start_str,
        'end': end_str,
        'days': days_out
    })

@require_GET
def app_report_fast(request, device_id):
    user = _check_app_token(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    if not start_str or not end_str:
        return JsonResponse({'success': False, 'error': 'start and end required'}, status=400)

    cache_key = f"app_report_{device_id}_{start_str}_{end_str}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    device = get_object_or_404(Device, device_id=device_id)

    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid date'}, status=400)

    readings = TemperatureReading.objects.filter(
        device=device,
        timestamp__date__range=[start_date, end_date],
        temperature__isnull=False
    ).order_by('timestamp').values('timestamp', 'temperature')

    from collections import defaultdict
    days_data = defaultdict(list)
    for r in readings:
        days_data[r['timestamp'].date()].append((r['timestamp'], float(r['temperature'])))

    days_out = []
    cur = start_date
    while cur <= end_date:
        bucket = days_data.get(cur, [])
        timestamps, temps = [], []
        last = None
        for ts, v in bucket:
            if last is None or (ts - last).total_seconds() >= 300:
                timestamps.append(ts.isoformat())
                temps.append(v)
                last = ts
        if timestamps:
            days_out.append({
                'date': cur.isoformat(),
                'timestamps': timestamps,
                'temperatures': temps
            })
        cur += timedelta(days=1)

    payload = {
        'success': True,
        'device_id': device.device_id,
        'start': start_str,
        'end': end_str,
        'days': days_out
    }
    cache.set(cache_key, payload, 300)
    return JsonResponse(payload)

@require_GET
def app_notifications(request):
    user = _check_app_token(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

    device_id = request.GET.get('device_id')
    date_str = request.GET.get('date')

    qs = Notification.objects.select_related('device', 'alert').all().order_by('-created_at')

    if device_id:
        qs = qs.filter(device__device_id=device_id)
    if date_str:
        try:
            d = datetime.strptime(date_str, '%Y-%m-%d').date()
            qs = qs.filter(created_at__date=d)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date'}, status=400)

    qs = qs[:300]

    data = []
    for n in qs:
        data.append({
            'id': n.id,
            'message': n.message,
            'type': n.notification_type,
            'is_read': n.is_read,
            'device_id': n.device.device_id if n.device else None,
            'device_name': n.device.name if n.device else 'SYS',
            'temperature': float(n.alert.temperature) if n.alert and n.alert.temperature is not None else None,
            'threshold': float(n.alert.threshold) if n.alert and n.alert.threshold is not None else None,
            'created_at': n.created_at.isoformat(),
        })

    return JsonResponse({'success': True, 'notifications': data})

@csrf_exempt
@require_POST
def app_mark_notification_read(request, notification_id):
    user = _check_app_token(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

    try:
        n = Notification.objects.get(id=notification_id)
        n.is_read = True
        n.save(update_fields=['is_read'])
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)

@csrf_exempt
@require_POST
def app_mark_all_notifications_read(request):
    user = _check_app_token(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

    Notification.objects.filter(is_read=False).update(is_read=True)
    return JsonResponse({'success': True})

@csrf_exempt
@require_POST
def app_update_device(request, device_id):
    user = _check_app_token(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

    device = get_object_or_404(Device, device_id=device_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    if 'name' in data:
        device.name = data['name']
    if 'offset' in data:
        try:
            device.temperature_offset = float(data['offset'])
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid offset'}, status=400)

    device.save()
    return JsonResponse({'success': True})