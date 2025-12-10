#!/usr/bin/python3
# -*- coding:utf-8 -*-

import time
import os
import subprocess
from datetime import timedelta
from PIL import Image, ImageDraw, ImageFont
import waveshare_OLED.WS_OLED as OLED

# -----------------------------
# Utility Functions
# -----------------------------

def get_temp_f():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            c = int(f.read()) / 1000
        f_temp = (c * 9/5) + 32
        return f"{f_temp:.1f}F"
    except:
        return "N/A"

def get_uptime():
    try:
        with open("/proc/uptime") as f:
            seconds = float(f.read().split()[0])
        return str(timedelta(seconds=int(seconds)))
    except:
        return "N/A"

def get_input_voltage():
    # Try Pi5 / Pi4 power supply voltage path
    paths = [
        "/sys/class/power_supply/rpi_power_supply/voltage_now",
    ]

    # Search hwmon for in0_input
    for root, dirs, files in os.walk("/sys/class/hwmon"):
        if "in0_input" in files:
            paths.append(os.path.join(root, "in0_input"))

    for p in paths:
        try:
            with open(p) as f:
                v = int(f.read().strip())
            # hwmon is in mV, power_supply is in microvolts
            if v > 10000:  # microvolts
                return f"{v/1_000_000:.2f}V"
            else:          # millivolts
                return f"{v/1000:.2f}V"
        except:
            pass

    return "N/A"

def scan_wifi():
    try:
        out = subprocess.check_output("iw dev wlan0 scan 2>/dev/null | grep SSID", shell=True).decode()
        return len(out.splitlines())
    except:
        return 0

# Bluetooth tracking
bt_seen = set()

def scan_bt():
    global bt_seen
    try:
        # lescan with --duplicates prevents scan-parameter errors
        out = subprocess.Popen(
            ["hcitool", "lescan", "--duplicates"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        time.sleep(3)
        out.kill()

        lines = out.stdout.read().decode(errors="ignore").splitlines()

        current_devices = set()
        for l in lines:
            parts = l.split()
            if len(parts) >= 1 and ":" in parts[0]:
                mac = parts[0]
                current_devices.add(mac)
                bt_seen.add(mac)

        return len(current_devices), len(bt_seen)

    except:
        return 0, len(bt_seen)

# -----------------------------
# OLED Initialization
# -----------------------------
disp = OLED.OLED_3inch5()
disp.Init()
disp.clear()

font = ImageFont.load_default()

# -----------------------------
# Main Loop
# -----------------------------
while True:
    # Gather data
    temp_f = get_temp_f()
    uptime = get_uptime()
    usb_v = get_input_voltage()
    wifi_count = scan_wifi()
    bt_current, bt_unique = scan_bt()

    # -----------------
    # Screen 1 (Left)
    # -----------------
    image1 = Image.new("1", (128, 64), 0)
    draw1 = ImageDraw.Draw(image1)

    draw1.text((0, 0),  f"r: {temp_f}", font=font, fill=1)
    draw1.text((0, 12), f"Uptime: {uptime}", font=font, fill=1)
    draw1.text((0, 24), f"USB: {usb_v}", font=font, fill=1)
    draw1.text((0, 36), f"WiFi APs: {wifi_count}", font=font, fill=1)

    disp.ShowImage(image1, 0, 0)  # screen 3C

    # -----------------
    # Screen 2 (Right)
    # -----------------
    image2 = Image.new("1", (128, 64), 0)
    draw2 = ImageDraw.Draw(image2)

    draw2.text((0, 0),  f"BT Current: {bt_current}", font=font, fill=1)
    draw2.text((0, 12), f"BT Unique:  {bt_unique}", font=font, fill=1)

    disp.ShowImage(image2, 128, 0)  # screen 3D

    # -----------------
    # Screen 3 (Bottom)
    # -----------------
    image3 = Image.new("1", (256, 64), 0)
    draw3 = ImageDraw.Draw(image3)

    draw3.text((0, 0), "System Status Panel", font=font, fill=1)
    draw3.text((0, 16), f"Temp: {temp_f} | USB: {usb_v}", font=font, fill=1)
    draw3.text((0, 32), f"WiFi: {wifi_count} | BT: {bt_unique}", font=font, fill=1)
    draw3.text((0, 48), f"Uptime: {uptime}", font=font, fill=1)

    disp.ShowImage(image3, 0, 64)

    time.sleep(3)
