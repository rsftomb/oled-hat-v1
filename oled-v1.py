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

VERSION = "v1.22"

# OLED setup
serial_left = i2c(port=1, address=0x3C)
serial_right = i2c(port=1, address=0x3D)

oled_left = ssd1306(serial_left)
oled_right = ssd1306(serial_right)

# Shared data
wifi_now = 0
wifi_total = 0
bt_now = 0
bt_total = 0

seen_wifi = set()
seen_bt = {}      # mac -> name
bt_blips = []     # radar blip offsets

lock = threading.Lock()

# Helpers
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

# Wi-Fi scanner
def wifi_scanner():
    global wifi_now, wifi_total
    while True:
        try:
            out = subprocess.check_output(
                "sudo iwlist wlan0 scan 2>/dev/null | grep ESSID",
                shell=True
            ).decode()
            current = []
            for line in out.splitlines():
                ssid = line.split("ESSID:")[1].replace('"','').strip()
                if ssid:
                    current.append(ssid)
                    seen_wifi.add(ssid)
            with lock:
                wifi_now = len(current)
                wifi_total = len(seen_wifi)
        except:
            pass
        time.sleep(5)

# Bluetooth scanner (btmgmt)
def bt_scanner():
    global bt_now, bt_total, bt_blips
    while True:
        current = {}
        blips = []
        try:
            out = subprocess.check_output(
                "timeout 5s sudo btmgmt find",
                shell=True,
                stderr=subprocess.DEVNULL
            ).decode()

            for line in out.splitlines():
                if "dev_found" in line:
                    parts = line.split()
                    mac = next((p for p in parts if ":" in p and len(p.split(":"))==6), None)
                    name = "Unknown"
                    if "name" in parts:
                        name = " ".join(parts[parts.index("name")+1:])
                    if mac:
                        current[mac] = name
                        seen_bt[mac] = name
                        blips.append((
                            random.randint(-15,15),
                            random.randint(-15,15)
                        ))
        except:
            pass

        with lock:
            bt_now = len(current)
            bt_total = len(seen_bt)
            bt_blips = blips

        time.sleep(5)

# Threads
threading.Thread(target=wifi_scanner, daemon=True).start()
threading.Thread(target=bt_scanner, daemon=True).start()

# Animations
def draw_wifi_bars(draw, level):
    x = 0
    base = 55
    for i in range(4):
        h = (i+1)*6
        if i < level:
            draw.rectangle((x+i*10, base-h, x+i*10+6, base), fill=255)
        else:
            draw.rectangle((x+i*10, base-h, x+i*10+6, base), outline=255)

def draw_radar(draw, angle, blips):
    cx, cy, r = 68, 32, 28   # shifted right from 64 → 68
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=255)
    x = cx + int(r*math.cos(angle))
    y = cy + int(r*math.sin(angle))
    draw.line((cx,cy,x,y), fill=255)
    for bx,by in blips:
        draw.ellipse((cx+bx-2, cy+by-2, cx+bx+2, cy+by+2), fill=255)

# Display cycle
radar_mode = True
mode_time = time.time()
angle = 0

while True:
    now = time.time()
    if now - mode_time > 5:
        radar_mode = not radar_mode
        mode_time = now

    with lock:
        w_now, w_total = wifi_now, wifi_total
        b_now, b_total = bt_now, bt_total
        blips = list(bt_blips)
        rand_ssid = random.choice(list(seen_wifi)) if seen_wifi else "None"
        rand_bt = random.choice(list(seen_bt.values())) if seen_bt else "None"

    # LEFT display
    with canvas(oled_left) as draw:
        draw.text((0,0), "User: jleary53", fill=255)
        draw.text((0,10), f"Temp: {get_cpu_temp()}", fill=255)
        draw.text((0,20), f"CPU: {psutil.cpu_percent():.1f}%", fill=255)
        draw.text((0,30), f"Up: {get_uptime()}", fill=255)
        draw.text((0,40), f"Volt: {get_usb_voltage()}", fill=255)
        draw.text((0,50), f"Ver: {version}", fill=255)

    # RIGHT display
    with canvas(oled_right) as draw:
        if radar_mode:
            draw_radar(draw, angle, blips)
            draw_wifi_bars(draw, w_now % 5)
            draw.text((0,0), "Radar", fill=255)
        else:
            draw.text((0,0), f"WiFi: {w_now}/{w_total}", fill=255)
            draw.text((0,10), f"BT: {b_now}/{b_total}", fill=255)
            draw.text((0,20), f"IP: {get_ip()}", fill=255)
            draw.text((0,30), f"SSID: {rand_ssid[:16]}", fill=255)
            draw.text((0,40), f"BTdev: {rand_bt[:16]}", fill=255)

    angle += 0.2
    time.sleep(0.2)
