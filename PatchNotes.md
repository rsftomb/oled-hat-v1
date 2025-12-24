📓 ### **WarPi.G – Patch Notes**
_______________________________________________________________________________________

### Build 1223.1

- Added WebUI index.html
  - Expanded telemetry to include:
- Live WiFi SSID list
- Live Bluetooth device name list
- Sublist containers for SSIDs and BT devices scrollable with styled scrollbars.
- UI now uses consistent two-tier display: main metrics at top, expandable sublists below.
  - Minor CSS adjustments for mobile-friendliness:
- Flexible width (90% of viewport, max-width 400px)
- Font-size optimized for readability on small screens
- Refresh interval remains 1 second for real-time updates.

### Build 1222.3

- CPU chip icon & finalized layout refinements
- Added CPU chip icon to match WiFi/Bluetooth visual styling.
- Ensured all system metrics (CPU, WiFi, Bluetooth) have consistent icon + label layout.
- Optimized flexbox spacing for smaller screens.
  - Header and footer styling finalized:
- Fixed positions
- Green-on-black aesthetic
- Disclaimer added to footer for legal clarity.

### Build 1221.01

### Maintenance
- Minor UI code formatting and consistency cleanup
_______________________________________________________________________________________

## Build 1220.03

### Reliability & Boot Stability
- Improved startup reliability when launched via `systemd`
- Added startup delay handling to ensure:
  - I²C bus availability
  - Wi-Fi interface readiness
- Reduced risk of boot-time race conditions on Pi Zero 2 W

### Service Behavior
- Verified clean restart behavior under `systemd`
- Confirmed graceful recovery on script restart without OLED lockups

### Maintenance
- Minor code formatting and consistency cleanup
- No user-facing visual or behavioral changes
_______________________________________________________________________________________

### Build 1220.02

### System & Startup
- Updated primary Python script name from `oled-hat-v1.py` to **`warpig.py`**
- Preserved existing `systemd` auto-start behavior via `start_oled.sh`
- No changes required to service files or startup configuration

### Internal Cleanup
- Aligned internal naming with project branding (`WarPi.G`)
- Removed legacy references to old script naming
- No functional behavior changes to radar, Wi-Fi, or Bluetooth systems

_______________________________________________________________________________________

### Build 1220.01

## Radar System (Major Update)
- **Radar source changed from Bluetooth to Wi-Fi**
  - Radar now visualizes nearby Wi-Fi access points instead of Bluetooth devices.
  - Bluetooth scanning remains active for statistical display only.

- **Signal-strength-based positioning**
  - Wi-Fi RSSI is mapped to radar radius.
  - Stronger signals render closer to center; weaker signals appear toward the edge.

- **Sweep-hit detection & flash effect**
  - Radar blips flash when intersected by the sweep line.
  - Provides real-time visual confirmation of detection events.

- **SSID detection pop-ups**
  - Newly detected Wi-Fi networks briefly display their SSID on the radar screen.
  - Pop-ups automatically expire after a short duration.

- **Blip population control**
  - Radar limited to **3 active Wi-Fi blips** at any time.
  - Old or stale entries are removed using time-based decay.
  - Prevents clutter and improves readability on small OLED displays.

## Wi-Fi Scanner Improvements
- Added **time-based aging** for detected networks.
- Stale SSIDs are automatically removed from radar visualization.
- Total-seen and currently-seen counts are preserved for stats display.

## Bluetooth Scanner
- Bluetooth tracking retained for:
  - Active device count
  - Total seen device count
- Bluetooth devices no longer generate radar artifacts.

## Visual & UX Enhancements
- Radar behavior now more closely resembles a true RF sweep:
  - Dynamic detection
  - Visual confirmation on sweep contact
  - Reduced screen noise under dense RF conditions
- Improved readability during extended runtimes.

## Stability
- Prevented unbounded growth of internal radar state.
- Reduced OLED clutter and overpopulation during long scanning sessions.
______________________________________________________________________________________

  **Build 1219.01 - Beta Prerelease**
- Minor UI Update to Wifi/BT Counter
- Optimization of boot sequence & UI.
_______________________________________________________________________________________
**Build 1215.04**  
- SD Health & UI Stabilization
- Replaced USB voltage readout with SD card health monitoring
- Added detection for read-only filesystem state
- Display SD usage percentage and free space on LEFT OLED
- Improved exception handling around disk and mount queries
- Minor UI spacing and refresh stability improvements
_______________________________________________________________________________________
**Build 1214.02** 
- Wi-Fi Scan
- Bluetooth Scan
- Introduced lightweight state machine for screen control
- Preserved background scanning threads during menu navigation
- Improved button debounce logic for reliable input
_______________________________________________________________________________________
**Build 1212.05** 
- Dual-OLED Wardriving Dashboard
- Implemented dual OLED layout (left/right displays)
- Added animated Bluetooth radar visualization
- Added live Wi-Fi signal bar display
- Improved Bluetooth device tracking and timeout pruning
- Randomized device “blips” for radar realism
_______________________________________________________________________________________
**Build 1211.04 - Initial Release**
- Core Scanning & System Telemetry
- Initial release of Wi-Fi and Bluetooth scanning engine

Added live system telemetry:
- CPU usage
- CPU temperature
- Uptime
- IP address
- Implemented background scanning threads for non-blocking UI
- Established base display rendering loop using luma.oled
