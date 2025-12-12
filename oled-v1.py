#!/usr/bin/env python3
import time
import psutil
import subprocess
import threading
from datetime import timedelta
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas

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
seen_bt = set()

lock = threading.Lock()

# System info helpers
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

# --- EYE ANIMATION FRAMES ---
def draw_eyes_center(draw):
    draw.ellipse((20, 20, 40, 40), outline=255, fill=0)
    draw.ellipse((60, 20, 80, 40), outline=255, fill=0)
    draw.ellipse((28, 28, 34, 34), outline=255, fill=255)
    draw.ellipse((68, 28, 74, 34), outline=255, fill=255)

def draw_eyes_left(draw):
    draw.ellipse((20, 20, 40, 40), outline=255, fill=0)
    draw.ellipse((60, 20, 80, 40), outline=255, fill=0)
    draw.ellipse((24, 28, 30, 34), outline=255, fill=255)
    draw.ellipse((64, 28, 70, 34), outline=255, fill=255)

def draw_eyes_right(draw):
    draw.ellipse((20, 20, 40, 40), outline=255, fill=0)
    draw.ellipse((60, 20, 80, 40), outline=255, fill=0)
    draw.ellipse((32, 28, 38, 34), outline=255, fill=255)
    draw.ellipse((72, 28, 78, 34), outline=255, fill=255)

def draw_eyes_blink(draw):
    draw.rectangle((20, 28, 40, 32), fill=255)
    draw.rectangle((60, 28, 80, 32), fill=255)

# --- Wi-Fi scanner ---
def wifi_scanner():
    global wifi_now, wifi_total
    while True:
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
                    count += 1
            with lock:
                wifi_now = count
                wifi_total = len(seen_wifi)
        except:
            with lock:
                wifi_now = 0
        time.sleep(5)

# --- Bluetooth scanner ---
def bt_scanner():
    global bt_now, bt_total
    while True:
        current = set()
        try:
            scan_cmds = """
echo -e 'scan on\ndevices\nscan off' | bluetoothctl
"""
            output = subprocess.check_output(scan_cmds, shell=True, stderr=subprocess.DEVNULL).decode()

            for line in output.splitlines():
                if line.startswith("Device"):
                    mac = line.split()[1]
                    current.add(mac)
                    seen_bt.add(mac)
        except:
            pass

        with lock:
            bt_now = len(current)
            bt_total = len(seen_bt)
        time.sleep(5)

# Start threads
threading.Thread(target=wifi_scanner, daemon=True).start()
threading.Thread(target=bt_scanner, daemon=True).start()

# Icons
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

# --- Main Loop with Animation ---
MODE_TIME_INFO = 15
MODE_TIME_EYES = 5

last_switch = time.time()
mode = "info"

while True:

    # Switch mode every 15s/5s
    if mode == "info" and time.time() - last_switch > MODE_TIME_INFO:
        mode = "eyes"
        last_switch = time.time()
    elif mode == "eyes" and time.time() - last_switch > MODE_TIME_EYES:
        mode = "info"
        last_switch = time.time()

    # --- NORMAL MODE ---
    if mode == "info":

        with lock:
            w_now, w_total = wifi_now, wifi_total
            b_now, b_total = bt_now, bt_total

        ip = get_ip()
        cpu = psutil.cpu_percent(interval=0.5)
        temp = get_cpu_temp()
        uptime = get_uptime()
        usbv = get_usb_voltage()

        # LEFT DISPLAY
        with canvas(oled_left) as draw:
            draw.text((0, 0),  " User: jleary53", fill=255)
            draw.text((0,10), f" Temp: {temp}", fill=255)
            draw.text((0,20), f" CPU: {cpu:.1f}%", fill=255)
            draw.text((0,30), f" IP: {ip}", fill=255)
            draw.text((0,40), f" Uptime: {uptime}", fill=255)
            draw.text((0,50), f" Batt: {usbv}", fill=255)

        # RIGHT DISPLAY
        with canvas(oled_right) as draw:
            draw.text((0,0), "Mode: Wardrive", fill=255)
            draw_wifi_icon(draw, 0, 10)
            draw.text((10,10), f"WiFi Now: {w_now}", fill=255)
            draw.text((10,20), f"WiFi Tot: {w_total}", fill=255)
            draw_bt_icon(draw, 0, 35)
            draw.text((10,35), f"BT Now: {b_now}", fill=255)
            draw.text((10,45), f"BT Tot: {b_total}", fill=255)

        time.sleep(1)

    # --- EYES ANIMATION MODE ---
    else:

        frames = [
            draw_eyes_center,
            draw_eyes_left,
            draw_eyes_right,
            draw_eyes_center,
            draw_eyes_blink,
            draw_eyes_center
        ]

        for frame in frames:
            if mode != "eyes":
                break
            with canvas(oled_left) as draw:
                frame(draw)
            with canvas(oled_right) as draw:
                frame(draw)
            time.sleep(0.3)
