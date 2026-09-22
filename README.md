# InsituMicron — Saint-Gobain Load Cell HMI & DAQ System

![InsituMicron Logo](InsituMicronlogo.jpg)

**Branch:** `St-gobain-lc`  
**Target Platform:** Raspberry Pi 5 (Touchscreen Kiosk) + STM32 Nucleo (F446RE)  
**Application:** 3-Point Flexural Bend Testing & Real-Time DAQ for Ceramic / Glass Samples

---

## 📖 Overview

The **InsituMicron Load Cell HMI** is an industrial-grade PySide6 (Qt6) touch interface designed for high-accuracy 3-point flexural bend testing. An STM32 Nucleo microcontroller samples load (N) and displacement (mm) from high-precision sensors and streams the data over USB-serial to the Raspberry Pi 5. The HMI provides real-time visualization, automatic break detection, data logging (SQLite & CSV), and one-click PDF engineering test reports.

---

## 🚀 Key Features

- **Live Multi-Mode Dashboard**:
  - **Load vs Displacement** (Default flexural curve)
  - **Load vs Time**
  - **Displacement vs Time**
  - **Stress vs Strain** (Automated calculation using beam theory: \(\sigma = \frac{3FL}{2bd^2}\), \(\varepsilon = \frac{6Dd}{L^2}\))
- **Automatic Break Detection**: Configurable arm load threshold (N) and percentage drop triggers instant break alerts and auto-stops data acquisition.
- **On-Screen Touch Keyboard & Numpad**: Fully integrated virtual touch inputs optimized for industrial touchscreens.
- **Historical Analysis & Overlay**: Browse, compare, and overlay previous test runs.
- **Automated PDF Test Reports**: Generate professional test reports with sample parameters, peak load, flexural strength, and stress-strain curves using ReportLab.
- **Auto-Detection**: Scans USB-serial interfaces automatically for the ST-Link (`VID:PID 0483:374B`).
- **Resilient Data Storage**: High-frequency real-time logging via SQLite and instant CSV exports to mounted USB flash drives.

---

## 🗂️ Project Structure

```
├── main.py                     # Application entry point & window management
├── ui_layout.py                # Main UI layout, pages, and interactive widgets
├── graph_manager.py            # PyQtGraph live plotting engine
├── serial_manager.py           # Background thread for STM32 USB-serial streaming
├── data_logger.py              # SQLite & CSV data persistence
├── flexural_analysis.py        # Stress-strain & flexural strength calculations
├── pdf_reporter.py             # PDF engineering report generator
├── settings_manager.py         # Persistent configuration handler (hmi_settings.json)
├── usb_utils.py                # USB flash drive mount & ST-Link detection
├── virtual_keyboard.py         # On-screen touch alphanumeric keyboard and numpad
├── theme.py / constants.py     # Dark industrial theme and UI styling
├── st_gobain_firm1_mainc.c     # STM32 Nucleo firmware for load cell & sensor rig
├── requirements.txt            # Python dependencies
├── deploy/                     # Kiosk service scripts and udev rules
│   ├── kiosk.service           # Systemd kiosk autostart service
│   ├── install_kiosk.sh        # One-line kiosk installer script
│   └── 99-usb-mount.rules      # Udev rules for automated USB drive mounting
└── docs/                       # Datasheets and user manuals
    ├── InsituMicron_DAQ_Hardware_Datasheet_V1.0.pdf
    ├── InsituMicron_DAQ_Operator_Manual_V1.1.pdf
    └── Raspberry_Pi_Kiosk_Setup_Guide.md
```

---

## 🛠️ Hardware Requirements

- **Raspberry Pi 5** (4GB or 8GB RAM, Raspberry Pi OS Bookworm 64-bit)
- **10.1" / 7" Touchscreen Display** (1280×800 or 1920×1080)
- **STM32F446RE Nucleo Board** connected via USB
- **Load Cell & Amplifier** (DFRobot Gravity ADS1115 / HX711)
- **Micro-Epsilon Displacement Sensor**

---

## ⚙️ Installation & Running

### 1. Clone the Repository (St-gobain-lc Branch)
```bash
git clone -b St-gobain-lc https://github.com/aravind-0356/Insitimicron--Stgobain-GUI.git ~/InsituMicron-LoadCell
cd ~/InsituMicron-LoadCell
```

### 2. Setup Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the HMI
```bash
python3 main.py
```

### 4. Deploy Kiosk Autostart (Raspberry Pi)
```bash
cd deploy
sudo bash install_kiosk.sh
```

---

## 📄 License & Ownership
Proprietary — Developed for **Saint-Gobain** by **InsituMicron**. All rights reserved.
