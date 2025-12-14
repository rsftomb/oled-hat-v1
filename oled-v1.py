#!/usr/bin/env python3
import time
import psutil
import subprocess
import threading
import random
import math
from datetime import timedelta

import RPi.GPIO as GPIO

from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas

# =====================
# Version
# =====================
VERSION = "v1.24"

# =====================
# OLED setup
# =====================
serial_left = i2c(port=1, address=0x3C)
serial_right = i2c(port=1, address=0x3D)

oled_left = ssd1306(serial_left)
oled_right = ssd1306(serial_right)

# =====================
# Waveshare buttons
# =====================
BTN_K1 = 5    # UP
BTN_K2 = 6    # DOWN
BTN_K3 = 16   # SELECT
BTN_K4 = 24   # BACK

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for btn in (BTN_K1, BTN_K2, BTN_K3, BTN_K4):
    GPIO.setup(btn, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# =====================
# Shared state
# =====================
wifi_now = 0
wifi_total = 0
bt_now = 0
bt_total = 0

seen_wifi = set()
seen_bt = {}          # mac -> name
bt_last_seen = {}     # mac -> timestamp
bt_blips = {}         # mac -> (x,y)

lock = threading.Lock()

# =====================
# Menu state
# =====================
MENU_ITEMS = ["Dashboard", "WiFi Scan", "Bluetooth Scan"]
menu_index = 0
current_screen = "Dashboard"

last_button_time = 0
BUTTON_DELAY = 0.25

# =====================
# Helpers
# =====================
def button_pressed(pin):
    return GPIO.input(pin) == GPIO.LOW

def get_ip():
    try:
        return subprocess.check_output("hostname -I", shell=True).decode().strip()
    except:
        return "No IP"

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

def get_usb_voltage():
    try:
        v = subprocess.check_output("vcgencmd measure_volts", shell=True).decode()
        return v.split("=")[1].strip()
    except:
        return "?"

# =====================
# Wi-Fi scanner
# =====================
def wifi_scanner():
    global wifi_now, wifi_total
    while True:
        current = []
        try:
            out = subprocess.check_output(
                "sudo iwlist wlan0 scan 2>/dev/null | grep ESSID",
                shell=True
            ).decode()
            for line in out.splitlines():
                ssid = line.split("ESSID:")[1].replace('"','').strip()
                if ssid:
                    current.append(ssid)
                    seen_wifi.add(ssid)
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

    subprocess.Popen(
        "bluetoothctl scan on",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    while True:
        try:
            out = subprocess.check_output(
                "bluetoothctl devices",
                shell=True
            ).decode()

            now_ts = time.time()

            for line in out.splitlines():
                if line.startswith("Device"):
                    parts = line.split(maxsplit=2)
                    mac = parts[1]
                    name = parts[2] if len(parts) == 3 else "Unknown"

                    seen_bt[mac] = name
                    bt_last_seen[mac] = now_ts

                    if mac not in bt_blips:
                        bt_blips[mac] = (
                            random.randint(-14, 14),
                            random.randint(-14, 14)
                        )
        except:
            pass

        for mac in list(bt_last_seen.keys()):
            if time.time() - bt_last_seen[mac] > 15:
                bt_last_seen.pop(mac, None)

        with lock:
            bt_now = len(bt_last_seen)
            bt_total = len(seen_bt)

        time.sleep(3)

# =====================
# Start threads
# =====================
threading.Thread(target=wifi_scanner, daemon=True).start()
threading.Thread(target=bt_scanner, daemon=True).start()

# =====================
# Graphics
# =====================
def draw_wifi_bars(draw, level):
    x = 0
    base = 55
    for i in range(4):
        h = (i + 1) * 6
        if i < level:
            draw.rectangle((x+i*10, base-h, x+i*10+6, base), fill=255)
        else:
            draw.rectangle((x+i*10, base-h, x+i*10+6, base), outline=255)

def draw_radar(draw, angle, blips):
    cx, cy, r = 70, 32, 28
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=255)

    x = cx + int(r * math.cos(angle))
    y = cy + int(r * math.sin(angle))
    draw.line((cx, cy, x, y), fill=255)

    for bx, by in blips:
        draw.ellipse((cx+bx-2, cy+by-2, cx+bx+2, cy+by+2), fill=255)

# =====================
# Main loop
# =====================
radar_mode = True
mode_time = time.time()
angle = 0

try:
    while True:
        now = time.time()

        # -------- Buttons --------
        if now - last_button_time > BUTTON_DELAY:
            if button_pressed(BTN_K1):
                menu_index = (menu_index - 1) % len(MENU_ITEMS)
                last_button_time = now

            elif button_pressed(BTN_K2):
                menu_index = (menu_index + 1) % len(MENU_ITEMS)
                last_button_time = now

            elif button_pressed(BTN_K3):
                current_screen = MENU_ITEMS[menu_index]
                last_button_time = now

            elif button_pressed(BTN_K4):
                current_screen = "Dashboard"
                last_button_time = now

        # -------- Mode timing --------
        if radar_mode and now - mode_time > 5:
            radar_mode = False
            mode_time = now
        elif not radar_mode and now - mode_time > 10:
            radar_mode = True
            mode_time = now

        with lock:
            w_now = wifi_now
            w_total = wifi_total
            b_now = bt_now
            b_total = bt_total
            blips = list(bt_blips.values())
            ssids = list(seen_wifi)
            bt_names = list(seen_bt.values())

        # -------- LEFT OLED --------
        with canvas(oled_left) as draw:
            draw.text((0, 0), "WiGLE: jleary53", fill=255)
            draw.text((0,10), f"Temp: {get_cpu_temp()}", fill=255)
            draw.text((0,20), f"CPU: {psutil.cpu_percent():.1f}%", fill=255)
            draw.text((0,30), f"Up: {get_uptime()}", fill=255)
            draw.text((0,40), f"Volt: {get_usb_voltage()}", fill=255)
            draw.text((0,50), f"Version: {VERSION}", fill=255)

        # -------- RIGHT OLED --------
        with canvas(oled_right) as draw:
            draw.text((0, 0), f">{MENU_ITEMS[menu_index]}", fill=255)

            if current_screen == "Dashboard":
                if radar_mode:
                    draw.text((0,10), "Radar", fill=255)
                    draw_radar(draw, angle, blips)
                    draw_wifi_bars(draw, w_now % 5)
                else:
                    draw.text((0,10), f"WiFi: {w_now}/{w_total}", fill=255)
                    draw.text((0,20), f"BT: {b_now}/{b_total}", fill=255)
                    draw.text((0,30), f"IP: {get_ip()}", fill=255)

            elif current_screen == "WiFi Scan":
                draw.text((0,10), f"Now: {w_now}", fill=255)
                draw.text((0,20), f"Total: {w_total}", fill=255)
                y = 30
                for ssid in ssids[-3:]:
                    draw.text((0, y), ssid[:16], fill=255)
                    y += 10

            elif current_screen == "Bluetooth Scan":
                draw.text((0,10), f"Now: {b_now}", fill=255)
                draw.text((0,20), f"Total: {b_total}", fill=255)
                y = 30
                for name in bt_names[-3:]:
                    draw.text((0, y), name[:16], fill=255)
                    y += 10

        angle += 0.15
        time.sleep(0.2)

except KeyboardInterrupt:
    GPIO.cleanup()
