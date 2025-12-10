import time
import subprocess
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont
import psutil
import socket

# OLED setup
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial, width=128, height=64)

# Load default font
font = ImageFont.load_default()

# Set to store unique SSIDs since boot
seen_networks = set()

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

def get_mem_usage():
    mem = psutil.virtual_memory()
    return f"{mem.percent}%"

def scan_wifi():
    try:
        output = subprocess.check_output("sudo iwlist wlan0 scan | grep 'ESSID\\|Signal'", shell=True).decode()
        networks = []
        current_signal = "N/A"
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("ESSID:"):
                ssid = line.split(":")[1].strip('"')
                networks.append(ssid)
                seen_networks.add(ssid)
            elif line.startswith("Quality="):
                parts = line.split()
                quality = parts[0].split('=')[1]
                current_signal = quality
        return len(networks), current_signal, len(seen_networks)
    except:
        return 0, "N/A", len(seen_networks)

while True:
    # Create a blank image for drawing
    image = Image.new("1", (device.width, device.height))
    draw = ImageDraw.Draw(image)

    # System info top line
    top_line = f"CPU:{get_cpu_load()} T:{get_cpu_temp()} IP:{get_ip()}"
    draw.text((0, 0), top_line, font=font, fill=255)

    # Second line - Wi-Fi signal
    _, current_signal, _ = scan_wifi()
    second_line = f"Wi-Fi Signal: {current_signal}"
    draw.text((0, 10), second_line, font=font, fill=255)

    # Main area - Wi-Fi stats
    num_now, _, num_total = scan_wifi()
    main_text = f"Networks Now: {num_now}\nTotal Seen: {num_total}"
    draw.text((0, 25), main_text, font=font, fill=255)

    # Display it
    device.display(image)
    time.sleep(5)
