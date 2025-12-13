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

VERSION = "v1.1"

# ---------------------------
# OLED setup
# ---------------------------
serial_left = i2c(port=1, address=0x3C)
serial_right = i2c(port=1, address=0x3D)

oled_left = ssd1306(serial_left)
oled_right = ssd1306(serial_right)

# ---------------------------
# Shared data
# ---------------------------
wifi_now = 0
wifi_total = 0
bt_now = 0
bt_total = 0
random_ssid = "N/A"
random_bt_name = "N/A"
bt_devices = []  # List of tuples: (mac, name)
bt_signals = {}  # Dict of mac -> pseudo signal strength

seen_wifi = set()
seen_bt = set()

lock = threading.Lock()

# ---------------------------
# System info helpers
# ---------------------------
def get_ip():
    try:
        ip = subprocess.check_output("hostname -I", shell=True).decode().strip()
        return ip if ip else "No IP"
    except:
        return "No IP"

def get_cpu_temp():
    try:
        temp_c = subprocess.check_output("vcgencmd measure_temp", shell=True).decode()
        temp_c = float(temp_c.replace("temp=", "").replace("'C\n", ""))
        temp_f = (temp_c * 9/5) + 32
        return f"{temp_f:.1f}F"
    except:
        return "?"

def get_uptime():
    try:
        seconds = float(open("/proc/uptime").read().split()[0])
        return str(timedelta(seconds=int(seconds)))
    except:
        return "?"

def get_usb_voltage():
    try:
        output = subprocess.check_output("vcgencmd measure_volts", shell=True).decode().strip()
        volts = output.split('=')[1].replace('V','')
        return f"{float(volts):.2f}V"
    except:
        return "?"

# ---------------------------
# Wi-Fi scanner thread
# ---------------------------
def wifi_scanner():
    global wifi_now, wifi_total, random_ssid
    while True:
        try:
            result = subprocess.check_output(
                "sudo iwlist wlan0 scan 2>/dev/null | grep ESSID",
                shell=True
            ).decode()
            count = 0
            ssids = []
            for line in result.splitlines():
                ssid = line.split("ESSID:")[1].replace('"','').strip()
                if ssid:
                    seen_wifi.add(ssid)
                    ssids.append(ssid)
                    count += 1
            with lock:
                wifi_now = count
                wifi_total = len(seen_wifi)
                if ssids:
                    random_ssid = random.choice(ssids)
        except:
            with lock:
                wifi_now = 0
                random_ssid = "N/A"
        time.sleep(5)

# ---------------------------
# Bluetooth scanner thread
# ---------------------------
def bt_scanner():
    global bt_now, bt_total, random_bt_name, bt_devices, bt_signals
    while True:
        current = []
        names = []
        signals = {}
        try:
            scan_cmds = """
echo -e 'scan on\ndevices\nscan off' | bluetoothctl
"""
            output = subprocess.check_output(scan_cmds, shell=True, stderr=subprocess.DEVNULL).decode()
            for line in output.splitlines():
                if line.startswith("Device"):
                    parts = line.strip().split(maxsplit=2)
                    mac = parts[1]
                    name = parts[2] if len(parts) >= 3 else mac
                    current.append((mac, name))
                    seen_bt.add((mac, name))
                    names.append(name)
                    signals[mac] = random.randint(5,28)  # pseudo-distance/signal
            with lock:
                bt_now = len(current)
                bt_total = len(seen_bt)
                bt_devices = current.copy()
                bt_signals = signals.copy()
                if names:
                    random_bt_name = random.choice(names)
        except:
            with lock:
                bt_now = 0
                random_bt_name = "N/A"
                bt_devices = []
                bt_signals = {}
        time.sleep(5)

# ---------------------------
# Start scanner threads
# ---------------------------
threading.Thread(target=wifi_scanner, daemon=True).start()
threading.Thread(target=bt_scanner, daemon=True).start()

# ---------------------------
# Icon drawing functions
# ---------------------------
def draw_wifi_icon(draw, x, y):
    draw.line((x, y+6, x+4, y+2), fill=255)
    draw.line((x+1, y+6, x+5, y+2), fill=255)
    draw.line((x+2, y+6, x+6, y+2), fill=255)
    draw.line((x+3, y+6, x+7, y+2), fill=255)
    draw.rectangle((x+3, y+7, x+4, y+8), fill=255)

def draw_bt_icon(draw, x, y):
    draw.line((x, y, x+3, y+3), fill=255)
    draw.line((x+3, y+3, x, y+6), fill=255)
    draw.line((x, y, x+3, y+6), fill=255)
    draw.line((x, y+3, x+3, y+3), fill=255)

# Radar + Wi-Fi animation frames
def draw_wifi_bars(draw, level):
    x = 0
    base_y = 50
    for i in range(4):
        height = (i + 1) * 6
        if i < level:
            draw.rectangle((x + i*10, base_y - height, x + i*10 + 6, base_y), fill=255)
        else:
            draw.rectangle((x + i*10, base_y - height, x + i*10 + 6, base_y), outline=255)

def draw_radar(draw, sweep_angle, devices, signals):
    cx, cy = 64, 32
    r = 28
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=255)
    x = cx + int(r * math.cos(sweep_angle))
    y = cy + int(r * math.sin(sweep_angle))
    draw.line((cx, cy, x, y), fill=255)
    for mac, name in devices:
        distance = signals.get(mac, random.randint(5,28))
        angle = random.uniform(0, 2*math.pi)
        bx = int(cx + distance * math.cos(angle))
        by = int(cy + distance * math.sin(angle))
        draw.ellipse((bx-2, by-2, bx+2, by+2), fill=255)
        draw.text((bx+3, by-3), name[:6], fill=255)

# ---------------------------
# Main OLED loop
# ---------------------------
sweep_angle = 0.0
radar_increment = math.pi / 30

while True:
    with lock:
        w_now, w_total = wifi_now, wifi_total
        b_now, b_total = bt_now, bt_total
        ssid_display = random_ssid
        bt_display = random_bt_name
        devices = bt_devices.copy()
        signals = bt_signals.copy()

    ip = get_ip()
    cpu = psutil.cpu_percent(interval=0.5)
    temp = get_cpu_temp()
    uptime = get_uptime()
    usbv = get_usb_voltage()

    # LEFT OLED
    with canvas(oled_left) as draw:
        draw.text((0, 0), f"User: jleary53", fill=255)
        draw.text((0,10), f"Version: {VERSION}", fill=255)
        draw.text((0,20), f"Temp: {temp}", fill=255)
        draw.text((0,30), f"CPU: {cpu:.1f}%", fill=255)
        draw.text((0,40), f"IP: {ip}", fill=255)
        draw.text((0,50), f"Uptime: {uptime}", fill=255)
        draw.text((0,60), f"Batt: {usbv}", fill=255)
        draw.text((0,70), f"SSID: {ssid_display}", fill=255)

    # RIGHT OLED
    with canvas(oled_right) as draw:
        draw.text((0,0), "Mode: Wardrive", fill=255)
        draw_wifi_bars(draw, w_now % 5)
        draw_radar(draw, sweep_angle, devices, signals)
        draw_bt_icon(draw, 0, 55)
        draw.text((10,55), f"BT: {bt_display}", fill=255)
        draw.text((10,65), f"BT Now: {b_now} Tot: {b_total}", fill=255)

    sweep_angle += radar_increment
    if sweep_angle > 2*math.pi:
        sweep_angle -= 2*math.pi

    time.sleep(0.1)
