====================================== PATCH NOTES ======================================
📓 Changelog / Patch Notes

v1.31 — SD Health & UI Stabilization

Replaced USB voltage readout with SD card health monitoring

Added detection for read-only filesystem state

Display SD usage percentage and free space on LEFT OLED

Improved exception handling around disk and mount queries

Minor UI spacing and refresh stability improvements

v1.30 — Menu System & Button Integration

Added scrollable menu system navigable via Waveshare K1–K4 buttons

Implemented menu-driven views:

Dashboard

Wi-Fi Scan

Bluetooth Scan

Introduced lightweight state machine for screen control

Preserved background scanning threads during menu navigation

Improved button debounce logic for reliable input

v1.25 — Dual-OLED Wardriving Dashboard

Implemented dual OLED layout (left/right displays)

Added animated Bluetooth radar visualization

Added live Wi-Fi signal bar display

Improved Bluetooth device tracking and timeout pruning

Randomized device “blips” for radar realism

v1.23 — Core Scanning & System Telemetry

Initial release of Wi-Fi and Bluetooth scanning engine

Added live system telemetry:

CPU usage

CPU temperature

Uptime

IP address

Implemented background scanning threads for non-blocking UI

Established base display rendering loop using luma.oled
