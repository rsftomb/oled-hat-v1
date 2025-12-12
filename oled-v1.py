#!/usr/bin/env python3
import time
import psutil
import subprocess
import threading
from datetime import timedelta
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas

# ---------------------------------
# OLED SETUP
# ---------------------------------
serial_left = i2c(port=1, address=0x3C)
serial_right = i2c(port=1, address=0x3D)

oled_left = ssd1306(serial_left)
oled_right = ssd1306(serial_right)

# ---------------------------------
# Thread-Safe Shared Data
# ---------------------------------
wifi_now = 0
wifi_total = 0
bt_now = 0
bt_total = 0

seen_wifi = set()
seen_bt = set()

lock = threading.Lock()

# ---------------------------------
# System Info Helpers
# ---------------------------------
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

# ---------------------------------
# Wi-Fi Scanner Thread
# ---------------------------------
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

# ---------------------------------
# Bluetooth Scanner Thread (Classic + BLE)
# ---------------------------------
def bt_scanner():
    global bt_now, bt_total

    while True:
        current = set()

        try:
            # --------------------------
            # CLASSIC BLUETOOTH SCAN
            # --------------------------
            subprocess.run("timeout 4 hcitool scan",
                           shell=True,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)

            classic_output = subprocess.check_output(
                "bluetoothctl devices",
                shell=True
            ).decode()

            for line in classic_output.splitlines():
                if "Device" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        mac = parts[1]
                        current.add(mac)
                        seen_bt.add(mac)

            # --------------------------
            # BLE SCAN (btmgmt find)
            # --------------------------
            ble_output = subprocess.check_output(
                "timeout 4 sudo btmgmt find",
                shell=True,
                stderr=subprocess.DEVNULL
            ).decode()

            for line in ble_output.splitlines():
                line = line.strip()
                if line.startswith("hci") and "dev_found" in line:
                    parts = line.split()
                    for p in parts:
                        if ":" in p and len(p.split(":")) == 6:
                            mac = p
                            current.add(mac)
                            seen_bt.add(mac)

        except:
            pass

        # Update results
        with lock:
            bt_now = len(current)
            bt_total = len(seen_bt)

        time.sleep(5)

# ---------------------------------
# Start Scanner Threads
# ---------------------------------
threading.Thread(target=wifi_scanner, daemon=True).start()
threading.Thread(target=bt_scanner, daemon=True).start()

# ---------------------------------
# MAIN OLED LOOP
# ---------------------------------
while True:
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
        draw.text((0, 0),  f"Temp: {temp}", fill=255)
        draw.text((0,10), f"CPU: {cpu:.1f}%", fill=255)
        draw.text((0,20), f"IP: {ip}", fill=255)
        draw.text((0,30), f"Uptime: {uptime}", fill=255)
        draw.text((0,40), f"Batt: {usbv}", fill=255)

    # RIGHT DISPLAY
    with canvas(oled_right) as draw:
        draw.text((0,0),  f"WiFi Now: {w_now}", fill=255)
        draw.text((0,10), f"WiFi Tot: {w_total}", fill=255)
        draw.text((0,25), f"BT Now: {b_now}", fill=255)
        draw.text((0,35), f"BT Tot: {b_total}", fill=255)

    time.sleep(1)
