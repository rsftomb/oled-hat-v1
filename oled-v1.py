#!/usr/bin/env python3
import time
import psutil
import subprocess
import threading
import random
import math
from datetime import timedelta
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas

# =====================
# Version (manual edit)
# =====================
VERSION = "1215.01"

# =====================
# OLED setup
# =====================
serial_left = i2c(port=1, address=0x3C)
serial_right = i2c(port=1, address=0x3D)

oled_left = ssd1306(serial_left)
oled_right = ssd1306(serial_right)

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
# Helpers
# =====================
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

        # prune stale devices
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
# Animations
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
# Display loop
# =====================
radar_mode = True
mode_time = time.time()
angle = 0
scroll_pos = 0

while True:
    now = time.time()

    # mode timing
    if radar_mode and now - mode_time > 6:
        radar_mode = False
        mode_time = now
    elif not radar_mode and now - mode_time > 14:
        radar_mode = True
        mode_time = now

    with lock:
        w_now = wifi_now
        w_total = wifi_total
        b_now = bt_now
        b_total = bt_total
        blips = list(bt_blips.values())

        rand_ssid = random.choice(list(seen_wifi)) if seen_wifi else "None"
        rand_bt = random.choice(list(seen_bt.values())) if seen_bt else "None"

    # LEFT OLED
    with canvas(oled_left) as draw:
        draw.text((0, 0), "WiGLE: jleary53", fill=255)
        draw.text((0,10), f"Temp: {get_cpu_temp()}", fill=255)
        draw.text((0,20), f"CPU: {psutil.cpu_percent():.1f}%", fill=255)
        draw.text((0,30), f"Up: {get_uptime()}", fill=255)
        try:
            u = psutil.disk_usage("/")
            free = u.free / (1024**3)
            sd_health = f"SD Use {u.percent:.0f}% {free:.1f}G"
        except:
            sd_health = "SD ERR"
        draw.text((0,40), sd_health, fill=255)
        draw.text((0,50), f"Build#: {VERSION}", fill=255)

    # RIGHT OLED
    with canvas(oled_right) as draw:
        if radar_mode:
            draw.text((0,0), "Radar", fill=255)
            draw_radar(draw, angle, blips)
            draw_wifi_bars(draw, w_now % 5)
        else:
            # Wi-Fi
            wifi_line = f"WiFi Now:{w_now} T:{w_total}"
            if len(wifi_line) > 20:
                wifi_line = wifi_line[:20] + "..."
            draw.text((0,0), wifi_line, fill=255)

            # Bluetooth
            bt_line = f"BT Now: {b_now} T: {b_total}"
            if len(bt_line) > 20:
                bt_line = bt_line[:20] + "..."
            draw.text((0,10), bt_line, fill=255)

            # IP
            ip_str = f"IP: {get_ip()}"
            if len(ip_str) > 20:
                ip_str = ip_str[:20] + "..."
            draw.text((0,20), ip_str, fill=255)

            # Random SSID
            ssid_str = f"SSID: {rand_ssid[:16]}"
            draw.text((0,30), ssid_str, fill=255)

            # Random BT
            bt_str = f"Bluetooth: {rand_bt[:16]}"
            draw.text((0,40), bt_str, fill=255)

            # Mode scrolling
            mode_text = "WarPi.G Zero2W "
            display_text = mode_text[scroll_pos:] + mode_text[:scroll_pos]
            draw.text((0,50), display_text[:20], fill=255)
            scroll_pos = (scroll_pos + 1) % len(mode_text)

    angle += 0.15
    time.sleep(0.2)
