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

# ================= OLED SETUP =================
serial_left = i2c(port=1, address=0x3C)
serial_right = i2c(port=1, address=0x3D)

oled_left = ssd1306(serial_left)
oled_right = ssd1306(serial_right)

# ================= SHARED DATA =================
wifi_now = 0
wifi_total = 0
bt_now = 0
bt_total = 0

seen_wifi = set()
seen_bt = set()

current_wifi = []
current_bt = []

bt_blip = False
bt_blip_time = 0

lock = threading.Lock()

# ================= SYSTEM INFO =================
def get_ip():
    try:
        ip = subprocess.check_output("hostname -I", shell=True).decode().strip()
        return ip if ip else "No IP"
    except:
        return "No IP"

def get_cpu_temp():
    try:
        out = subprocess.check_output("vcgencmd measure_temp", shell=True).decode()
        c = float(out.replace("temp=", "").replace("'C\n", ""))
        return f"{(c*9/5)+32:.1f}F"
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
        out = subprocess.check_output("vcgencmd measure_volts", shell=True).decode()
        volts = out.split("=")[1].replace("V","")
        return f"{float(volts):.2f}V"
    except:
        return "?"

# ================= WIFI SCANNER =================
def wifi_scanner():
    global wifi_now, wifi_total
    while True:
        local_wifi = []
        try:
            result = subprocess.check_output(
                "sudo iwlist wlan0 scan 2>/dev/null | grep ESSID",
                shell=True
            ).decode()

            count = 0
            for line in result.splitlines():
                ssid = line.split("ESSID:")[1].replace('"','').strip()
                if ssid:
                    seen_wifi.add(ssid)
                    local_wifi.append(ssid)
                    count += 1

            with lock:
                wifi_now = count
                wifi_total = len(seen_wifi)
                current_wifi.clear()
                current_wifi.extend(local_wifi)
        except:
            pass

        time.sleep(5)

# ================= BLUETOOTH SCANNER =================
def bt_scanner():
    global bt_now, bt_total, bt_blip, bt_blip_time
    while True:
        local_bt = {}
        try:
            cmd = "echo -e 'scan on\ndevices\nscan off' | bluetoothctl"
            out = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode()

            for line in out.splitlines():
                if line.startswith("Device"):
                    parts = line.split(maxsplit=2)
                    mac = parts[1]
                    name = parts[2] if len(parts) == 3 else mac
                    local_bt[mac] = name

                    if mac not in seen_bt:
                        bt_blip = True
                        bt_blip_time = time.time()

                    seen_bt.add(mac)
        except:
            pass

        with lock:
            current_bt.clear()
            current_bt.extend(local_bt.values())
            bt_now = len(local_bt)
            bt_total = len(seen_bt)

        time.sleep(5)

# ================= START THREADS =================
threading.Thread(target=wifi_scanner, daemon=True).start()
threading.Thread(target=bt_scanner, daemon=True).start()

# ================= ICONS =================
def draw_wifi_icon(draw, x, y):
    for i in range(4):
        draw.line((x+i, y+6, x+4+i, y+2), fill=255)
    draw.rectangle((x+3, y+7, x+4, y+8), fill=255)

def draw_bt_icon(draw, x, y):
    draw.line((x, y, x+3, y+3), fill=255)
    draw.line((x+3, y+3, x, y+6), fill=255)
    draw.line((x, y, x+3, y+6), fill=255)

# ================= RADAR DRAW =================
def draw_radar(draw, angle, show_blip):
    cx, cy, r = 64, 32, 28
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=255)

    x = cx + int(r * math.cos(angle))
    y = cy + int(r * math.sin(angle))
    draw.line((cx, cy, x, y), fill=255)

    if show_blip:
        draw.ellipse((cx+14, cy-3, cx+18, cy+3), fill=255)

# ================= DISPLAY LOOP =================
mode = "info"
mode_time = time.time()
sweep = 0.0

while True:
    now = time.time()

    if mode == "info" and now - mode_time > 15:
        mode = "radar"
        mode_time = now
    elif mode == "radar" and now - mode_time > 5:
        mode = "info"
        mode_time = now

    with lock:
        w_now, w_total = wifi_now, wifi_total
        b_now, b_total = bt_now, bt_total
        ssid = random.choice(current_wifi) if current_wifi else "---"
        bt_name = random.choice(current_bt) if current_bt else "---"

    ip = get_ip()
    cpu = psutil.cpu_percent(interval=0.3)
    temp = get_cpu_temp()
    uptime = get_uptime()
    usbv = get_usb_voltage()

    # ================= INFO MODE =================
    if mode == "info":
        with canvas(oled_left) as draw:
            draw.text((0,0),  "User: jleary53", fill=255)
            draw.text((0,10), f"Temp: {temp}", fill=255)
            draw.text((0,20), f"CPU: {cpu:.1f}%", fill=255)
            draw.text((0,30), f"IP: {ip}", fill=255)
            draw.text((0,40), f"Up: {uptime}", fill=255)
            draw.text((0,50), f"V: {usbv}", fill=255)

        with canvas(oled_right) as draw:
            draw.text((0,0), "Mode: Wardrive", fill=255)
            draw_wifi_icon(draw, 0, 10)
            draw.text((10,10), f"WiFi {w_now}/{w_total}", fill=255)
            draw_bt_icon(draw, 0, 30)
            draw.text((10,30), f"BT {b_now}/{b_total}", fill=255)

    # ================= RADAR MODE =================
    else:
        sweep += 0.2

        show_blip = False
        if bt_blip and time.time() - bt_blip_time < 2:
            show_blip = True
        else:
            bt_blip = False

        with canvas(oled_left) as draw:
            draw.text((0,0), "WiFi Scan", fill=255)
            draw.text((0,12), ssid[:14], fill=255)

        with canvas(oled_right) as draw:
            draw.text((0,0), "BT Radar", fill=255)
            draw_radar(draw, sweep, show_blip)
            if show_blip:
                draw.text((0,52), bt_name[:14], fill=255)

    time.sleep(0.1)
