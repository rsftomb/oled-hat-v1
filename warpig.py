#!/usr/bin/env python3
import time
import psutil
import subprocess
import threading
import random
import math
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import timedelta
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas

# =====================
# Version
# =====================
VERSION = "1223.02 WebUI"

# =====================
# OLED setup
# =====================
serial_left  = i2c(port=1, address=0x3C)
serial_right = i2c(port=1, address=0x3D)

oled_left  = ssd1306(serial_left)
oled_right = ssd1306(serial_right)

# =====================
# Boot screen
# =====================
def show_boot_screen():
    stages = [
        ("Init Core.", 25),
        ("Init WiFi..", 45),
        ("Init BT...", 60),
        ("Booting WarPi.G....", 85),
        ("Starting WebUI.....", 100),
    ]

    for label, pct in stages:
        for step in range(0, pct + 1, 5):
            with canvas(oled_left) as d:
                d.text((0, 8), "WarPi.G", fill=255)
                d.text((0, 22), label, fill=255)
                d.rectangle((0, 44, 120, 52), outline=255)
                d.rectangle((0, 44, int(step * 1.2), 52), fill=255)

            with canvas(oled_right) as d:
                d.text((0, 20), "Updating...", fill=255)
                d.text((0, 36), f"Build# {VERSION}", fill=255)

            time.sleep(0.04)
    time.sleep(0.4)

# =====================
# Shared state
# =====================
wifi_now = wifi_total = 0
bt_now = bt_total = 0

wifi_seen = {}
wifi_last_seen = {}
wifi_blips = {}

seen_bt = {}
bt_last_seen = {}

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

def rssi_to_radius(rssi, max_r=26):
    rssi = max(-90, min(-30, rssi))
    return int(((abs(rssi) - 30) / 60) * max_r)

# =====================
# Web status server
# =====================
def start_web_status_server():
    class StatusHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/status":
                self.send_response(404)
                self.end_headers()
                return

            with lock:
                data = {
                    "version": VERSION,
                    "wifi_now": wifi_now,
                    "wifi_total": wifi_total,
                    "wifi_seen": list(wifi_seen.keys()),
                    "bt_now": bt_now,
                    "bt_total": bt_total,
                    "bt_seen": list(seen_bt.values()),
                    "ip": get_ip(),
                    "cpu": psutil.cpu_percent(),
                    "temp": get_cpu_temp(),
                    "uptime": get_uptime(),
                }

            payload = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)

        # Disable logging to console
        def log_message(self, format, *args):
            return

    try:
        HTTPServer(("0.0.0.0", 8081), StatusHandler).serve_forever()
    except Exception as e:
        print("Web server failed to start:", e)

# =====================
# Wi-Fi scanner (radar source)
# =====================
def wifi_scanner():
    global wifi_now, wifi_total

    STALE_TIME = 15
    MAX_BLIPS = 3

    while True:
        now_ts = time.time()
        current = set()

        try:
            out = subprocess.check_output(
                "sudo iwlist wlan0 scan 2>/dev/null | egrep 'ESSID|Signal level'",
                shell=True
            ).decode().splitlines()

            ssid = None

            for line in out:
                if "ESSID" in line:
                    ssid = line.split("ESSID:")[1].replace('"','').strip()

                elif "Signal level" in line and ssid:
                    try:
                        rssi = int(line.split("Signal level=")[1].split(" ")[0])
                    except:
                        rssi = -80

                    current.add(ssid)
                    wifi_seen[ssid] = True
                    wifi_last_seen[ssid] = now_ts

                    if ssid not in wifi_blips:
                        if len(wifi_blips) >= MAX_BLIPS:
                            oldest = min(wifi_last_seen, key=wifi_last_seen.get)
                            wifi_blips.pop(oldest, None)
                            wifi_last_seen.pop(oldest, None)

                        wifi_blips[ssid] = {
                            "angle": random.uniform(0, 2 * math.pi),
                            "r": rssi_to_radius(rssi),
                            "hit": 0
                        }

                    ssid = None

        except:
            pass

        for s in list(wifi_last_seen):
            if now_ts - wifi_last_seen[s] > STALE_TIME:
                wifi_last_seen.pop(s, None)
                wifi_blips.pop(s, None)

        with lock:
            wifi_now = len(current)
            wifi_total = len(wifi_seen)

        time.sleep(5)

