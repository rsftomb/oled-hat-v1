# WarPi.G

**WarPi.G** is a dual-OLED situational awareness display designed for the Raspberry Pi Zero 2 W.  
It visualizes nearby RF activity with a live radar-style interface, system telemetry, and network statistics in a compact, always-on format.

## Features

### Wi-Fi Radar (Primary Display)
- Live **radar-style visualization** of nearby Wi-Fi access points
- **Signal-strength-based positioning**
  - Stronger signals appear closer to the center
  - Weaker signals render farther out
- **Sweep-hit detection**
  - Radar blips flash when intersected by the sweep line
- **SSID pop-up notifications**
  - Newly detected networks briefly display their SSID

 **Blip population control**
  - Maximum of **3 active Wi-Fi blips**
  - Time-based decay removes stale networks
  - Prevents clutter on small OLED displays

### Bluetooth Monitoring
- Tracks nearby Bluetooth devices
- Displays:
  - Active device count
  - Total devices seen
- Bluetooth is **stats-only** and does not affect radar visuals

### System Telemetry
- CPU usage
- CPU temperature
- System uptime
- Disk usage
- IP address
- Build/version display

### Dual OLED Layout
- **Left OLED**
  - System status and telemetry
- **Right OLED**
  - Radar visualization and network stats
- Automatic mode cycling between radar and statistics views

______________________________________________________________________________

## Hardware Requirements

- Raspberry Pi Zero 2 W
- Two SSD1306 OLED displays (I²C)
  - Default addresses:
    - `0x3C` (left)
    - `0x3D` (right)
- Wi-Fi interface (`wlan0`)
- Bluetooth enabled (optional)

______________________________________________________________________________

## Software Requirements

- Raspberry Pi OS (Bullseye or newer recommended)
- Python 3.9+
- Required Python packages:
  pip install luma.oled luma.core psutil

## System Utilities

The following system utilities must be available on the host system:

- `iwlist` — Wi-Fi scanning
- `bluetoothctl` — Bluetooth scanning
- `vcgencmd` — CPU temperature reporting

> ⚠️ **Wi-Fi scanning requires root privileges** due to the use of `iwlist`.

______________________________________________________________________________

## Installation

1. Clone the repository:
   git clone https://github.com/rsftomb/oled-hat-v1
   cd WarPi.G

**Install Python dependencies:**
pip install -r requirements.txt

**Enable I²C:**
sudo raspi-config
Navigate to Interface Options → I2C
Enable I²C and reboot if prompted

**Run the application:**
sudo python3 oled-hat-v1.py



**Disclaimer**

WarPi.G is intended for educational and experimental use only.
Ensure compliance with all applicable local laws and regulations regarding RF scanning and monitoring.
