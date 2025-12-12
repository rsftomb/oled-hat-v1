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
        with open("/sys/class/power_supply/rpi_power_supply/voltage_now") as f:
            v = int(f.read().strip())
        return f"{v/1_000_000:.2f}V"
    except:
        return "?"

# Wi-Fi scanner thread
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
            pass
        time.sleep(5)

# Bluetooth scanner thread
def bt_scanner():
    global bt_now, bt_total, seen_bt
    while True:
        current = set()
        try:
            subprocess.run("bluetoothctl scan on", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(6)
            subprocess.run("bluetoothctl scan off", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            output = subprocess.check_output("bluetoothctl devices", shell=True).decode()
            for line in output.splitlines():
                if line.startswith("Device"):
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        mac = parts[1]
