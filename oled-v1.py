#!/usr/bin/env python3
import time
import psutil
import subprocess
import threading
import math
import random
from datetime import timedelta
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas

serial_left = i2c(port=1, address=0x3C)
serial_right = i2c(port=1, address=0x3D)

oled_left = ssd1306(serial_left)
oled_right = ssd1306(serial_right)

wifi_now = 0
wifi_total = 0
bt_now = 0
bt_total = 0

seen_wifi = set()
current_wifi = set()
seen_bt = set()
current_bt = set()

lock = threading.Lock()

def get_ip():
    try:
        return subprocess.check_output("hostname -I", shell=True).decode().strip()
    except:
        return "No IP"

def get_cpu_temp():
    try:
        t = subprocess.check_output("vcgencmd measure_temp", shell=True).decode()
        t = float(t.replace("temp=", "").replace("'C\n", ""))
        return f"{(t*9/5+32):.1f}F"
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

def wifi_scanner():
    global wifi_now, wifi_total
    while True:
        local_now = set()
        try:
            out = subprocess.check_output(
                "sudo iwlist wlan0 scan 2>/dev/null | grep ESSID",
                shell=True
            ).decode()
            for l in out.splitlines():
                ssid = l.split("ESSID:")[1].replace('"','').strip()
                if ssid:
                    local_now.add(ssid)
                    seen_wifi.add(ssid)
        except:
            pass
        with lock:
            current_wifi.clear()
            current_wifi.update(local_now)
            wifi_now = len(local_now)
            wifi_total = len(seen_wifi)
        time.sleep(5)

def bt_scanner():
    global bt_now, bt_total
    while True:
        local_now = set()
        try:
            cmd = "echo -e 'scan on\ndevices\nscan off' | bluetoothctl"
            out = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode()
            for l in out.splitlines():
                if l.startswith("Device"):
                    parts = l.split(maxsplit=2)
                    dev = parts[2] if len(parts) > 2 else parts[1]
                    local_now.add(dev)
                    seen_bt.add(dev)
        except:
            pass
        with lock:
            current_bt.clear()
            current_bt.update(local_now)
            bt_now = len(local_now)
            bt_total = len(seen_bt)
        time.sleep(5)

threading.Thread(target=wifi_scanner, daemon=True).start()
threading.Thread(target=bt_scanner, daemon=True).start()

# --- Radar + WiFi Animation Frames ---

def draw_wifi_bars(draw, level):
    x = 20
    base_y = 54
    for i in range(4):
        height = (i + 1) * 6
        if i < level:
            draw.rectangle((x+i*10, base_y-height, x+i*10+6, base_y), fill=255)
        else:
            draw.rectangle((x+i*10, base_y-height, x+i*10+6, base_y), outline=255)

def draw_radar(draw, sweep_angle, show_blip=False):
    cx, cy, r = 64, 32, 28
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=255)
    x = cx + int(r * math.cos(sweep_angle))
    y = cy + int(r * math.sin(sweep_angle))
    draw.line((cx, cy, x, y), fill=255)
    if show_blip:
        draw.ellipse((cx+15, cy-3, cx+19, cy+3), fill=255)

MODE_INFO = 15
MODE_ANIM = 5
mode = "info"
last_switch = time.time()

while True:
    now = time.time()

    if mode == "info" and now - last_switch > MODE_INFO:
        mode = "anim"
        last_switch = now
    elif mode == "anim" and now - last_switch > MODE_ANIM:
        mode = "info"
        last_switch = now

    if mode == "info":
        with lock:
            w_now, w_total = wifi_now, wifi_total
            b_now, b_total = bt_now, bt_total
            rand_wifi = random.choice(list(current_wifi)) if current_wifi else "---"
            rand_bt = random.choice(list(current_bt)) if current_bt else "---"

        with canvas(oled_left) as draw:
            draw.text((0,0),  "User: jleary53", fill=255)
            draw.text((0,10), f"WiFi: {rand_wifi[:16]}", fill=255)
            draw.text((0,20), f"Temp: {get_cpu_temp()}", fill=255)
            draw.text((0,30), f"CPU: {psutil.cpu_percent()}%", fill=255)
            draw.text((0,40), f"Up: {get_uptime()}", fill=255)
            draw.text((0,50), f"V: {get_usb_voltage()}", fill=255)

        with canvas(oled_right) as draw:
            draw.text((0,0),  "warscanner", fill=255)
            draw.text((0,10), f"BT: {rand_bt[:16]}", fill=255)
            draw.text((0,22), f"WiFi N:{w_now}", fill=255)
            draw.text((0,32), f"WiFi T:{w_total}", fill=255)
            draw.text((0,44), f"BT N:{b_now}", fill=255)
            draw.text((0,54), f"BT T:{b_total}", fill=255)

        time.sleep(1)

    else:
        sweep = 0
        level = 0
        direction = 1
        start = time.time()

        while time.time() - start < MODE_ANIM:
            with canvas(oled_left) as draw:
                draw.text((0,0), "WiFi Scan", fill=255)
                draw_wifi_bars(draw, level)

            with canvas(oled_right) as draw:
                draw.text((0,0), "Radar", fill=255)
                draw_radar(draw, sweep, show_blip=(int(time.time()*2)%4==0))

            sweep += 0.25
            level += direction
            if level >= 4 or level <= 0:
                direction *= -1

            time.sleep(0.15)
