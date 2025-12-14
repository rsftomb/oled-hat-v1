#!/usr/bin/env python3
import time
import psutil
import subprocess
import threading
import random
import math
import csv
from datetime import timedelta, datetime

import RPi.GPIO as GPIO
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas

# =====================
# Version
# =====================
VERSION = "v1.50"

# =====================
# OLED setup
# =====================
oled_left = ssd1306(i2c(port=1, address=0x3C))
oled_right = ssd1306(i2c(port=1, address=0x3D))

# =====================
# Buttons
# =====================
BTN_K1 = 5
BTN_K2 = 6
BTN_K3 = 16
BTN_K4 = 24

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
for b in (BTN_K1, BTN_K2, BTN_K3, BTN_K4):
    GPIO.setup(b, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# =====================
# Runtime state
# =====================
wifi_enabled = True
bt_enabled = True
logging_enabled = True

wifi_now = 0
wifi_total = 0
bt_now = 0
bt_total = 0

seen_wifi = {}
seen_bt = {}
bt_last_seen = {}
bt_blips = {}

lock = threading.Lock()

# =====================
# Control menu
# =====================
MENU_ITEMS = [
    "WiFi Scan",
    "Bluetooth Scan",
    "Logging",
    "Clear WiFi",
    "Clear BT"
]
menu_index = 0
last_button = 0
DEBOUNCE = 0.25

# =====================
# Helpers
# =====================
def pressed(pin):
    return GPIO.input(pin) == GPIO.LOW

def get_cpu_temp():
    try:
        t = subprocess.check_output("vcgencmd measure_temp", shell=True).decode()
        c = float(t.replace("temp=","").replace("'C\n",""))
        return f"{(c*9/5)+32:.1f}F"
    except:
        return "?"

def get_uptime():
    try:
        s = float(open("/proc/uptime").read().split()[0])
        return str(timedelta(seconds=int(s)))
    except:
        return "?"

def get_sd_health():
    try:
        u = psutil.disk_usage("/")
        free = u.free / (1024**3)
        return f"SD {u.percent:.0f}% {free:.1f}G"
    except:
        return "SD ERR"

def log_wifi_csv(ssid, bssid, channel, level):
    if not logging_enabled:
        return
    with open("/home/pi/wigle_wifi_log.csv", "a", newline='') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.utcnow().isoformat(), ssid, bssid, channel, level])

def log_bt_csv(mac, name):
    if not logging_enabled:
        return
    with open("/home/pi/wigle_bt_log.csv", "a", newline='') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.utcnow().isoformat(), mac, name])

# =====================
# Wi-Fi scanner
# =====================
def wifi_scanner():
    global wifi_now, wifi_total
    while True:
        if not wifi_enabled:
            time.sleep(1)
            continue

        current = {}
        try:
            out = subprocess.check_output(
                "sudo iwlist wlan0 scan 2>/dev/null | grep -E 'ESSID|Address|Channel|Signal'",
                shell=True
            ).decode()
            ssid, bssid, channel, level = None, None, None, None
            for l in out.splitlines():
                l = l.strip()
                if "Address:" in l:
                    bssid = l.split("Address:")[1].strip()
                elif "ESSID:" in l:
                    ssid = l.split("ESSID:")[1].replace('"','').strip()
                elif "Channel:" in l:
                    channel = l.split("Channel:")[1].strip()
                elif "Signal level=" in l:
                    try:
                        level = int(l.split("Signal level=")[1].split()[0])
                    except:
                        level = 0
                if ssid and bssid:
                    current[bssid] = (ssid, channel, level)
                    seen_wifi[bssid] = (ssid, channel, level)
                    log_wifi_csv(ssid, bssid, channel, level)
                    ssid, bssid, channel, level = None, None, None, None
        except:
            pass

        with lock:
            wifi_now = len(current)
            wifi_total = len(seen_wifi)

        time.sleep(5)

