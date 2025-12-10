import time
import subprocess
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont
import psutil
import socket
import threading

# OLED setup
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial, width=128, height=64)
font = ImageFont.load_default()

# Sets to store unique networks and Bluetooth devices since boot
seen_wifi = set()
seen_bt = set()

# Shared data variables
wifi_now = 0
wifi_total = 0
wifi_signal = "N/A"
bt_now = 0
bt_total = 0

# Lock to prevent race conditions
data_lock = threading.Lock()

def get_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return "No IP"

def get_cpu_temp():
    try:
        temp = subprocess.check_output("vcgencmd measure_temp", shell=True).decode()
        return temp.replace("temp=","").strip()
    except:
        return "N/A"

def get_cpu_load():
    return f"{psutil.cpu_percent()}%"

def wifi_scanner():
    global wifi_now, wifi_total, wifi_signal
    while True:
        try:
            output = subprocess.check_output("sudo iwlist wlan0 scan | grep 'ESSID\\|Signal'", shell=True).decode()
            networks = []
            signal = "N/A"
            for line in output.split("\n"):
                line = line.strip()
                if line.startswith("ESSID:"):
                    ssid = line.split(":")[1].strip('"')
                    networks.append(ssid)
                    seen_wifi.add(ssid)
                elif line.startswith("Quality="):
                    quality = line.split()[0].split('=')[1]
                    signal = quality
            with data_lock:
                wifi_now = len(networks)
                wifi_total = len(seen_wifi)
                wifi_signal = signal
        except:
            with data_lock:
                wifi_now = 0
                wifi_signal = "N/A"
        time.sleep(5)

def bt_scanner():
    global bt_now, bt_total
    while True:
        try:
            subprocess.run("timeout 5s bluetoothctl scan on", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            output = subprocess.check_output("bluetoothctl devices", shell=True).decode()
            devices = []
            for line in output.split("\n"):
                if line.startswith("Device"):
                    addr = line.split()[1]
                    devices.append(addr)
                    seen_bt.add(addr)
            with data_lock:
                bt_now = len(devices)
                bt_total = len(seen_bt)
        except:
            with data_lock:
                bt_now = 0
        time.sleep(5)

# Start scanner threads
threading.Thread(target=wifi_scanner, daemon=True).start()
threading.Thread(target=bt_scanner, daemon=True).start()

# Main display loop
while True:
    image = Image.new("1", (device.width, device.height))
    draw = ImageDraw.Draw(image)

    # Top line - CPU info
    top_line = f"CPU:{get_cpu_load()} T:{get_cpu_temp()} IP:{get_ip()}"
    draw.text((0, 0), top_line, font=font, fill=255)

    # Second line - Wi-Fi signal
    with data_lock:
        second_line = f"Wi-Fi Signal:{wifi_signal}"
    draw.text((0, 10), second_line, font=font, fill=255)

    # Main area - Wi-Fi and Bluetooth stats
    with data_lock:
        main_text = f"W-Net:{wifi_now} Total:{wifi_total}\nBT:{bt_now} Total:{bt_total}"
    draw.text((0, 25), main_text, font=font, fill=255)

    device.display(image)
    time.sleep(1)
