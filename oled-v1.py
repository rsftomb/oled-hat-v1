#!/usr/bin/env python3
import time
import psutil
import subprocess
from datetime import timedelta
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas

# -----------------------------
# OLED SCREEN SETUP
# -----------------------------
serial_left = i2c(port=1, address=0x3C)
serial_right = i2c(port=1, address=0x3D)

oled_left = ssd1306(serial_left)
oled_right = ssd1306(serial_right)

# Track unique devices seen
seen_wifi = set()
seen_bt = set()

# -----------------------------
# Helper Functions
# -----------------------------
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
    # Read Pi input voltage
    paths = ["/sys/class/power_supply/rpi_power_supply/voltage_now"]
    for p in paths:
        try:
            with open(p) as f:
                v = int(f.read().strip())
            return f"{v/1_000_000:.2f}V"  # microvolts -> volts
        except:
            pass
    return "?"

def scan_wifi():
    global seen_wifi
    try:
        result = subprocess.check_output("sudo iwlist wlan0 scan 2>/dev/null | grep ESSID", shell=True).decode()
        count = 0
        for line in result.splitlines():
            ssid = line.split("ESSID:")[1].replace('"','').strip()
            if ssid:
                seen_wifi.add(ssid)
                count += 1
        return count, len(seen_wifi)
    except:
        return 0, len(seen_wifi)

def scan_bt():
    global seen_bt
    try:
        # Use bluetoothctl for scanning to prevent errors
        output = subprocess.check_output("timeout 3 bluetoothctl scan on", shell=True, stderr=subprocess.DEVNULL).decode()
        current = set()
        for line in output.splitlines():
            if "Device" in line:
                parts = line.strip().split()
                if len(parts) >= 2:
                    mac = parts[1]
                    current.add(mac)
                    seen_bt.add(mac)
        return len(current), len(seen_bt)
    except:
        return 0, len(seen_bt)

# -----------------------------
# MAIN LOOP
# -----------------------------
while True:
    # Gather data
    ip = get_ip()
    cpu = psutil.cpu_percent()
    temp = get_cpu_temp()
    uptime = get_uptime()
    usbv = get_usb_voltage()
    wifi_now, wifi_total = scan_wifi()
    bt_now, bt_total = scan_bt()

    # -----------------------------
    # LEFT SCREEN (System Info)
    # -----------------------------
    with canvas(oled_left) as draw:
        draw.text((0,0),  f"r: {temp}", fill=255)
        draw.text((0,10), f"CPU: {cpu}%", fill=255)
        draw.text((0,20), f"IP: {ip}", fill=255)
        draw.text((0,30), f"Uptime: {uptime}", fill=255)
        draw.text((0,40), f"USB: {usbv}", fill=255)

    # -----------------------------
    # RIGHT SCREEN (Wi-Fi / BT Info)
    # -----------------------------
    with canvas(oled_right) as draw:
        draw.text((0,0),  f"WiFi Now: {wifi_now}", fill=255)
        draw.text((0,10), f"WiFi Tot: {wifi_total}", fill=255)
        draw.text((0,25), f"BT Now: {bt_now}", fill=255)
        draw.text((0,35), f"BT Tot: {bt_total}", fill=255)

    time.sleep(2)
#!/usr/bin/env python3
import time
import psutil
import subprocess
from datetime import timedelta
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas

# -----------------------------
# OLED SCREEN SETUP
# -----------------------------
serial_left = i2c(port=1, address=0x3C)
serial_right = i2c(port=1, address=0x3D)

oled_left = ssd1306(serial_left)
oled_right = ssd1306(serial_right)

# Track unique devices seen
seen_wifi = set()
seen_bt = set()

# -----------------------------
# Helper Functions
# -----------------------------
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
    # Read Pi input voltage
    paths = ["/sys/class/power_supply/rpi_power_supply/voltage_now"]
    for p in paths:
        try:
            with open(p) as f:
                v = int(f.read().strip())
            return f"{v/1_000_000:.2f}V"  # microvolts -> volts
        except:
            pass
    return "?"

def scan_wifi():
    global seen_wifi
    try:
        result = subprocess.check_output("sudo iwlist wlan0 scan 2>/dev/null | grep ESSID", shell=True).decode()
        count = 0
        for line in result.splitlines():
            ssid = line.split("ESSID:")[1].replace('"','').strip()
            if ssid:
                seen_wifi.add(ssid)
                count += 1
        return count, len(seen_wifi)
    except:
        return 0, len(seen_wifi)

def scan_bt():
    global seen_bt
    try:
        # Use bluetoothctl for scanning to prevent errors
        output = subprocess.check_output("timeout 3 bluetoothctl scan on", shell=True, stderr=subprocess.DEVNULL).decode()
        current = set()
        for line in output.splitlines():
            if "Device" in line:
                parts = line.strip().split()
                if len(parts) >= 2:
                    mac = parts[1]
                    current.add(mac)
                    seen_bt.add(mac)
        return len(current), len(seen_bt)
    except:
        return 0, len(seen_bt)

# -----------------------------
# MAIN LOOP
# -----------------------------
while True:
    # Gather data
    ip = get_ip()
    cpu = psutil.cpu_percent()
    temp = get_cpu_temp()
    uptime = get_uptime()
    usbv = get_usb_voltage()
    wifi_now, wifi_total = scan_wifi()
    bt_now, bt_total = scan_bt()

    # -----------------------------
    # LEFT SCREEN (System Info)
    # -----------------------------
    with canvas(oled_left) as draw:
        draw.text((0,0),  f"r: {temp}", fill=255)
        draw.text((0,10), f"CPU: {cpu}%", fill=255)
        draw.text((0,20), f"IP: {ip}", fill=255)
        draw.text((0,30), f"Uptime: {uptime}", fill=255)
        draw.text((0,40), f"USB: {usbv}", fill=255)

    # -----------------------------
    # RIGHT SCREEN (Wi-Fi / BT Info)
    # -----------------------------
    with canvas(oled_right) as draw:
        draw.text((0,0),  f"WiFi Now: {wifi_now}", fill=255)
        draw.text((0,10), f"WiFi Tot: {wifi_total}", fill=255)
        draw.text((0,25), f

