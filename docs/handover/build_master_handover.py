# docs/handover/build_master_handover.py
"""
Master Handover Document Generator for InsituMicron Load & Displacement DAQ System.
Client / Deployment Site: Saint-Gobain (MOR Test Rig)
Generates: docs/handover/InsituMicron_DAQ_Rig_Technical_Handover_Manual_V1.0.docx
"""
import os
import sys

# Ensure local handover directory is on sys.path
sys.path.insert(0, os.path.dirname(__file__))

from builder_common import (
    create_base_document, add_title_page, setup_header_footer,
    add_document_control, add_table_of_contents, add_chapter_heading,
    add_section_heading, add_sub_heading, add_callout, add_code_block,
    add_def_table, add_header_table,
    CLR_PRIMARY, CLR_ACCENT, CLR_TEXT, CLR_MUTED, CLR_LIGHT_BG, CLR_BORDER
)
from docx.shared import Inches, Pt, RGBColor


def build_master_manual(output_path):
    print("Building Master Technical Handover Manual for Load & Displacement DAQ Rig (Saint-Gobain)...")
    doc = create_base_document()

    # Determine paths
    repo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    logo_path = os.path.join(repo_dir, "InsituMicronlogo.jpg")

    # Title Page
    add_title_page(
        doc,
        main_title="Master Technical Handover Manual: Load & Displacement DAQ System",
        subtitle="Comprehensive Engineering Guide for Embedded Firmware, Touchscreen Architecture, Electronics & Kiosk Deployment (Saint-Gobain MOR Test Rig)",
        system_model="InsituMicron Load & Displacement DAQ Rig (Raspberry Pi 5 + Waveshare 10.1\" Touch Display + STM32 Nucleo F446RE) - Saint-Gobain",
        doc_version="Software v1.0 / Firmware v1.0",
        doc_date="2026-10-23",
        author="Aravind (Embedded Systems Engineer)",
        reviewer="Engineering Team / Custodians",
    )

    # Running Headers and Footers
    setup_header_footer(
        doc,
        short_title="InsituMicron DAQ System Handover | Saint-Gobain",
        doc_version="v1.0",
        doc_date="2026-10-23",
        logo_path=logo_path if os.path.exists(logo_path) else None,
    )

    # Document Control Block
    doc_control_rows = [
        [
            "1.0",
            "2026-10-23",
            "Aravind\nEmbedded Systems Engineer",
            "Engineering Team\nInsituMicron",
            "Initial complete master technical handover manual covering embedded firmware, PySide6 GUI, electrical hardware BOM, kiosk deployment, testing runbooks, risk register, and quick reference for the Saint-Gobain deployment."
        ]
    ]
    add_document_control(doc, doc_control_rows)

    # Table of Contents
    add_table_of_contents(doc)

    # =========================================================================
    # CHAPTER 1: SYSTEM ARCHITECTURE AND OPERATING TOPOLOGY
    # =========================================================================
    add_chapter_heading(doc, 1, "System Architecture and Operating Topology")

    add_callout(
        doc, "DANGER", "ELECTRICAL MAINS PROTECTION CHAIN & PHYSICAL ISOLATION",
        "MAINS PROTECTION ORDER: 230V AC Mains -> MCB (4A) -> E-Stop (XB5) -> Contactor (LC1E) -> SMPS (24V & 5V).\n"
        "The DAQ instrument connects to 230 VAC 50 Hz single-phase mains power. Mains voltage is routed directly through a Schneider ACTI9 4A MCB, followed by the normally closed (NC) contacts of a Schneider Harmony XB5AS8444 mushroom-head emergency stop button, which energizes the 230V coil of a Schneider LC1E0910M7 contactor. Pressing the emergency stop drops the contactor coil, physically severing AC mains voltage before it reaches both internal switch-mode power supplies (24V SMPS and 5V SMPS). This completely isolates DC power from all sensors, displays, and controller electronics independently of software. Never bypass this contactor circuit during servicing."
    )

    add_callout(
        doc, "NOTE", "SYSTEM PURPOSE & DEPLOYMENT SCOPE (SAINT-GOBAIN)",
        "This master document provides the complete engineering knowledge transfer for the InsituMicron Load and Displacement Data Acquisition (DAQ) System retrofitted on top of an existing MOR (Modulus of Rupture) test setup for Saint-Gobain. The rig is purely a high-precision data acquisition and analysis instrument; specimen loading is applied by the host mechanical structure without motorized control from this unit. There is no traditional proprietary industrial HMI (such as Kinco); the entire HMI architecture is realized through a Waveshare 10.1\" capacitive touch display driven by a Raspberry Pi 5 running PySide6 under the Cage Wayland compositor."
    )

    add_section_heading(doc, "1.1", "Physical and Logical System Topology")
    doc.add_paragraph(
        "The DAQ instrument provides deterministic real-time sensing, live touchscreen visualization, and local data persistence for flexural bend tests. The system separates the real-time physical acquisition domain from the user interface and analytics domain using a dual-processor architecture:"
    )

    topo_defs = [
        ("Host Controller (Raspberry Pi 5)", "Quad-core ARM Cortex-A76 @ 2.4 GHz processor with 4 GB LPDDR4X RAM running Raspberry Pi OS Lite (64-bit) locked under an immutable OverlayFS filesystem. Executes the PySide6 (Qt6) industrial touchscreen GUI under the Cage Wayland kiosk compositor. Manages SQLite WAL logging, real-time pyqtgraph visualization, and automated USB exports."),
        ("Touchscreen Interface (Waveshare 10.1\" IPS)", "10.1-inch industrial IPS panel (1280 x 800 resolution) with 10-point capacitive toughened-glass touch surface and HDMI video interface. Powered via 5V DC from the internal SMPS; touch input is transferred via USB. Replaces traditional industrial HMI panels."),
        ("Sensor Microcontroller (STM32F446RE)", "32-bit ARM Cortex-M4 microcontroller running bare-metal C firmware at 84 MHz SYSCLK. Owns high-speed deterministic acquisition of analog load cell signals via an isolated 15-bit I2C ADC and displacement readings via an RS-485 serial LVDT sensor. Formats and transmits telemetry packets to the host over USB-serial at 20 Hz."),
        ("Displacement Transducer (Micro-Epsilon LVDT)", "Micro-Epsilon induSENSOR DTD-10G8 inductive displacement sensor with dedicated MSC7xxx digital controller. Communicates over RS-485 serial at 256000 baud with 9-bit Even parity framing (9E1), measuring probe stroke with sub-micron resolution."),
        ("Load Measurement Signal Conditioner & ADC", "Pre-existing 0 to 10 V conditioned analog load cell output interfaced to a DFRobot Gravity 15-bit dual-channel ADC module (I2C address 0x4B). Communicates over I2C2 at 100 kHz, delivering digitized force data scaled up to 2943 N (300 kgf)."),
        ("Mains Power & Safety Protection Enclosure", "Powder-coated mild steel benchtop enclosure (400 x 350 x 160 mm) housing the MCB, contactor, E-stop, Mean Well LRS-150-24 (24V SMPS), Mean Well RS-25-5 (5V SMPS), and dual JIGO 24VDC cooling fans."),
    ]
    add_def_table(doc, topo_defs)

    add_section_heading(doc, "1.2", "End-to-End Data Acquisition Pipeline")
    doc.add_paragraph(
        "Data flow from raw physical transducer interaction to permanent storage executes through a synchronized pipeline operating at 20 Hz (50 ms cycle time):"
    )

    data_pipeline_steps = [
        ("1. Transducer Sensing", "The specimen undergoes mechanical flexure on the Saint-Gobain MOR frame. The load cell produces an analog voltage proportional to force, conditioned to a 0 to 10 V range. Concurrently, the Micro-Epsilon LVDT plunger tracks mechanical deflection."),
        ("2. Real-Time MCU Conversion", "The STM32 microcontroller samples the DFRobot ADC over I2C2 (60 ms non-blocking wait per channel) and applies an in-situ 3-sample median filter on Channel 1 to reject impulse spikes. Simultaneously, the MCU polls the Micro-Epsilon controller over USART3 at 256000 baud 9E1 and parses the 17-byte binary response frame."),
        ("3. Serial Packet Telemetry", "Every 50 ms (20 Hz), the STM32 formats calibrated load (N), tare-shifted displacement (mm), and a bitmask error status into a single CSV string ($<load>,<disp>,<status>\\r\\n) and transmits it non-blocking over USART2 (115200 baud 8N1) via the ST-Link virtual COM port."),
        ("4. Host Ingestion & Signal Emission", "On the Raspberry Pi, a dedicated background QThread (SerialManager) reads newline-delimited strings from /dev/ttyACM0. It validates framing, extracts numeric values, flags sensor fault bits, and emits the new_data(timestamp, load, disp) Qt signal to the GUI thread."),
        ("5. Live Visualization & Analysis", "The MainWindow slot consumes the signal, applies user calibration multipliers (settings.get), updates digital readouts, appends data points to the 100,000-point GraphManager circular buffer, and repaints the active pyqtgraph mode (throttled to save CPU)."),
        ("6. Batch Persistence (SQLite WAL)", "If a test is active, points are pushed into the DataLogger in-memory buffer. Every 100 points, points are committed in a single atomic SQL transaction to test_data.db under Write-Ahead Logging (WAL) mode on the /mnt/data partition, minimizing flash memory wear on the SD card."),
    ]
    add_def_table(doc, data_pipeline_steps)

    add_section_heading(doc, "1.3", "Micro-Epsilon LVDT Serial Acquisition Chain")
    doc.add_paragraph(
        "The Micro-Epsilon induSENSOR DTD-10G8 controller communicates using a proprietary master-slave binary protocol over RS-485. The STM32 USART3 peripheral is configured for 256000 baud, 9 data bits, Even parity, and 1 stop bit (9E1). Hardware flow control is disabled:"
    )

    add_code_block(
        doc,
        "// STM32 Polling Request Frame (Hexadecimal, 6 Bytes):\n"
        "10 7E 01 4C CB 16\n\n"
        "// Micro-Epsilon Response Frame Structure (17 Bytes):\n"
        "[0..3]   Header Pattern : 0x68 0x0B 0x0B 0x68\n"
        "[4..6]   Protocol Fields: Type & Sub-type indicators\n"
        "[7..10]  Unscaled Float : 32-bit IEEE-754 Single Precision (Unscaled displacement, mm)\n"
        "[11..14] Scaled Float   : 32-bit IEEE-754 Single Precision (Calibrated displacement, mm)\n"
        "[15]     Checksum       : 8-bit arithmetic sum of bytes [4] through [14]\n"
        "[16]     Stop Delimiter : 0x16",
        caption="Micro-Epsilon MSC7xxx Binary Communication Frame"
    )

    doc.add_paragraph(
        "To prevent frame desynchronization from line reflections or noise, the MCU implements a 256-byte circular ring buffer in HAL_UART_RxCpltCallback. When the buffer reaches 17 bytes, MicroEpsilon_Process scans for the start sequence 0x68 0x0B 0x0B 0x68 and terminating byte 0x16. It validates the 8-bit checksum against byte 15. If valid, memcpy extracts the IEEE-754 floats directly. If the sensor fails to respond within 45 ms, the state machine resets to idle."
    )

    add_section_heading(doc, "1.4", "DFRobot 15-Bit ADC Load Measurement Chain")
    doc.add_paragraph(
        "The load cell amplifier outputs an analog voltage in the 0 to 10 V range. It connects to Channel 1 of a DFRobot Gravity 15-bit ADC module (ADS1115 derivative) interfaced to the STM32 via I2C2 at standard 100 kHz clock speed:"
    )

    adc_timing_defs = [
        ("I2C Bus Address", "7-bit slave address 0x4B (transmitted as 0x96 write address: 0x4B << 1)."),
        ("Channel Selection Register", "Register 0x20. Writing current_channel (0x01 for load cell) initiates conversion on the ADC."),
        ("Channel Data Register", "Register 0x31. Read operation returns 3 consecutive bytes containing a 24-bit raw value (ad_value = (B0 << 16) | (B1 << 8) | B2)."),
        ("Voltage Scaling", "voltage_mv = ad_value / 100.0f; voltage_v = voltage_mv / 1000.0f. The ADC maps full-scale 10.0 V directly to millivolts."),
        ("Force Conversion Equation", "weight_kg = (voltage_v / 10.0f) * 2943.0f. Converts 0 to 10 V linear output to 0 to 2943 Newtons (300 kgf equivalent: 300 * 9.81 N)."),
        ("Non-Blocking State Wait", "The state machine executes State 0 (command write), delays 60 ms without blocking the main CPU loop, then executes State 1 (data register read)."),
        ("3-Sample Median Filter", "Stores 3 consecutive Channel 1 readings in ch1_hist[3]. Sorts the trio and selects sorted[1] as the median, completely eliminating single-cycle EMI spikes."),
    ]
    add_def_table(doc, adc_timing_defs)

    add_section_heading(doc, "1.5", "Telemetry Message Format and Framing")
    doc.add_paragraph(
        "The serial communication link between the STM32 microcontroller and the Raspberry Pi runs over the ST-Link virtual COM port (USART2) at 115200 baud, 8 data bits, no parity, 1 stop bit (8N1). Packets are human-readable ASCII CSV strings formatted as follows:"
    )

    add_code_block(
        doc,
        "// Telemetry Line Syntax:\n"
        "$<Load_N>,<Disp_mm>,<Status_Bitmask>\\r\\n\n\n"
        "// Example Packet Transmission:\n"
        "$145.20,1.245,0\\r\\n\n\n"
        "// Status Bitmask Bit Allocation:\n"
        "Bit 0 (0x01) : Displacement Sensor Error (Displacement value is NaN or Infinite)\n"
        "Bit 1 (0x02) : Load Cell ADC Error (Load value is NaN or Infinite)\n"
        "Bit 2 (0x04) : Micro-Epsilon Communication Timeout (No response frame within 100 ms)",
        caption="USART2 Telemetry Packet Format and Error Bitmask"
    )

    add_section_heading(doc, "1.6", "Multithreading and Process Model")
    doc.add_paragraph(
        "The software architecture enforces strict decoupling between hardware communication, data persistence, and graphical rendering:"
    )

    thread_defs = [
        ("Wayland Compositor (Cage)", "Cage runs as a minimal single-application Wayland compositor directly on TTY1 without a desktop environment. Manages display scaling, fullscreen kiosk presentation, and touch event routing."),
        ("GUI Main Thread (PySide6)", "Executes the Qt event loop, processes finger tap events on TouchLineEdit widgets, drives QTimer tickers (recording duration, auto-stop tracking), and renders pyqtgraph plot updates."),
        ("Serial Acquisition Thread (SerialManager)", "Dedicated QThread running a continuous blocking read loop on pyserial. Deserializes incoming telemetry lines and dispatches thread-safe Qt signals (new_data, connection_status_changed). Never directly touches GUI widgets."),
        ("SQLite Storage Engine (DataLogger)", "Thread-safe data logging engine guarded by threading.Lock. Implements Write-Ahead Logging (WAL) and synchronous=FULL pragmas. Buffers data points in an internal queue and flushes 100-sample batches atomically."),
    ]
    add_def_table(doc, thread_defs)

    add_section_heading(doc, "1.7", "Operating Modes and 3-Point Flexural Stress/Strain Analysis")
    doc.add_paragraph(
        "The system is designed specifically for 3-point bend testing of brittle materials (ceramics, glasses). The software supports 4 distinct visualization and analysis modes:"
    )

    math_defs = [
        ("1. Load vs Displacement", "Plots Load (N) on Y-axis against Actuator Displacement (mm) on X-axis. Primary real-time engineering curve displayed during specimen loading."),
        ("2. Load vs Time", "Plots Load (N) against elapsed test time (s). Used to inspect loading rate stability and detect load relaxation or creep behavior."),
        ("3. Displacement vs Time", "Plots Displacement (mm) against elapsed test time (s). Visualizes actuator travel velocity and mechanical stage compliance."),
        ("4. Stress vs Strain", "Converts raw load and displacement into material stress and strain using classical 3-point beam bending mechanics:"),
    ]
    add_def_table(doc, math_defs)

    add_code_block(
        doc,
        "// 3-Point Flexural Mechanics Equations:\n"
        "Flexural Stress (MPa)  : sigma = (3 * F * L) / (2 * b * d^2)\n"
        "Flexural Strain (—)    : epsilon = (6 * D * d) / (L^2)\n\n"
        "Where:\n"
        "  F = Applied Load (Newtons, N)\n"
        "  D = Mid-span Displacement (millimeters, mm)\n"
        "  L = Support Span Length (millimeters, mm)\n"
        "  b = Specimen Width (millimeters, mm)\n"
        "  d = Specimen Thickness / Height (millimeters, mm)",
        caption="Three-Point Flexural Stress and Strain Mechanics Equations"
    )

    doc.add_paragraph(
        "For brittle ceramics, failure occurs catastrophically at peak stress. The analysis engine automatically identifies the Break Point at peak stress, rejects post-fracture phantom displacement, fits the Flexural Modulus (E) over the linear elastic region using a rolling R^2 linear regression scan, and computes the modulus fit line."
    )

    # =========================================================================
    # CHAPTER 2: STM32 NUCLEO FIRMWARE ARCHITECTURE
    # =========================================================================
    add_chapter_heading(doc, 2, "Microcontroller Firmware Guide (STM32F446RE)")

    add_callout(
        doc, "WARNING", "HARDWARE INDEPENDENT WATCHDOG REFRESH TIMINGS",
        "The firmware configures the STM32 Independent Watchdog (IWDG) with a 64 prescaler and a 4095 reload register value, establishing a strict 8.19-second hardware reset window. The while(1) main loop must call HAL_IWDG_Refresh(&hiwdg) continuously. Any blocking call, infinite loop, or unhandled I2C bus hang exceeding 8.19 seconds forces an unannounced hardware MCU reset, disconnecting the host serial port. Never insert blocking HAL_Delay calls inside the main execution loop."
    )

    add_section_heading(doc, "2.1", "Microcontroller Hardware and Clock Configuration")
    doc.add_paragraph(
        "The firmware executes on an STM32F446RE ARM Cortex-M4 microcontroller (Nucleo-64 board). The clock tree is driven by the internal 16 MHz High-Speed Internal (HSI) RC oscillator coupled to the main Phase-Locked Loop (PLL), configured as follows:"
    )

    clk_params = [
        ("Oscillator Source", "HSI (High-Speed Internal 16 MHz RC oscillator)"),
        ("PLL M Divider", "16 (VCO Input Clock = 16 MHz / 16 = 1.0 MHz)"),
        ("PLL N Multiplier", "336 (VCO Output Clock = 1.0 MHz * 336 = 336.0 MHz)"),
        ("PLL P Divider", "RCC_PLLP_DIV4 (SYSCLK = 336.0 MHz / 4 = 84.0 MHz)"),
        ("Flash Latency", "FLASH_LATENCY_2 (Two wait states required for 84 MHz operation at Scale 3)"),
        ("AHB Prescaler", "DIV1 (HCLK = 84.0 MHz CPU and DMA clock)"),
        ("APB1 Prescaler", "DIV2 (PCLK1 = 42.0 MHz peripheral clock, max allowable for APB1)"),
        ("APB2 Prescaler", "DIV1 (PCLK2 = 84.0 MHz high-speed peripheral clock)"),
    ]
    add_def_table(doc, clk_params)

    add_section_heading(doc, "2.2", "Peripheral Assignment and Hardware Pin Map")
    doc.add_paragraph(
        "The following table documents all configured peripherals, operating modes, baud rates, pin mappings, and physical hardware connections:"
    )

    headers_periph = ["Peripheral", "Role / Target", "Mode / Interrupt", "Baud / Speed", "Hardware Pins", "Framing / Protocol"]
    rows_periph = [
        ["USART2", "Host Telemetry (RPi 5)", "HAL_UART_Transmit_IT", "115200 bps", "PA2 (TX), PA3 (RX)", "8 Data, No Parity, 1 Stop (8N1)"],
        ["USART3", "Micro-Epsilon LVDT Sensor", "HAL_UART_Receive_IT", "256000 bps", "PC10 (TX), PC11 (RX)", "9 Data, Even Parity, 1 Stop (9E1)"],
        ["I2C2", "DFRobot 15-bit ADC", "Polling (HAL_I2C_Mem)", "100 kHz (Std)", "PB10 (SCL), PB3 (SDA)", "7-Bit Address 0x4B, No Stretch"],
        ["IWDG", "System Watchdog", "Hardware Timer", "32 kHz LSI", "Internal", "Prescaler 64, Reload 4095 (~8.19 s)"],
        ["GPIO", "User LED (LD2)", "Push-Pull Output", "Low Speed", "PA5 (Green LED)", "Toggles on activity / debug heartbeat"],
        ["GPIO", "User Pushbutton (B1)", "Falling Edge EXTI", "Input", "PC13 (Blue Button)", "Reserved / manual trigger"],
    ]
    add_header_table(doc, headers_periph, rows_periph, col_widths=[Inches(0.9), Inches(1.3), Inches(1.3), Inches(0.9), Inches(1.1), Inches(1.2)])

    add_section_heading(doc, "2.3", "I2C Bus Fault Recovery Mechanism (I2C2_Bus_Recovery)")
    doc.add_paragraph(
        "Industrial electrical transients and electrical contact bounce can cause I2C slave devices to become desynchronized, holding the SDA data line low indefinitely. Standard HAL calls fail permanently under this condition. The firmware implements a dedicated hardware recovery procedure executed if 3 consecutive I2C transaction errors occur:"
    )

    recovery_steps = [
        ("Step 1: Peripheral De-Initialization", "Calls HAL_I2C_DeInit(&hi2c2) to release internal peripheral registers and disconnect pins from the I2C hardware macrocell."),
        ("Step 2: GPIO Reconfiguration", "Reconfigures PB10 (SCL) and PB3 (SDA) as standard Open-Drain General Purpose Outputs (GPIO_MODE_OUTPUT_OD) with no internal pull resistors."),
        ("Step 3: Nine-Clock Toggle Sequence", "Sets SDA High, then clocks SCL High and Low 9 consecutive times with 1 ms delays. This satisfies the I2C standard protocol to force any slave stuck in a read cycle to release the SDA bus."),
        ("Step 4: Manual Stop Condition", "Drives SCL High, waits 1 ms, then drives SDA High, issuing an explicit I2C STOP condition onto the physical bus."),
        ("Step 5: Peripheral Re-Initialization", "Calls MX_I2C2_Init() to restore the hardware I2C2 peripheral to normal 100 kHz master operation."),
    ]
    add_def_table(doc, recovery_steps)

    add_section_heading(doc, "2.4", "Cooperative Non-Blocking Main Scheduler")
    doc.add_paragraph(
        "The firmware executes inside an infinite while(1) loop governed by non-blocking software timers evaluated against HAL_GetTick(). This architecture guarantees that no single slow peripheral starves other acquisition tasks:"
    )

    sched_rows = [
        ("Watchdog Refresh (Continuous)", "Executes HAL_IWDG_Refresh(&hiwdg) on every single loop iteration, resetting the 8.19-second countdown timer."),
        ("DFRobot ADC Process (60 ms State Switch)", "Advances the ADC state machine. State 0 sends a 1-byte register request. State 1 waits until tick - last_adc_tick >= 60 ms, reads 3 bytes, applies median filtering, and toggles current_channel between 1 and 2."),
        ("Micro-Epsilon Process (50 ms Poll Interval)", "Advances the LVDT state machine. Every 50 ms, transmits the 6-byte request frame over USART3. Evaluates incoming ring-buffer bytes; extracts displacement upon valid checksum."),
        ("Host Telemetry Transmission (20 Hz)", "Constructs the CSV telemetry string ($%.2f,%.3f,%d\\r\\n), evaluates error bits (NaN checks and 100 ms sensor timeout), and transmits non-blocking over USART2 via UART2_SendNonBlocking."),
    ]
    add_def_table(doc, sched_rows)

    add_section_heading(doc, "2.5", "Sensor Offsets, Calibration Factors, and Physical Datums")
    doc.add_paragraph(
        "Two critical physical scaling factors are hard-coded in the firmware:"
    )

    cal_facts = [
        ("Micro-Epsilon Tare Offset (me_tare_offset = -6.202f)", "Defined at line 64: static float me_tare_offset = -6.202f. Subtracted in MicroEpsilon_GetScaledValue() (return scaled_val - me_tare_offset). This represents an intentional design choice by the author establishing the mechanical zero datum for the fully relaxed MOR flexural fixture probe."),
        ("Load Full-Scale Factor (2943.0 N)", "Defined at line 547: weight_kg = (voltage_v / 10.0f) * 2943.0f. Note that while the variable name is weight_kg, the equation multiplies directly by 2943.0 Newtons, mapping the 0 to 10 V amplifier output to 300 kgf (300 * 9.81 = 2943 N)."),
    ]
    add_def_table(doc, cal_facts)

    add_section_heading(doc, "2.6", "Firmware Build, Flash, and Verification Runbook")
    doc.add_paragraph(
        "To compile, flash, and verify the STM32 firmware from a clean development workstation:"
    )

    fw_steps = [
        ("Step 1: Open Project in STM32CubeIDE", "Launch STM32CubeIDE (v1.14 or later). Import the project containing stgobain_lc_rpi_main.c. Confirm HAL library version STM32F4 HAL v1.8.x."),
        ("Step 2: Build Firmware", "Select Release configuration. Click Project -> Build Project (Ctrl+B). Verify zero compilation errors and zero warnings."),
        ("Step 3: Connect ST-Link Probe", "Connect the STM32 Nucleo-64 board to the workstation via a USB Type-A to Mini-B cable. Confirm the ST-Link status LED lights solid red/green."),
        ("Step 4: Flash Microcontroller", "Click Run -> Run (Ctrl+F11) or execute via STM32CubeProgrammer CLI: STM32_Programmer_CLI -c port=SWD -w firmware.bin 0x08000000 -v -rst."),
        ("Step 5: Verify Telemetry Stream", "Open a terminal emulator (PuTTY, Tera Term) at 115200 baud, 8N1. Confirm steady 20 Hz output of CSV frames: $0.00,0.000,0. Disconnect terminal before reconnecting to the Raspberry Pi."),
    ]
    add_def_table(doc, fw_steps)

    # =========================================================================
    # CHAPTER 3: TOUCHSCREEN GUI SOFTWARE ARCHITECTURE
    # =========================================================================
    add_chapter_heading(doc, 3, "Touchscreen GUI Software Architecture (PySide6 / Qt6)")

    add_callout(
        doc, "NOTE", "CORPORATE DESIGN SYSTEM AND DPI COMPLIANCE",
        "The touchscreen interface is built on PySide6 (Qt6 for Python) styled in accordance with InsituMicron corporate design guidelines (Primary Teal #005b7f, Accent Teal #00a8cc). In main.py, QT_AUTO_SCREEN_SCALE_FACTOR=1 is asserted. Under Windows development environments, Qt scales coordinates by ~1.3x, leaving ~991 physical pixels. All form pages are wrapped in transparent QScrollArea containers to prevent QStackedWidget minimum size clipping. On the production Raspberry Pi, scaling is 1.0x."
    )

    add_section_heading(doc, "3.1", "Software Architecture and Module Inventory")
    doc.add_paragraph(
        "The Python codebase contains 11 functional modules cleanly decoupled across responsibilities:"
    )

    headers_mod = ["Module File", "Primary Class / Ownership", "Dependencies", "Architectural Constraints"]
    rows_mod = [
        ["main.py", "QApplication Lifecycle & Kiosk Mode", "PySide6, theme, ui_layout", "Entry point; sets DPI env vars; must not contain business logic."],
        ["ui_layout.py", "MainWindow (UI Coordinator)", "PySide6, graph_manager, serial_manager, data_logger", "Composition root; builds pages, handles auto-stop & CTD."],
        ["serial_manager.py", "SerialManager (QThread)", "pyserial, PySide6.QtCore", "Dedicated thread for UART read; never touches UI widgets directly."],
        ["graph_manager.py", "GraphManager (Plot Controller)", "pyqtgraph, numpy, PySide6", "Maintains 100k ring buffer; renders active mode with downsampling."],
        ["data_logger.py", "DataLogger (SQLite Engine)", "sqlite3, pandas, threading", "Thread-safe WAL storage; auto-recovers interrupted tests on boot."],
        ["flexural_analysis.py", "FlexuralAnalysisEngine (Pure Math)", "numpy, scipy.stats", "Zero Qt dependencies; computes modulus, break stress/strain."],
        ["pdf_reporter.py", "PDFReporter (Certificate Builder)", "reportlab", "Generates single-page PDF test reports with metadata and graphs."],
        ["settings_manager.py", "SettingsManager (JSON Store)", "json, os, platform", "Stores calibration factors in /mnt/data/ to survive OverlayFS."],
        ["virtual_keyboard.py", "NumpadDialog, TextInputDialog", "PySide6.QtWidgets", "Touchscreen popup keyboards for headless kiosk operation."],
        ["usb_utils.py", "detect_usb_drive Utility", "psutil, os, platform", "Detects automounted pendrives; ignores STM32 virtual flash partitions."],
        ["theme.py / constants.py", "Design Tokens & Global QSS", "None", "Defines primary/accent colors, button heights, and font rules."],
    ]
    add_header_table(doc, headers_mod, rows_mod, col_widths=[Inches(1.2), Inches(1.5), Inches(1.5), Inches(2.07)])

    add_section_heading(doc, "3.2", "Composition Root and Application Lifecycle")
    doc.add_paragraph(
        "When the application boots on the Raspberry Pi 5 under the Cage compositor, the execution sequence progresses as follows:"
    )

    boot_steps = [
        ("1. Boot Diagnostic Logging", "data_logger.log_kiosk_status('GUI BOOT STARTED') appends an ISO timestamp to /mnt/data/kiosk_status.log. atexit registers clean shutdown logging."),
        ("2. Touch Synthesis Initialization", "QApplication.setAttribute(Qt.AA_SynthesizeMouseForUnhandledTouchEvents, True) ensures capacitive touch screen taps synthesize standard mouse clicks for QWidget buttons."),
        ("3. Global Styling Injection", "app.setStyleSheet(GLOBAL_STYLESHEET) applies corporate stylesheets across all buttons, tables, and frames. Font default is set to Segoe UI 12 pt (falling back to sans-serif on Linux)."),
        ("4. MainWindow Instantiation", "MainWindow initializes SettingsManager, DataLogger (triggering WAL migration and auto-recovery), GraphManager, and SerialManager."),
        ("5. Layout Construction", "setup_layout() instantiates the left sidebar (logo, 4 menu items, Start/Stop buttons, timer label, connection indicator) and the 4-page QStackedWidget."),
        ("6. Hardware Worker Launch", "serial_manager.start_reading() launches the QThread background serial scanning loop."),
        ("7. Kiosk Fullscreen Presentation", "If os.environ.get('KIOSK_MODE') == '1', app.setOverrideCursor(Qt.BlankCursor) hides the mouse cursor and window.showFullScreen() occupies the entire 1280x800 display."),
    ]
    add_def_table(doc, boot_steps)

    add_section_heading(doc, "3.3", "Threading Model and Qt Signal/Slot Catalogue")
    doc.add_paragraph(
        "Thread-safe inter-process communication relies strictly on Qt Signal/Slot mechanisms across the thread boundary:"
    )

    headers_sig = ["Signal Name", "Payload Signature", "Emitter", "Receiver / Slot", "Description / Behavior"]
    rows_sig = [
        ["new_data", "float, float, float\n(time_s, load_N, disp_mm)", "SerialManager\n(QThread)", "MainWindow.update_graph\n(GUI Thread)", "Emitted at 20 Hz on valid telemetry packet. Updates readouts, feeds GraphManager, logs to SQLite."],
        ["connection_status_changed", "bool, str\n(is_connected, message)", "SerialManager\n(QThread)", "MainWindow._on_connection_changed\n(GUI Thread)", "Emitted on port connect, disconnect, or sensor fault bitmask. Updates UI status indicator and logs."],
        ["btn_tare_load.clicked", "None", "MainWindow UI", "MainWindow._tare_load", "Captures _last_raw_load as load_offset. Tares live force readout to 0 N."],
        ["btn_tare_disp.clicked", "None", "MainWindow UI", "MainWindow._tare_disp", "Captures _last_raw_disp as disp_offset. Tares live stroke readout to 0.000 mm."],
    ]
    add_header_table(doc, headers_sig, rows_sig, col_widths=[Inches(1.3), Inches(1.2), Inches(1.1), Inches(1.3), Inches(1.37)])

    add_section_heading(doc, "3.4", "Real-Time Plotting Engine and Mode Switching (GraphManager)")
    doc.add_paragraph(
        "The real-time plotting subsystem wraps pyqtgraph.PlotWidget with custom industrial styling: white background, thick #2c2f33 dark axes, 18 pt bold title, and a custom overlay Reset button that enables auto-range. The engine manages an internal double-ended queue (collections.deque(maxlen=100000)) storing all raw time, load, and displacement tuples since the test began."
    )

    doc.add_paragraph(
        "When the operator switches between the 4 segmented graph buttons (Load vs Disp, Load vs Time, Disp vs Time, Stress vs Strain), the plot widget does not lose data. _switch_mode() updates axis titles and instantly replots the entire in-memory history from the deque. If the buffer exceeds 5,000 points, an automatic slicing downsampler (x[::step]) activates to guarantee a consistent 60 FPS UI refresh without GPU choking on the Raspberry Pi."
    )

    add_section_heading(doc, "3.5", "Persistent SQLite Storage and Crash Recovery (DataLogger)")
    doc.add_paragraph(
        "Test metadata and high-frequency time-series points are stored in an embedded SQLite database (test_data.db). The database schema comprises two indexed tables:"
    )

    add_code_block(
        doc,
        "// SQLite Database Schema:\n"
        "CREATE TABLE tests (\n"
        "    test_id       INTEGER PRIMARY KEY AUTOINCREMENT,\n"
        "    name          TEXT NOT NULL,\n"
        "    started_at    TEXT NOT NULL,\n"
        "    ended_at      TEXT,\n"
        "    duration_s    REAL,\n"
        "    notes         TEXT DEFAULT '',\n"
        "    sample_name   TEXT DEFAULT '',\n"
        "    test_number   TEXT DEFAULT '',\n"
        "    business_type TEXT DEFAULT '',\n"
        "    length_mm     REAL,\n"
        "    width_mm      REAL,\n"
        "    thickness_mm  REAL,\n"
        "    temperature_c REAL\n"
        ");\n\n"
        "CREATE TABLE data_points (\n"
        "    id          INTEGER PRIMARY KEY AUTOINCREMENT,\n"
        "    test_id     INTEGER NOT NULL,\n"
        "    timestamp_s REAL NOT NULL,\n"
        "    load_val    REAL NOT NULL,\n"
        "    disp_val    REAL NOT NULL,\n"
        "    FOREIGN KEY (test_id) REFERENCES tests(test_id)\n"
        ");\n"
        "CREATE INDEX idx_dp_test ON data_points(test_id);",
        caption="SQLite Database Schema for Test Metadata and Time-Series Points"
    )

    doc.add_paragraph(
        "To survive sudden power disconnection, the database executes PRAGMA journal_mode=WAL and PRAGMA synchronous=FULL. Rolling backups (test_data.db.bak1, .bak2, .bak3) are created prior to opening. On initialization, _auto_recover_tests() executes SELECT test_id FROM tests WHERE ended_at IS NULL. For any interrupted test, it queries MAX(timestamp_s), sets duration_s, appends _RECOVERED to the test name, and closes the record cleanly."
    )

    add_section_heading(doc, "3.6", "Pure-Math 3-Point Flexural Analysis Engine (flexural_analysis.py)")
    doc.add_paragraph(
        "The analytical engine is completely decoupled from Qt and GUI dependencies, allowing headless automated verification. The algorithm operates in 5 deterministic phases:"
    )

    ana_phases = [
        ("Phase 1: Input Validation & Auto-Inversion", "Validates positive span length, width, and height. If the test was run with inverted polarities (min(load) < 0 and abs(min) > max), it automatically inverts load and displacement arrays and logs a warning."),
        ("Phase 2: Stress & Strain Conversion", "Converts raw load and displacement into stress (MPa) and strain (mm/mm) arrays using standard beam bending equations."),
        ("Phase 3: Break Detection (Peak Stress)", "Identifies peak stress via np.argmax(stress). For brittle ceramics, failure occurs at peak load. Any post-peak displacement is flagged as phantom displacement from the loading pin penetrating broken fragments and excluded from modulus fitting."),
        ("Phase 4: Rolling R^2 Linear Elastic Scan", "Excludes initial toe strain (grip seating noise below toe_strain_threshold = 0.001). Applies a sliding window linear regression scan across the pre-peak region to find the maximum slope with R^2 >= 0.995."),
        ("Phase 5: Flexural Modulus Computation", "Executes scipy.stats.linregress over the detected linear elastic window to compute the Young's Flexural Modulus (slope in MPa) and generate the modulus line for visual overlay."),
    ]
    add_def_table(doc, ana_phases)

    add_section_heading(doc, "3.7", "Automated PDF Report Generation (pdf_reporter.py)")
    doc.add_paragraph(
        "Generates formal test certificates using ReportLab. The document compiles onto a single standard Letter page containing the corporate header logo, test metadata table (Sample ID, Test Number, Business Type, Furnace Temperature, Dimensions), mechanical properties summary table (Flexural Modulus E, Break Stress, Break Strain), high-resolution rendered Stress-Strain curve image, and optional operator comments box."
    )

    add_section_heading(doc, "3.8", "Security Lock, Protected Calibration, and Admin Access Control")
    doc.add_paragraph(
        "Sensor calibration factors and auto-break parameters directly dictate test validity. Access is restricted behind an administrative security lock indicated by a color-coded badge on the Settings page:"
    )

    lock_states = [
        ("LOCKED (Red Badge)", "Default startup state. Load calibration, displacement calibration, auto-start threshold, auto-stop drop percentage, and CTD threshold are strictly read-only."),
        ("ADMIN (Green Badge)", "Unlocked state. Clicking the badge opens a TouchLineEdit modal prompting for credentials. Once verified, settings become editable and changes are saved immediately to hmi_settings.json."),
        ("Credential Storage & Custody", "Admin credentials are hard-coded in ui_layout.py (lines 37-38). In accordance with corporate security rules, actual credentials are not recorded in this manual. They are controlled exclusively by the system administrator."),
    ]
    add_def_table(doc, lock_states)

    # =========================================================================
    # CHAPTER 4: HARDWARE, ELECTRONICS & BILL OF MATERIALS
    # =========================================================================
    add_chapter_heading(doc, 4, "Hardware, Electronics & Bill of Materials")

    add_callout(
        doc, "DANGER", "EXACT MAINS PROTECTION SEQUENCE & CONTACTOR ISOLATION",
        "MAINS PROTECTION ORDER: 230V AC -> MCB (4A) -> E-Stop (XB5) -> Contactor (LC1E) -> SMPS (24V & 5V).\n"
        "Mains 230 VAC 50 Hz enters through the IEC socket and connects directly to the Schneider A9N1P04C 4A MCB. The switched line passes through the NC contact of the Schneider Harmony XB5AS8444 emergency stop switch before driving the 230V coil of the Schneider LC1E0910M7 contactor. The contactor power poles feed the AC inputs of the Mean Well LRS-150-24 and RS-25-5 SMPS units. When the E-stop is struck, the contactor coil drops out instantly, severing AC power to all SMPS units and de-energizing all DC rails."
    )

    add_section_heading(doc, "4.1", "Electrical Safety, MCB, Emergency Stop & Contactor Interlock")
    doc.add_paragraph(
        "The electrical architecture prioritizes operator safety and equipment protection through the hardware-enforced protection chain:"
    )

    elec_safety_defs = [
        ("1. 230V AC Mains Ingress", "230 VAC, 50 Hz single-phase supply entering through an IEC C14 inlet with chassis ground bonded directly to the powder-coated enclosure earth stud."),
        ("2. MCB Protection (4A)", "Schneider A9N1P04C SP C-Curve ACTI9 10kA 4A Miniature Circuit Breaker provides primary thermal-magnetic overcurrent and short-circuit protection for the system."),
        ("3. Emergency Stop (XB5)", "Schneider Electric Harmony XB5AS8444 mushroom-head latching pushbutton with Normally Closed (NC) contacts wired in series with the contactor coil circuit."),
        ("4. Contactor Interlock (LC1E)", "Schneider Electric LC1E0910M7 3-pole contactor with 230 VAC coil. Closing the contactor connects AC mains to both internal SMPS units. Actuating the E-stop immediately de-energizes the coil, opening all power poles."),
        ("5. Switched DC SMPS Supplies", "Mains AC feeds Mean Well LRS-150-24 (24V SMPS) and Mean Well RS-25-5 (5V SMPS). Cutting contactor power completely kills both 24V and 5V DC supplies."),
        ("Green Start / Red Stop Buttons", "Schneider Harmony XB5AA31N (NO contact green push Start) and XB5AA42N (NC contact red push Stop) wired in a standard latching seal-in contactor control circuit."),
        ("Mains Power Indicator Lamp", "Schneider Electric XB7EV03MPN green LED indicator mounted on the front panel, illuminated whenever the contactor is closed and internal 24V/5V DC rails are live."),
    ]
    add_def_table(doc, elec_safety_defs)

    add_section_heading(doc, "4.2", "Power Distribution Architecture (24V and 5V SMPS)")
    doc.add_paragraph(
        "The enclosure houses two dedicated industrial switch-mode power supplies (SMPS) manufactured by Mean Well:"
    )

    smps_defs = [
        ("Mean Well LRS-150-24 (24V DC / 6.5A)", "High-efficiency 150W metal chassis SMPS. Powers the Micro-Epsilon MSC7xxx LVDT controller, dual JIGO 80x80x25mm cooling fans, and front panel indicator circuits. Features short-circuit, overload, and overvoltage protection."),
        ("Mean Well RS-25-5 (5V DC / 5.0A)", "Compact 25W metal chassis SMPS. Powers the Waveshare 10.1\" capacitive touch display, DFRobot ADC analog rail, and internal interface electronics. Relieves the Raspberry Pi USB bus from high current draw."),
        ("Raspberry Pi 27W USB-C Power Supply", "Official Raspberry Pi 27W (5.1V / 5.0A) power adapter dedicated exclusively to the Raspberry Pi 5 to prevent undervoltage throttling during intensive compute or graphing bursts."),
    ]
    add_def_table(doc, smps_defs)

    add_section_heading(doc, "4.3", "Complete 41-Item Electrical Bill of Materials (BOM)")
    doc.add_paragraph(
        "The complete, verified 41-item bill of materials from St Gobain Project 2 BOM Electrical.xlsx is detailed below. Note that there is no proprietary HMI panel; the touchscreen interface is formed by the Waveshare 10.1\" display and Raspberry Pi 5:"
    )

    headers_bom = ["#", "Part Name", "Purpose / Role in Architecture", "Manufacturer", "Qty"]
    rows_bom = [
        ["1", "Waveshare 10.1inch Capacitive Touch Display", "Touchscreen Display Panel (1280x800 IPS, Optical Bond)", "Waveshare", "1"],
        ["2", "Raspberry Pi 5 4GB", "Main Embedded Host Controller (Hosts PySide6 GUI & Cage)", "Raspberry Pi", "1"],
        ["3", "Raspberry Pi 5 Active Cooler", "Thermal Management for BCM2712 SoC", "Raspberry Pi", "1"],
        ["4", "Raspberry Pi 27W USB-C Power Supply", "Dedicated Host Power Adapter", "Raspberry Pi", "1"],
        ["5", "SanDisk Cruzer Blade 8GB USB Pen Drive", "Test Data Export Media", "SanDisk", "1"],
        ["6", "Official Micro-HDMI to Standard HDMI Cable (2m)", "Video Signal to Waveshare Display (HDMI-1 Port)", "Raspberry Pi", "1"],
        ["7", "STM32 NUCLEO-F446RE", "Real-Time Sensor Microcontroller", "STMicroelectronics", "1"],
        ["8", "Micro Epsilon LVDT induSENSOR DTD-10G8", "Displacement Transducer & Controller", "Micro-Epsilon", "1"],
        ["9", "Mean Well LRS-150-24 SMPS", "24V DC Main Sensor & Fan Supply", "Mean Well", "1"],
        ["10", "Mean Well RS-25-5 SMPS", "5V DC Logic & Display Supply", "Mean Well", "1"],
        ["11", "Schneider Electric XB5AS8444 E-Stop", "Emergency Stop Latching Pushbutton (NC Coil Cutoff)", "Schneider Electric", "1"],
        ["12", "Schneider A9N1P04C SP C-Curve MCB", "4A Single Pole Circuit Breaker (Mains Protection)", "Schneider Electric", "1"],
        ["13", "Schneider Electric LC1E0910M7 Contactor", "230V AC Coil Power Contactor (Mains Interlock)", "Schneider Electric", "1"],
        ["14", "Waveshare Rail-mount TTL to RS485 Converter", "Galvanic Isolation for USART3 RS485", "Waveshare", "3"],
        ["15", "DFRobot Gravity: 0-10V 15-Bit Dual ADC", "High-Precision I2C Load Cell ADC (0x4B)", "DFRobot", "1"],
        ["16", "4-pin JST PH 2mm Cable", "I2C Interconnect for ADC Module", "Generic", "1"],
        ["17", "BNC Plug/Jack with Terminal Block", "Conditioned Load Cell Cable Interconnect", "Generic", "1"],
        ["18", "Schneider XB5AA42N Red Push Button", "NC Contact Mains Stop Button", "Schneider Electric", "1"],
        ["19", "Schneider XB5AA31N Green Push Button", "NO Contact Mains Start Button", "Schneider Electric", "1"],
        ["20", "Schneider XB7EV03MPN Green Indicator", "Front Panel Mains Power ON Indicator", "Schneider Electric", "1"],
        ["21", "Havells 6A 3-Pin Flat Plug Top", "Mains Input Connection", "Havells", "1"],
        ["22", "3-Core Power Cable (2m)", "Internal Mains Wiring for SMPS Units", "Generic", "2"],
        ["23", "3-Core Shielded Cable (1m)", "Displacement Sensor Signal Wiring", "Generic", "1"],
        ["24", "1.5 mm^2 Power Wire (Red/Black 5m)", "DC Power Distribution Wiring", "Generic", "5"],
        ["25", "Jumper Wires (Assorted)", "Prototyping & Signals Interconnect", "Generic", "1"],
        ["26", "Single Strand Wires", "Internal Zero-PCB Routing", "Generic", "1"],
        ["27", "USB Cable (Type-A to Mini-B)", "ST-Link Telemetry to RPi 5", "Generic", "1"],
        ["28", "DB9 Female Terminal Conversion Board", "Serial Interfacing Hardware", "Generic", "1"],
        ["29", "USB to RS232 Adapter Cable (1.5m)", "Firmware Diagnostics / Service Port", "Waveshare", "1"],
        ["30", "USB Panel Extender Cable", "Chassis Bulkhead USB Drive Port", "Zebronics", "1"],
        ["31", "Female Header Pins 2x20 Pin Double Row", "MCU Board Mating Headers", "Generic", "2"],
        ["32", "4-Pin 5.08mm Pluggable Screw Terminals", "Chassis Signal & Sensor Breakout", "Generic", "4"],
        ["33", "KF301 2-Pin 5.08mm Screw Terminals", "DC Power Ingress Breakout", "Generic", "1"],
        ["34", "Fork / Crimp Terminals (Assorted)", "Terminal Strip Power Termination", "Generic", "1"],
        ["35", "Custom Carrier PCB Fabrication", "Interface Board Integrating MCU & Ports", "Teqtis", "1"],
        ["36", "Wire Ferrules (Pack of 50)", "Stranded Wire Termination & Protection", "Generic", "50"],
        ["37", "Aviator Connector - 5 Pin (GX16-5)", "External LVDT Sensor Bulkhead", "Generic", "1"],
        ["38", "Aviator Connector - 3 Pin (GX16-3)", "External DC Auxiliary Bulkhead", "Generic", "1"],
        ["39", "WAGO 221-413 (3-Pin Terminal)", "AC Mains Line Splicing", "WAGO", "1"],
        ["40", "WAGO 221-415 (5-Pin Terminal)", "DC Ground and +24V Distribution", "WAGO", "2"],
        ["41", "JIGO 80x80x25mm 24VDC Fan (140mA)", "Enclosure Forced Air Ventilation", "JIGO", "2"],
    ]
    add_header_table(doc, headers_bom, rows_bom, col_widths=[Inches(0.4), Inches(2.2), Inches(1.97), Inches(1.1), Inches(0.6)])

    add_section_heading(doc, "4.4", "Sensor Interconnects, Galvanic Isolation & Signal Routing")
    doc.add_paragraph(
        "Industrial testing environments suffer from severe electromagnetic interference (EMI) originating from nearby hydraulic pumps and furnace heaters. The DAQ hardware incorporates three isolation barriers:"
    )

    iso_defs = [
        ("RS-485 Galvanic Isolation", "The Micro-Epsilon LVDT serial lines pass through a Waveshare Rail-Mount Galvanic Isolated Converter before reaching STM32 USART3, eliminating ground loops between the remote sensor frame and the controller enclosure."),
        ("Shielded Sensor Cabling", "The LVDT probe cable is 100% braided shielded copper terminated via a metal 5-pin GX16 aviator connector with shield drain tied directly to the chassis earth ground lug."),
        ("Differential Load Cell Signal Path", "The 0 to 10 V load conditioner signal enters via a shielded BNC bulkhead directly to the DFRobot ADC terminal block, minimizing noise coupling onto the high-resolution analog input."),
    ]
    add_def_table(doc, iso_defs)

    add_section_heading(doc, "4.5", "Controller Enclosure, Connectors, and Pinout Reference")
    doc.add_paragraph(
        "External connections on the powder-coated enclosure bulkhead are standardized to prevent incorrect cabling:"
    )

    conn_defs = [
        ("GX16 5-Pin Aviator (LVDT)", "Pin 1: +24V DC Sensor Supply | Pin 2: Ground | Pin 3: RS-485 Data A (+) | Pin 4: RS-485 Data B (-) | Pin 5: Cable Shield Earth."),
        ("BNC Connector (Load Cell)", "Center Pin: Conditioned +0 to 10 V Analog Signal | Outer Shell: Analog Ground (AGND)."),
        ("Front Panel USB Port", "Standard USB 2.0 Type-A bulkhead port extended from Raspberry Pi 5 USB 3.0 port for operator pendrive exports."),
        ("AC Mains Ingress", "IEC C14 power inlet socket with integrated 5x20mm fuse holder adjacent to the main ACTI9 MCB switch."),
    ]
    add_def_table(doc, conn_defs)

    # =========================================================================
    # CHAPTER 5: INDUSTRIAL KIOSK DEPLOYMENT & OS HARDENING
    # =========================================================================
    add_chapter_heading(doc, 5, "Industrial Kiosk Deployment & OS Hardening")

    add_callout(
        doc, "DANGER", "OVERLAYFS PROTECTS SD CARD FROM HARD POWER CUTS",
        "Industrial operators routinely power off test rigs by switching off mains power without executing an OS shutdown. Under standard Linux, cutting power during a write cycle corrupts flash sectors, rendering the SD card unbootable. To make the system physically indestructible, the OS partition is locked into an immutable Read-Only state using OverlayFS. Persistent files (SQLite database, configuration, logs) reside exclusively on a separate ext4 partition mounted at /mnt/data. Never disable OverlayFS on a production machine except during controlled software upgrades."
    )

    add_section_heading(doc, "5.1", "Operating System and Kiosk Architecture Overview")
    doc.add_paragraph(
        "The software runs on a 64-bit Raspberry Pi OS Lite installation. Standard desktop environments (X11, Wayfire, Labwc, PIXEL) are intentionally stripped out to avoid window manager race conditions and minimize memory footprint. The application is hosted directly by the Cage Wayland compositor, which launches the PySide6 process full-screen and blocks desktop breakout."
    )

    add_section_heading(doc, "5.2", "MicroSD Card Partitioning Scheme (Option B Architecture)")
    doc.add_paragraph(
        "A 64 GB MicroSD card is partitioned into three isolated filesystems following the battle-tested Option B architecture:"
    )

    part_defs = [
        ("Partition 1: /boot/firmware (vfat, 512 MB)", "Contains kernel images, device tree blobs (DTBs), cmdline.txt, and config.txt. Mounted read-only (bootro enabled via raspi-config nonint enable_bootro)."),
        ("Partition 2: / (ext4, 8 GB)", "Contains the complete Raspberry Pi OS Lite operating system, Python virtual environment, dependencies, and application source code. Shielded under OverlayFS; all writes are held in volatile RAM and discarded on reboot."),
        ("Partition 3: /mnt/data (ext4, ~50 GB)", "Dedicated persistent data partition occupying all remaining flash storage. Houses test_data.db, hmi_settings.json, persistent systemd journals, and kiosk_status.log. Survives power cycles unharmed."),
    ]
    add_def_table(doc, part_defs)

    add_section_heading(doc, "5.3", "Battle-Tested Console Autologin & Pre-GUI Mount Script")
    doc.add_paragraph(
        "Background systemd services fight for DRM/KMS permissions on Raspberry Pi 5. Furthermore, /etc/fstab automounts conflict with the OverlayFS shield, causing silent mount failures. The system implements the battle-tested Console Autologin method on TTY1 (raspi-config nonint do_boot_behaviour B2) coupled with explicit partition mounting in ~/.profile right before launching Cage:"
    )

    add_code_block(
        doc,
        "# /home/insitumicron-rpi/.profile:\n"
        "# 1. Ensure persistent partition is mounted to /mnt/data before GUI launch\n"
        "if ! mountpoint -q /mnt/data; then\n"
        "    sudo mount /dev/mmcblk0p3 /mnt/data\n"
        "fi\n\n"
        "# 2. Start Kiosk on TTY1\n"
        "if [ \"$(tty)\" = \"/dev/tty1\" ]; then\n"
        "    export QT_QPA_PLATFORM=wayland\n"
        "    export KIOSK_MODE=1\n"
        "    exec cage -s -- /home/insitumicron-rpi/Pi_HMI/venv/bin/python \\\n"
        "                    /home/insitumicron-rpi/Pi_HMI/main.py\n"
        "fi",
        caption="Battle-Tested ~/.profile Script with Pre-GUI Mount and Cage Launch"
    )

    add_section_heading(doc, "5.4", "Custom Plymouth Boot Splash Configuration")
    doc.add_paragraph(
        "Boot logs and Linux console output are suppressed to present an OEM appliance appearance. Kernel parameters in /boot/firmware/cmdline.txt are set to quiet splash loglevel=0 logo.nologo vt.global_cursor_default=0 console=tty1. In /etc/plymouth/plymouthd.conf, DeviceTimeout=8 is set to force Plymouth to wait for the Raspberry Pi 5 GPU driver (vc4-kms-v3d). A custom Plymouth theme (stgobain) displays final_boot_logo_1280x800.png centered on the display until Cage takes over the framebuffer."
    )

    add_section_heading(doc, "5.5", "Silent USB Storage Automounting (Udev Rules)")
    doc.add_paragraph(
        "When an operator inserts a USB flash drive into the front panel port, udev rule /etc/udev/rules.d/99-usb-mount.rules automatically mounts the filesystem to /media/usb with sync and flush mount options:"
    )

    add_code_block(
        doc,
        "# /etc/udev/rules.d/99-usb-mount.rules:\n"
        "ACTION==\"add\", SUBSYSTEMS==\"usb\", SUBSYSTEM==\"block\", ENV{ID_FS_USAGE}==\"filesystem\", \\\n"
        "  RUN+=\"/usr/bin/systemd-mount -o uid=1000,gid=1000,dmask=000,fmask=000,flush --no-block --automount=yes --collect $devnode /media/usb\"\n\n"
        "ACTION==\"remove\", SUBSYSTEMS==\"usb\", SUBSYSTEM==\"block\", ENV{ID_FS_USAGE}==\"filesystem\", \\\n"
        "  RUN+=\"/usr/bin/systemd-umount /media/usb\"",
        caption="Udev Rule for Silent Background USB Automounting"
    )

    doc.add_paragraph(
        "To prevent false detection, usb_utils.detect_usb_drive() scans mounted partitions and automatically filters out drives smaller than 50 MB (ignoring the virtual flash drive exposed by the STM32 ST-Link) and skips internal OverlayFS mountpoints (root-ro, root-rw, realroot, /mnt/data)."
    )

    add_section_heading(doc, "5.6", "Comprehensive Kiosk Obstacles Overcome & Solutions Log")
    doc.add_paragraph(
        "During development and bring-up of the Raspberry Pi 5 kiosk, 9 distinct architectural obstacles were encountered and permanently solved. Maintainers must be aware of these battle-tested solutions:"
    )

    kiosk_issues = [
        ("1. Systemd Ghost GUI (DRM Permissions)", "Problem: Running cage via background systemd service reported active, but physical screen remained stuck on tty3 console.\nFix: Background services lack active seat sessions. Switched to Console Autologin on tty1; ~/.profile inherits full DRM/KMS display permissions."),
        ("2. Micro-HDMI Port 1 Strict Priority", "Problem: Screen remained black when GUI launched.\nFix: Raspberry Pi 5 hardware video pipelines and Wayland compositors prioritize HDMI-1 (port closest to USB-C power). Cable must be physically plugged into HDMI-1."),
        ("3. FAT32 Dirty Bit Boot Lock", "Problem: Updates to cmdline.txt silently failed; partition mounted as read-only.\nFix: Unsafe power cuts cause Linux FAT driver to lock the partition. Cleared using: sudo umount /boot/firmware && sudo fsck.fat -a /dev/mmcblk0p1 && sudo mount -o rw /dev/mmcblk0p1 /boot/firmware."),
        ("4. Plymouth Screen Hijacking & GPU Delay", "Problem: Custom boot logo failed to appear; Plymouth forced console to tty3, hiding GUI.\nFix: Added DeviceTimeout=8 in /etc/plymouth/plymouthd.conf to force Plymouth to wait for the vc4-kms-v3d driver, and asserted console=tty1 in cmdline.txt."),
        ("5. USB Transfer & Phantom Drives", "Problem: Mounting USB drive on Pi failed when referencing /dev/sda1.\nFix: /dev/sda was a 40KB internal card reader; the actual drive was /dev/sdb1. Use lsblk to verify sizes before mounting. Never copy Windows .venv or .idea folders to Linux."),
        ("6. Python Virtual Environment (PEP 668)", "Problem: pip install commands failed on Debian Bookworm due to PEP 668 externally-managed environment.\nFix: Created local virtual environment (python -m venv venv) and bound all execution paths to /home/insitumicron-rpi/Pi_HMI/venv/bin/python."),
        ("7. Orphaned SQLite Database Location", "Problem: test_data.db was initially placed on read-only OS partition, causing SQL write errors.\nFix: Moved database to /mnt/data/ and updated data_logger.py to automatically route to /mnt/data if directory exists."),
        ("8. OverlayFS Blocking fstab Automounts", "Problem: fstab automounts conflicted with OverlayFS boot timing, falling back to RAM storage.\nFix: Removed fstab entry and inserted sudo mount /dev/mmcblk0p3 /mnt/data into ~/.profile right before launching GUI."),
        ("9. Hardware Disconnect UI Handling", "Problem: Serial disconnect mid-test caused blocking modal dialogs that froze kiosk UI.\nFix: Replaced blocking dialogs with auto-save and an in-place non-blocking red dashboard warning banner ('CONTROLLER DISCONNECTED - CHECK CONNECTION'). Removed drifting RTC Date column from UI."),
    ]
    add_def_table(doc, kiosk_issues)

    add_section_heading(doc, "5.7", "OS Maintenance Runbook: Software Upgrades under OverlayFS")
    doc.add_paragraph(
        "Because the root filesystem is locked as read-only, deploying software updates or modifying system files requires a strict unlock-update-relock sequence:"
    )

    upgrade_steps = [
        ("Step 1: SSH into Host Controller", "Connect laptop to the enclosure Ethernet port or Wi-Fi: ssh insitumicron-rpi@stgobain-hmi-lc.local."),
        ("Step 2: Disable OverlayFS Shield", "Execute: sudo raspi-config nonint disable_overlayfs && sudo raspi-config nonint disable_bootro."),
        ("Step 3: Reboot into Read-Write Mode", "Execute: sudo reboot. Allow 45 seconds for reboot. Log back in via SSH."),
        ("Step 4: Deploy Python Updates", "Transfer modified files to /home/insitumicron-rpi/Pi_HMI/ using scp or git pull. Verify file permissions: chown -R insitumicron-rpi:insitumicron-rpi /home/insitumicron-rpi/Pi_HMI/."),
        ("Step 5: Test Execution", "Run the updated application manually in test mode: python main.py. Verify behavior and exit."),
        ("Step 6: Re-Enable OverlayFS Shield", "Execute: sudo raspi-config nonint enable_overlayfs && sudo raspi-config nonint enable_bootro."),
        ("Step 7: Final Reboot into Locked Kiosk", "Execute: sudo reboot. Confirm system boots directly into the updated HMI with OverlayFS fully engaged."),
    ]
    add_def_table(doc, upgrade_steps)

    # =========================================================================
    # CHAPTER 6: OPERATIONS, STANDARD TESTING & RUNBOOKS
    # =========================================================================
    add_chapter_heading(doc, 6, "Operations, Standard Testing & Runbooks")

    add_section_heading(doc, "6.1", "Cold Start and System Verification Sequence")
    doc.add_paragraph(
        "To initiate operations from a completely powered-down state for the Saint-Gobain test rig:"
    )

    start_steps = [
        ("Step 1: Check Interlocks & Power", "Confirm mains power cable is connected. Confirm the red emergency stop button is twisted and released in the out position. Switch on the ACTI9 MCB."),
        ("Step 2: Press Start Button", "Press the green front-panel Start button. Confirm the green indicator lamp illuminates, verifying contactor closure and live internal DC rails."),
        ("Step 3: Wait for Kiosk Boot", "The Waveshare touchscreen displays the St. Gobain boot splash for ~25 seconds, transitioning directly into the full-screen Sample Parameters page."),
        ("Step 4: Verify Controller Link", "Navigate to the Settings tab in the left sidebar. Confirm the top status banner displays: 'Controller: CONNECTED (/dev/ttyACM0)' in green."),
    ]
    add_def_table(doc, start_steps)

    add_section_heading(doc, "6.2", "Standard 3-Point Flexural Bend Testing Runbook")
    doc.add_paragraph(
        "Standard workflow for conducting a mechanical flexure test:"
    )

    test_steps = [
        ("Step 1: Enter Sample Metadata", "On the Sample Parameters page, tap input fields to open the virtual keyboard. Enter Sample ID, Test Number, Business Type, Span Length (mm), Width (mm), Thickness/Height (mm), and Furnace Temperature (C)."),
        ("Step 2: Mount Specimen", "Place the ceramic or glass specimen symmetrically across the two lower support rollers of the 3-point bend fixture. Lower the upper loading roller until it is just clear of the specimen."),
        ("Step 3: Switch to Test Dashboard", "Tap Test Dashboard in the left sidebar. Confirm live digital readouts for Load (N) and Displacement (mm) are visible."),
        ("Step 4: Tare Sensors", "Tap Tare Load to zero residual tare weight. Tap Tare Disp to establish zero mechanical displacement at specimen touch."),
        ("Step 5: Start Test Recording", "Tap the green Start Test button in the sidebar. The status banner turns red ('RECORDING'), the elapsed timer starts, and live data curves appear on the plot."),
        ("Step 6: Specimen Loading & Rupture", "Advance the mechanical crosshead. Observe the real-time Load vs Displacement or Stress vs Strain curve. Upon specimen rupture, tap the red Stop Test button (or allow Auto-Stop to trigger). Data is automatically flushed to SQLite."),
    ]
    add_def_table(doc, test_steps)

    add_section_heading(doc, "6.3", "Contact-to-Displacement (CTD) Automated Tare Runbook")
    doc.add_paragraph(
        "In high-precision flexural testing, manually zeroing displacement at the precise micro-contact moment is difficult. The software provides an automated Contact-to-Displacement (CTD) feature:"
    )

    ctd_steps = [
        ("Principle", "When CTD is enabled, pressing Start Test arms the system into a WAITING_CONTACT state (amber badge). The software monitors load without logging data."),
        ("Contact Trigger", "When applied load reaches the CTD Threshold (default 10.0 N, configurable in Settings), the software automatically captures the current displacement as _ctd_disp_offset, tares the displacement curve to exactly 0.000 mm, transitions to RECORDING, and starts the timer."),
        ("Result", "All recorded displacement data reflects true specimen deflection after firm mechanical contact, eliminating pre-test air gap travel from the data record."),
    ]
    add_def_table(doc, ctd_steps)

    add_section_heading(doc, "6.4", "Automatic Break Detection and Auto-Stop Operation")
    doc.add_paragraph(
        "The Auto Start/Stop feature automates test termination when a specimen fractures:"
    )

    break_steps = [
        ("Arming Phase", "Once load exceeds the Auto-Start Threshold (default 20.0 N), the algorithm arms itself (lbl_auto_status displays 'TEST RUNNING' in green) and continuously tracks the maximum peak force reached (_auto_peak_load)."),
        ("Rupture Drop Trigger", "If load falls below drop_threshold = _auto_peak_load * (1.0 - _AUTO_STOP_DROP_FRACTION) (default 40% drop from peak), the algorithm instantly fires: disarms auto-stop, calls stop_test(), and displays an informative dialog showing peak load and drop load."),
        ("Protection Against False Stops", "The algorithm requires _auto_peak_load > _AUTO_START_THRESHOLD, preventing premature trip from low-force seating noise."),
    ]
    add_def_table(doc, break_steps)

    add_section_heading(doc, "6.5", "Historical Test Review, Multi-Curve Overlay, and Data Export")
    doc.add_paragraph(
        "Post-test workflow for data review and retrieval:"
    )

    export_steps = [
        ("Step 1: Open Test Analysis Tab", "Tap Test Analysis in the left sidebar. The overlay graph widget and analysis control panel are displayed."),
        ("Step 2: Browse Saved Tests", "Tap Browse Saved Tests to open the FileBrowserDialog. The table lists all past runs with Sample ID, Test Number, and Duration (drifting RTC Date column removed)."),
        ("Step 3: Multi-Test Overlay", "Select up to 5 tests in the table and tap Load Selected. The curves are rendered simultaneously on the graph in distinct colors with an interactive legend."),
        ("Step 4: Run Flexural Analysis", "Tap Calculate Properties. The engine computes Flexural Modulus (E), Break Stress, and Break Strain, displaying results in a summary table with the modulus regression line overlay."),
        ("Step 5: Export to USB Flash Drive", "Insert a USB pendrive into the front panel. In the file browser, select the desired tests and tap Export to USB. The software copies CSV files directly to /media/usb/ and executes os.fsync() to prevent write caching loss."),
        ("Step 6: Export PDF Certificate", "Tap Export PDF Report. Enter optional operator notes on the virtual keyboard. The system compiles a single-page PDF certificate to the USB drive."),
    ]
    add_def_table(doc, export_steps)

    add_section_heading(doc, "6.6", "Emergency Stop Actuation and Recovery Procedure")
    doc.add_paragraph(
        "If a mechanical jam, fixture collision, or hazardous condition occurs:"
    )

    estop_steps = [
        ("Actuation", "Firmly hit the red mushroom Emergency Stop button. The contactor immediately drops out, cutting all mains power to the 24V and 5V internal SMPS units and de-energizing all sensors and display electronics."),
        ("Recovery Step 1: Clear Hazard", "Resolve the mechanical binding or specimen misalignment. Confirm all personnel are clear of the load frame."),
        ("Recovery Step 2: Release E-Stop", "Twist the red mushroom E-Stop button clockwise until it springs outward into the reset position."),
        ("Recovery Step 3: Re-Energize Mains", "Press the green Start button. Confirm the green indicator lamp illuminates."),
        ("Recovery Step 4: System Re-Sync", "Allow the Raspberry Pi and STM32 to boot. The SerialManager thread will automatically re-discover the ST-Link COM port within 2 seconds once initialized."),
    ]
    add_def_table(doc, estop_steps)

    # =========================================================================
    # CHAPTER 7: KNOWN ISSUES, RISK REGISTER & ARCHITECTURAL DECISIONS
    # =========================================================================
    add_chapter_heading(doc, 7, "Known Issues, Risk Register & Architectural Decisions")

    add_section_heading(doc, "7.1", "Functional Safety and Risk Register")
    doc.add_paragraph(
        "Engineering risk register cataloging technical risks, severity classifications, and established mitigations:"
    )

    headers_risk = ["ID", "Area / Subsystem", "Risk / Technical Issue Description", "Severity", "Class", "Workaround / Mitigation Strategy"]
    rows_risk = [
        ["RSK-01", "Hardware Safety", "E-Stop button cuts AC mains via contactor but does not provide hardware feedback signal to STM32 GPIO.", "MEDIUM", "FUNCTIONAL SAFETY", "Contactor physically severs sensor and SMPS power, guaranteeing zero force transmission. Host detects serial disconnect gracefully."],
        ["RSK-02", "Firmware Tare", "Displacement baseline tare offset (-6.202 mm) is hard-coded into C firmware (me_tare_offset).", "MEDIUM", "DATA QUALITY", "Documented as intentional physical datum for MOR fixture [OWNER: Design choice]. Software provides live Tare Disp in GUI to offset any day-to-day drift."],
        ["RSK-03", "Security / Auth", "Administrative credentials (admin / insitumicron) are hard-coded in ui_layout.py in plaintext.", "LOW", "USABILITY / ACCESS", "Access is restricted to physical kiosk. Machine is offline with no external network exposure. Credentials controlled by admin [OWNER: Admin controlled]."],
        ["RSK-04", "Flash Durability", "SD card failure from continuous SQLite disk writes during high-frequency testing.", "HIGH", "RELIABILITY", "Mitigated via SQLite WAL mode, 100-sample batch writes, and root filesystem locked under immutable OverlayFS shield."],
        ["RSK-05", "I2C Bus Lockup", "DFRobot ADC slave device holding SDA low following electrical EMI noise burst.", "MEDIUM", "RELIABILITY", "Mitigated by I2C2_Bus_Recovery() routine: detects 3 errors, bit-bangs 9 SCL clock pulses, issues STOP, and re-initializes bus."],
        ["RSK-06", "Sensor Dropout", "Micro-Epsilon LVDT serial disconnect or cable snag during continuous stroke.", "MEDIUM", "DATA QUALITY", "Firmware bitmask status (0x04) flags timeout after 100 ms; GUI alerts operator and rejects invalid frames."],
    ]
    add_header_table(doc, headers_risk, rows_risk, col_widths=[Inches(0.6), Inches(1.1), Inches(1.8), Inches(0.8), Inches(1.0), Inches(1.97)])

    add_section_heading(doc, "7.2", "Architectural Decision Log (Key Engineering Trade-offs)")
    doc.add_paragraph(
        "Rationale for core technical decisions made during system architecture and development:"
    )

    dec_defs = [
        ("Decision 1: Dual-Processor Architecture (RPi 5 + STM32F446RE)", "Alternative Considered: Connecting ADC and LVDT directly to Raspberry Pi GPIO/SPI.\nReason: Linux is not a hard real-time OS; kernel context switches introduce millisecond jitter. Dedicated STM32 bare-metal firmware guarantees deterministic 1000 Hz LVDT sampling, strict I2C timing, and hardware IWDG watchdog protection."),
        ("Decision 2: SQLite WAL Mode vs Direct CSV Streaming", "Alternative Considered: Streaming data rows directly to an open CSV file on disk.\nReason: A power cut during CSV writing results in partial lines, corrupted files, and lost metadata. SQLite with Write-Ahead Logging (WAL) and batch commits provides ACID crash safety, zero corruption on power loss, and sub-second multi-test queries in the GUI."),
        ("Decision 3: Cage Wayland Compositor vs Standard X11 Desktop", "Alternative Considered: Running Raspberry Pi Desktop (PIXEL / X11) with window manager.\nReason: Standard desktops permit operators to minimize windows, access file managers, and accidentally exit the application. Cage provides an un-escapable, zero-overhead kiosk container that boots directly into the PySide6 fullscreen interface."),
        ("Decision 4: OverlayFS Immutable Root Partition", "Alternative Considered: Standard read-write Linux root filesystem with journaling.\nReason: In industrial production, machines are switched off at the mains switch without prior shutdown. OverlayFS eliminates all write operations to the OS partition, rendering the system impervious to SD card corruption across thousands of power cuts."),
        ("Decision 5: Decoupled Pure-Math Flexural Analysis Engine", "Alternative Considered: Computing mechanical properties inline within GUI widget callbacks.\nReason: Pure-math isolation (flexural_analysis.py) eliminates Qt dependencies, enabling standalone automated unit testing, headless script verification, and seamless integration into automated PDF certificate generation."),
    ]
    add_def_table(doc, dec_defs)

    # =========================================================================
    # CHAPTER 8: QUICK REFERENCE CARD
    # =========================================================================
    add_chapter_heading(doc, 8, "Quick Reference Card")

    add_section_heading(doc, "8.1", "System Default Parameters and Limits")
    doc.add_paragraph(
        "Operational parameters, engineering units, default settings, and safety limits:"
    )

    headers_ref = ["Parameter", "Value / Setting", "Unit", "Location / Scope", "Access Level"]
    rows_ref = [
        ["Load Calibration Factor", "1.0", "Multiplier", "hmi_settings.json", "Admin Protected (Settings Lock)"],
        ["Disp Calibration Factor", "1.0", "Multiplier", "hmi_settings.json", "Admin Protected (Settings Lock)"],
        ["Auto-Start Threshold", "20.0", "Newtons (N)", "hmi_settings.json", "Admin Protected (Settings Lock)"],
        ["Auto-Stop Drop Fraction", "40.0 (0.40)", "Percentage (%)", "hmi_settings.json", "Admin Protected (Settings Lock)"],
        ["CTD Contact Threshold", "10.0", "Newtons (N)", "hmi_settings.json", "Admin Protected (Settings Lock)"],
        ["Firmware Tare Offset", "-6.202", "Millimeters (mm)", "stgobain_lc_rpi_main.c", "Hardcoded Firmware Constant"],
        ["Load Full-Scale Force", "2943.0", "Newtons (N)", "stgobain_lc_rpi_main.c", "0 to 10 V ADC Calibration"],
        ["Telemetry Transmission Rate", "20.0 (50 ms)", "Hertz (Hz)", "USART2 (ST-Link)", "Fixed Firmware Interval"],
        ["Max Plot Buffer Capacity", "100,000", "Data Points", "graph_manager.py", "In-Memory Circular Buffer"],
        ["Max Multi-Test Overlay", "5", "Concurrent Curves", "ui_layout.py", "Analysis Graph Limitation"],
        ["Min USB Drive Size", "50.0", "Megabytes (MB)", "usb_utils.py", "Detection Filter Threshold"],
    ]
    add_header_table(doc, headers_ref, rows_ref, col_widths=[Inches(1.8), Inches(1.1), Inches(1.1), Inches(1.2), Inches(1.07)])

    add_section_heading(doc, "8.2", "Touchscreen Navigation Menu Map")
    doc.add_paragraph(
        "Structure of the 4 primary touchscreen pages accessible via the left sidebar:"
    )

    menu_defs = [
        ("1. Sample Parameters", "Configure specimen identification (Sample ID, Test Number, Business Type), geometric dimensions (Span Length, Width, Height in mm), and environmental furnace temperature (C)."),
        ("2. Test Dashboard", "Real-time monitoring interface while a test runs. Features live digital readouts, Tare Load and Tare Disp buttons, CTD toggle, Auto Start/Stop status indicator, and switchable 4-mode pyqtgraph plot."),
        ("3. Test Analysis", "Historical evaluation page. Browse past saved tests in the SQLite database, overlay up to 5 concurrent curves, run automated 3-point flexural stress-strain analysis, export CSV data to USB, and generate PDF certificates."),
        ("4. Settings", "Diagnostic and configuration page. Displays real-time controller serial link status, admin security lock badge, sensor calibration multipliers, auto-break thresholds, CTD threshold, and clean system shutdown control."),
    ]
    add_def_table(doc, menu_defs)

    add_section_heading(doc, "8.3", "Hardware Terminal and Pinout Cheat-Sheet")
    doc.add_paragraph(
        "Summary reference for wiring, peripheral baud rates, and terminal assignments:"
    )

    headers_pin = ["Hardware Interface", "Connector / Terminal", "Signal Names", "Electrical Standard", "Baud / Clock Rate"]
    rows_pin = [
        ["Micro-Epsilon LVDT", "GX16 5-Pin Bulkhead", "Pin 1: +24V, Pin 2: GND, Pin 3: Data A (+), Pin 4: Data B (-)", "RS-485 Differential", "256000 bps, 9E1"],
        ["Load Cell Amplifier", "BNC Female Bulkhead", "Center: +0 to 10 V Analog, Shell: AGND Ground", "Single-Ended Analog", "DC to 100 Hz"],
        ["DFRobot ADC I2C", "Carrier PCB Headers", "SCL (PB10), SDA (PB3), +5V, GND", "I2C Bus (Slave 0x4B)", "100 kHz Standard"],
        ["Host USB-Serial", "ST-Link Mini-B USB", "PA2 (MCU TX), PA3 (MCU RX), USB D+/D-", "USB 2.0 CDC VCP", "115200 bps, 8N1"],
        ["Mains AC Ingress", "IEC C14 Power Socket", "Line (L via MCB), Neutral (N), Earth (PE Stud)", "230 VAC 50 Hz", "Single Phase AC"],
        ["DC Power Rails", "Internal WAGO Terminals", "+24V DC (SMPS 1), +5V DC (SMPS 2), 0V Common", "Regulated DC", "Continuous"],
    ]
    add_header_table(doc, headers_pin, rows_pin, col_widths=[Inches(1.3), Inches(1.2), Inches(1.6), Inches(1.1), Inches(1.07)])

    add_section_heading(doc, "8.4", "File System and Persistence Locations Cheat-Sheet")
    doc.add_paragraph(
        "Reference locations for files across development and kiosk production environments:"
    )

    path_defs = [
        ("SQLite Test Database", "Production: /mnt/data/test_data.db | Development: <repo_dir>/test_data.db"),
        ("Database Backups", "Production: /mnt/data/test_data.db.bak1, .bak2, .bak3 (rolling on boot)"),
        ("HMI Settings JSON", "Production: /mnt/data/hmi_settings.json | Development: <repo_dir>/hmi_settings.json"),
        ("Kiosk Status Diagnostic Log", "Production: /mnt/data/kiosk_status.log | Development: <repo_dir>/kiosk_status.log"),
        ("USB Automount Location", "Production: /media/usb/ (auto-mounted via systemd udev rule)"),
        ("Systemd Journal Log", "Production: /mnt/data/journal/ (symlinked from /var/log/journal)"),
        ("Application Source Code", "Production: /home/insitumicron-rpi/Pi_HMI/ (locked read-only under OverlayFS)"),
    ]
    add_def_table(doc, path_defs)

    add_section_heading(doc, "8.5", "Status Indicators and Error Codes Reference")
    doc.add_paragraph(
        "Diagnostic indicators, visual badges, and telemetry error bitmasks:"
    )

    stat_defs = [
        ("Green Indicator Lamp (Front Panel)", "Illuminated when contactor is closed and AC mains is successfully energizing the internal 24V and 5V SMPS rails."),
        ("Controller: CONNECTED (Settings Page)", "Green banner indicating active USB-serial connection to STM32 ST-Link (/dev/ttyACM0). Telemetry packets arriving at 20 Hz."),
        ("Controller: DISCONNECTED / Searching...", "Red banner indicating USB-serial disconnect, unpowered STM32, or bad cable. System auto-reconnects every 2 seconds."),
        ("Telemetry Status Bit 0 (0x01)", "Displacement Sensor Error. Transmitted displacement value is NaN or Infinite; sensor disconnected or out of range."),
        ("Telemetry Status Bit 1 (0x02)", "Load Cell ADC Error. Transmitted load value is NaN or Infinite; ADC disconnected or I2C communication fault."),
        ("Telemetry Status Bit 2 (0x04)", "Micro-Epsilon Timeout. LVDT controller failed to return a valid binary response frame within 100 ms."),
        ("Auto Start/Stop: WAITING TO START", "Blue badge indicating auto-break armed and waiting for load to exceed Auto-Start Threshold (20 N)."),
        ("Auto Start/Stop: TEST RUNNING", "Green badge indicating active test recording and dynamic peak load tracking in progress."),
        ("Auto Start/Stop: AUTO STOPPED", "Red badge indicating test terminated automatically following a 40% drop from peak load."),
        ("CTD Badge: WAITING_CONTACT", "Amber badge indicating test armed and awaiting specimen contact threshold (10 N) before taring stroke."),
    ]
    add_def_table(doc, stat_defs)

    # Save Document
    print(f"Saving Master Technical Handover Manual to: {output_path}")
    doc.save(output_path)
    print("Master Technical Handover Manual generated successfully.")


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_file = os.path.join(out_dir, "InsituMicron_DAQ_Rig_Technical_Handover_Manual_V1.0.docx")
    build_master_manual(out_file)