# =====================
# Bluetooth scanner (stats only)
# =====================
def bt_scanner():
    global bt_now, bt_total

    subprocess.Popen("bluetoothctl scan on", shell=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    while True:
        try:
            out = subprocess.check_output("bluetoothctl devices", shell=True).decode()
            now = time.time()

            for line in out.splitlines():
                if line.startswith("Device"):
                    parts = line.split(maxsplit=2)
                    mac = parts[1]
                    name = parts[2] if len(parts) == 3 else "Unknown"
                    seen_bt[mac] = name
                    bt_last_seen[mac] = now
        except:
            pass

        for mac in list(bt_last_seen):
            if time.time() - bt_last_seen[mac] > 15:
                bt_last_seen.pop(mac, None)

        with lock:
            bt_now = len(bt_last_seen)
            bt_total = len(seen_bt)

        time.sleep(3)

# =====================
# Radar drawing
# =====================
def draw_radar(draw, sweep_angle):
    cx, cy, r = 70, 32, 28
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=255)

    sx = cx + int(r * math.cos(sweep_angle))
    sy = cy + int(r * math.sin(sweep_angle))
    draw.line((cx, cy, sx, sy), fill=255)

    now = time.time()
    with lock:
        blips = dict(wifi_blips)

    for data in blips.values():
        bx = cx + int(data["r"] * math.cos(data["angle"]))
        by = cy + int(data["r"] * math.sin(data["angle"]))

        if abs((sweep_angle - data["angle"] + math.pi) % (2*math.pi) - math.pi) < 0.15:
            data["hit"] = now

        if now - data["hit"] < 0.3:
            draw.ellipse((bx-3, by-3, bx+3, by+3), fill=255)
        else:
            draw.ellipse((bx-2, by-2, bx+2, by+2), outline=255)

# =====================
# Boot + threads
# =====================
show_boot_screen()
threading.Thread(target=wifi_scanner, daemon=True).start()
threading.Thread(target=bt_scanner, daemon=True).start()
threading.Thread(target=start_web_status_server, daemon=True).start()

# =====================
# Main loop
# =====================
radar_mode = True
mode_time = time.time()
angle = 0
scroll_pos = 0

while True:
    now = time.time()

    if radar_mode and now - mode_time > 7:
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
        rand_ssid = random.choice(list(wifi_seen)) if wifi_seen else "None"
        rand_bt   = random.choice(list(seen_bt.values())) if seen_bt else "None"

    with canvas(oled_left) as d:
        d.text((0, 0), "WiGLE: jleary53", fill=255)
        d.text((0,10), f"Temp: {get_cpu_temp()}", fill=255)
        d.text((0,20), f"CPU: {psutil.cpu_percent():.1f}%", fill=255)
        d.text((0,30), f"Up: {get_uptime()}", fill=255)
        d.text((0,40), f"IP: {get_ip()[:16]}", fill=255)
        d.text((0,50), f"Build: {VERSION}", fill=255)

    with canvas(oled_right) as d:
        if radar_mode:
            d.text((0,0), "WiFi -dB", fill=255)
            draw_radar(d, angle)
        else:
            d.text((0,0), f"WiFi Now:{w_now} Tot:{w_total}", fill=255)
            d.text((0,10), f"BT Now:{b_now} Tot:{b_total}", fill=255)
            d.text((0,30), f"SSID: {rand_ssid[:14]}", fill=255)
            d.text((0,40), f"BT Dev: {rand_bt[:14]}", fill=255)
            d.text((0,20), get_ip()[:20], fill=255)
            mode = "WarPi.G Zero2W   "
            text = mode[scroll_pos:] + mode[:scroll_pos]
            d.text((0,50), text[:20], fill=255)
            scroll_pos = (scroll_pos + 1) % len(mode)

    angle += 0.12
    time.sleep(0.2)
