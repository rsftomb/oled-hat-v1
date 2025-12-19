======== WarPi.G Zero2W - Python Wardriver for Pi Zero2w ======== 

Dual-OLED live telemetry + Wi-Fi/Bluetooth scanning system for the Raspberry Pi Zero 2 W.
Designed for compact wardriving rigs.

- Designed and tested on Raspberry Pi Zero 2 W
- Optimized for low power, portable wardriving use
- Intended for educational and lawful wireless surveying only - Author IS NOT liable for end users actions.
- Supports 2x SSD1306 (128×64) I²C OLED displays, pulls device/system stats, and continuously updates live scan data in real time.
- Future display support additions planned - Can be manually configured for your display.

✨ **WarPi.G Features**

📡 **WiFi Wardriving**
- Wi-Fi Uses _iwlist_ for maximum compatibility
- Shows current visible SSIDs
- Counts current visible devices
- Stores unique SSIDs for "Total Seen This Boot"

📶 **Bluetooth**
- Uses _bluetoothctl_ scan on/off
- Shows current visible Device Names
- Counts current visible devices
- Stores unique MACs "Total Seen This Boot"

📺 **Native Dual OLED Output - 40pin GPIO SLC**

- Left Display (0x3C): System Info
User: [username]
CPU temperature (°F)
CPU load %
IP address
Uptime HH:MM:SS
SD Usage

Right Display (0x3D): Wardriving Info

Mode: “Wardrive”

Wi-Fi icon + Now / Total

Bluetooth icon + Now / Total

✔ Multithreaded

Separate Wi-Fi and Bluetooth worker threads keep counts live and responsive.

✔ Clean Icons

Minimal WiFi + BT glyphs for clarity.

📦 **Hardware Requirements**

Raspberry Pi Zero 2 W

Two SSD1306 OLED displays

Working Wi-Fi + Bluetooth (built-in)

Software

**Install dependencies:**

sudo apt update
sudo apt install python3-pip python3-smbus python3-pil i2c-tools
pip3 install luma.oled psutil


**Enable I2C:**

sudo raspi-config

🔧 How It Works
Thread & Data Flow
Component	Description
wifi_scanner()	Performs repeated iwlist wlan0 scan operations. Updates count + unique total.
bt_scanner()	Runs bluetoothctl scan on/off. Tracks visible and total MACs.
get_cpu_temp()	Converts Pi temp to Fahrenheit.
get_usb_voltage()	Reads Pi 5V rail via vcgencmd measure_volts.
canvas(oled)	Draws each frame on both displays.
threading.Lock()	Prevents races between the two scan threads.


▶ Setup AutoRun Automatically (systemd)

Create a service:

/etc/systemd/system/oled.service

[Unit]
Description=WarScanner OLED Display Service
After=network.target bluetooth.target

[Service]
ExecStart=/usr/bin/python3 /home/YOURUSER/oled.py
Restart=always
User=pi

[Install]
WantedBy=multi-user.target


Enable and start:

sudo systemctl enable oled.service
sudo systemctl start oled.service


Restart live without reboot:

sudo systemctl restart oled.service

🧪 Known Limitations

Wi-Fi scan speed depends on local RF noise.

Bluetooth scanning may miss some devices using privacy MAC rotation.

OLEDs can burn in if static text is displayed for long periods.

🚀 Planned for V2

Auto-save CSV of all seen Wi-Fi + BT devices

Hotkey-triggered mode switching

Optional e-ink version (ultra-low-power)

📜 License (MIT)
MIT License

Copyright (c) 2025 
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

👤 Author

Developed by:
jleary53 / Sunshine State Media LLC
