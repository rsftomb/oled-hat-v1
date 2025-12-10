#!/usr/bin/env python3
import time
import psutil
import subprocess
import platform
from datetime import timedelta
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas

# --------------------------------------------------
# I2C SCREEN SETUP
# --------------------------------------------------
serial_left = i2c(port=1, address=0x3C)
serial_right = i2c(port=1, address=0x3D)

oled_left = ssd1306(serial_left)
oled_right = ssd1306(serial_right)

# Track previously seen WiFi/Bluetooth devices
seen_wifi = set()
seen_bt = set()

# --------------------------------------------------
# Helper Functions
# --------------------------------------------------

def get_ip():
    try:
        ip = subprocess.check_output("hostname -I", shell=True).decode().strip()
        return ip if ip else "No IP"
    except:
        return "No IP"

def get_cpu_temp():
    try:
        temp = subprocess.check_output("vcgencmd measure_temp", shell=True).decode()
        temp = temp.replace("temp=", "").replace("'C\n", "")
        return temp
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
        volt = subprocess.check_output("vcgencmd get_throttled", shell=True).decode().strip()
        if "0x0" in volt:
            return "OK"
        else:
            return "LOW!"
    except:
        return "?"

def scan_wifi():
    global seen_wifi
    try:
        result = subprocess.check_output("sudo iwlist wlan0 scan", shell=True).decode()
        networks = result.count("ESSID:")

        for line in result.splitlines():
            if "ESSID:" in line:
                ssid = line.split(":")[1].replace('"','')
                if ssid.strip():
                    seen_wifi.add(ssid)

        return networks, len(seen_wifi)
    except:
        return 0, len(seen_wifi)

def scan_bt():
    global seen_bt
    try:
        # Faster and more reliable scan
        output = subprocess.check_output("sudo hcitool lescan --duplicates --passive", shell=True, timeout=5).decode()

        current_devices = set()
        for line in output.split("\n"):
            if ":" in line:
                parts = line.strip().split()
                mac = parts[0]
                if len(mac.split(":")) == 6:  # validates BT MAC
                    current_devices.add(mac)
                    seen_bt.add(mac)

        return len(current_devices), len(seen_bt)
    except:
        return 0, len(seen_bt)

# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------
while True:
    # Collect readings
    ip = get_ip()
    cpu = psutil.cpu_percent()
    temp = get_cpu_temp()
    uptime = get_uptime()
    usbv = get_usb_voltage()

    wifi_now, wifi_total = scan_wifi()
    bt_now, bt_total = scan_bt()

    # ---------------------------
    # LEFT SCREEN (SYSTEM INFO)
    # ---------------------------
    with canvas(oled_left) as draw:
        draw.text((0,0), f"Host: {platform.node()}", fill=255)
        draw.text((0,10), f"IP: {ip}", fill=255)
        draw.text((0,20), f"CPU: {cpu}%", fill=255)
        draw.text((0,30), f"T:{temp}C", fill=255)
        draw.text((0,40), f"Up:{uptime}", fill=255)
        draw.text((0,50), f"USB:{usbv}", fill=255)

    # ---------------------------
    # RIGHT SCREEN (SCAN INFO)
    # ---------------------------
    with canvas(oled_right) as draw:
        draw.text((0,0),  f"WiFi Now: {wifi_now}",   fill=255)
        draw.text((0,10), f"WiFi Tot: {wifi_total}", fill=255)
        draw.text((0,25), f"BT Now: {bt_now}",       fill=255)
        draw.text((0,35), f"BT Tot: {bt_total}",     fill=255)

    time.sleep(2)
