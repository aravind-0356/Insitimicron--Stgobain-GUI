# InsituMicron — Saint-Gobain Motor Control HMI

![InsituMicron Logo](InsituMicronlogo.jpg)

**Branch:** `motor-hmi`  
**Target Platform:** Raspberry Pi 5 (Touchscreen Kiosk) + STM32 Nucleo (F446RE) + Leadshine Stepper Drive  
**Application:** Industrial Linear Rig Motion & Velocity Control

---

## 📖 Overview

The **InsituMicron Motor Control HMI** is a dedicated PySide6 (Qt6) interface built for precise motor positioning and velocity control of industrial linear rigs. Communicating directly with an STM32 Nucleo MCU, it controls Leadshine stepper motor drives over Modbus RTU, coordinates limit switch safety triggers, monitors encoder feedback, and logs motion data in real-time.

---

## 🚀 Key Features

- **Intuitive Jog & Position Control**:
  - Continuous and stepped JOG (Up / Down) with velocity setpoints.
  - Position readout with zero/tare capabilities.
  - Emergency hardware and software kill switch status integration.
- **Hardware Safety & Interlocks**:
  - Double-button safety interlocks preventing simultaneous opposing directional commands.
  - Active-low hardware kill switch monitoring via MCU GPIO (`PB5`).
- **Live Motion Telemetry & Graphing**:
  - Real-time visualization of position, velocity, and drive status.
- **On-Screen Touch Keyboard & Numpad**: Optimized for high-responsiveness on industrial touchscreens.
- **Auto-Detection**: Automatic discovery of the STM32 ST-Link interface (`VID:PID 0483:374B`).
- **Resilient Logging**: Motion profiles and test sequences logged to SQLite and exported to CSV.

---

## 🗂️ Project Structure

```
├── main.py                     # Application entry point & window management
├── ui_layout.py                # Touchscreen UI layout & motor control panels
├── graph_manager.py            # PyQtGraph live motion telemetry plotting
├── serial_manager.py           # Background thread for STM32 USB-serial streaming
├── data_logger.py              # SQLite & CSV data persistence
├── settings_manager.py         # Persistent configuration handler (hmi_settings.json)
├── usb_utils.py                # USB flash drive mount & ST-Link detection
├── virtual_keyboard.py         # On-screen touch alphanumeric keyboard and numpad
├── theme.py / constants.py     # Dark industrial theme and UI styling
├── stgobain_mtr_rpi_main.c     # STM32 Nucleo firmware for motor communication
├── test_init.py                # Hardware initialization and self-test routine
├── requirements.txt            # Python dependencies
├── CS2RS_Series_User_Manual_V1.5.pdf # Leadshine Stepper Driver manual
└── Raspberry_Pi_Kiosk_Setup_Guide.md # Raspberry Pi deployment guide
```

---

## 🛠️ Hardware Requirements

- **Raspberry Pi 5** (Raspberry Pi OS Bookworm 64-bit)
- **10.1" / 7" Touchscreen Display**
- **STM32F446RE Nucleo Board** connected via USB
- **Leadshine Stepper Motor Drive** (CS2RS Series, Modbus RTU on `USART1`)
- **Linear Stage with Optical / Mechanical Limit Switches**

---

## ⚙️ Installation & Running

### 1. Clone the Repository (Motor HMI Branch)
```bash
git clone -b motor-hmi https://github.com/aravind-0356/Insitimicron--Stgobain-GUI.git ~/InsituMicron-MotorHMI
cd ~/InsituMicron-MotorHMI
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

---

## 📄 License & Ownership
Proprietary — Developed for **Saint-Gobain** by **InsituMicron**. All rights reserved.