# =====================
# Bluetooth scanner
# =====================
def bt_scanner():
    global bt_now, bt_total

    subprocess.Popen("bluetoothctl scan on", shell=True,
                     stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)

    while True:
        if not bt_enabled:
            time.sleep(1)
            continue

        try:
            out = subprocess.check_output("bluetoothctl devices", shell=True).decode()
            now = time.time()
            for l in out.splitlines():
                if l.startswith("Device"):
                    _, mac, *name = l.split()
                    name = " ".join(name) if name else "Unknown"
                    seen_bt[mac] = name
                    bt_last_seen[mac] = now
                    log_bt_csv(mac, name)
                    if mac not in bt_blips:
                        bt_blips[mac] = (
                            random.randint(-14,14),
                            random.randint(-14,14)
                        )
        except:
            pass

        for mac in list(bt_last_seen):
            if time.time() - bt_last_seen[mac] > 15:
                bt_last_seen.pop(mac, None)

        with lock:
            bt_now = len(bt_last_seen)
            bt_total = len(seen_bt)

        time.sleep(3)

threading.Thread(target=wifi_scanner, daemon=True).start()
threading.Thread(target=bt_scanner, daemon=True).start()

# =====================
# Radar
# =====================
def draw_radar(draw, angle):
    cx, cy, r = 64, 32, 28
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=255)
    draw.line((cx, cy,
               cx+int(r*math.cos(angle)),
               cy+int(r*math.sin(angle))), fill=255)
    for bx, by in bt_blips.values():
        draw.ellipse((cx+bx-2, cy+by-2, cx+bx+2, cy+by+2), fill=255)

# =====================
# Main loop
# =====================
angle = 0

try:
    while True:
        now = time.time()

        if now - last_button > DEBOUNCE:
            if pressed(BTN_K1):
                menu_index = (menu_index - 1) % len(MENU_ITEMS)
                last_button = now
            elif pressed(BTN_K2):
                menu_index = (menu_index + 1) % len(MENU_ITEMS)
                last_button = now
            elif pressed(BTN_K3):
                item = MENU_ITEMS[menu_index]
                if item == "WiFi Scan":
                    wifi_enabled = not wifi_enabled
                elif item == "Bluetooth Scan":
                    bt_enabled = not bt_enabled
                elif item == "Logging":
                    logging_enabled = not logging_enabled
                elif item == "Clear WiFi":
                    seen_wifi.clear()
                elif item == "Clear BT":
                    seen_bt.clear()
                    bt_last_seen.clear()
                last_button = now
            elif pressed(BTN_K4):
                menu_index = 0
                last_button = now

        with lock:
            w_now, w_tot = wifi_now, wifi_total
            b_now, b_tot = bt_now, bt_total
            ssids = list(seen_wifi.values())
            bts = list(seen_bt.values())

        # LEFT OLED — telemetry
        with canvas(oled_left) as d:
            d.text((0,0), f"WiFi {w_now}/{w_tot} {'ON' if wifi_enabled else 'OFF'}", fill=255)
            d.text((0,10), f"BT   {b_now}/{b_tot} {'ON' if bt_enabled else 'OFF'}", fill=255)
            d.text((0,20), f"CPU {psutil.cpu_percent():.0f}% {get_cpu_temp()}", fill=255)
            d.text((0,30), f"UP {get_uptime()}", fill=255)
            d.text((0,40), get_sd_health(), fill=255)
            d.text((0,50), f"LOG {'ON' if logging_enabled else 'OFF'} v{VERSION}", fill=255)

        # RIGHT OLED — controls + radar
        with canvas(oled_right) as d:
            d.text((0,0), "CTRL", fill=255)
            y = 10
            for i, item in enumerate(MENU_ITEMS):
                prefix = ">" if i == menu_index else " "
                state = ""
                if item == "WiFi Scan":
                    state = "ON" if wifi_enabled else "OFF"
                elif item == "Bluetooth Scan":
                    state = "ON" if bt_enabled else "OFF"
                elif item == "Logging":
                    state = "ON" if logging_enabled else "OFF"
                d.text((0,y), f"{prefix}{item[:12]} {state}", fill=255)
                y += 10

            draw_radar(d, angle)

        angle += 0.15
        time.sleep(0.2)

except KeyboardInterrupt:
    GPIO.cleanup()
