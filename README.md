# OceanRemote Own-Hosting

Self-host your own cold-chain temperature monitoring server on **PythonAnywhere** - free tier works perfectly.

The companion **WPF Desktop Client** (OceanRemote Monitor) connects to any server built from this repo to monitor your sensors, generate firmware, and print PDF reports.

## What you get
- **Django Backend** with a REST API and a beautiful dark-mode web dashboard.
- **Device Management** (rename, calibrate, delete).
- **Historical Charts** (24H Log, 30D Trend, PDF Reports).
- **Alerts & Notifications** via Web Push.
- **Mobile-Ready PWA** (Install the web app on your phone).
- **Firmware Generator** for ESP8266, ESP32, and Raspberry Pi Pico W.
- **1-Click Installer** that configures everything automatically.

## Prerequisites
1. A free **PythonAnywhere** account.
2. An **API Token** from your PythonAnywhere account. 
   *(Go to Account -> API Token -> Create a new API token. Copy it).*

## 1-Minute Setup (The Magic Way)

You do not need to install anything on your computer. You do not need to clone, edit files, or configure WSGI manually.

1. Open a **Bash Console** on PythonAnywhere (Consoles -> Bash).
2. Paste this exact command and hit Enter:

git clone https://github.com/AdminOceanremote/oceanremote-own-hosting.git && cd oceanremote-own-hosting && bash bootstrap.sh

The script will:
- Create a virtual environment.
- Install all Python requirements.
- Automatically create your web app via the PythonAnywhere API.
- Ask you for a superuser username, email, and password.
- Configure the WSGI file and static mapping.
- Reload the server.

**That's it!** Your server will be live at https://your-username.pythonanywhere.com.

## Desktop Client (Windows)

To monitor your data locally, generate firmware, or print PDF reports, download and install the WPF desktop client. 

In the app Settings, set your Server URL to https://your-username.pythonanywhere.com and log in with the superuser credentials you created.

## Firmware
You don't need to write code. Use the Desktop App's **Firmware Generator** to:
1. Select your board (ESP32, ESP8266 D1 Mini/Large, Pico W).
2. Add as many sensors as your board supports (DHT22, DS18B20, NTC).
3. Enter your WiFi credentials.
4. Click **Generate Code** and copy it to the Arduino IDE.

## License
MIT