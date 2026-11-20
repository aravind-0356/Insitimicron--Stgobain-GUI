# docs/handover/build_stgobain_handover.py
"""
Generator script for Saint-Gobain High-Temperature Flexural Creep Testing System.
Produces: docs/handover/InsituMicron_StGobain_Technical_Handover_Manual_V1.0.docx
Contains all 11 Master Chapters:
  - Chapter 0: Handover Index & Repository Navigation (Doc 0)
  - Chapter 1: System Architecture and Operating Principles (Doc 1)
  - Chapter 2: Embedded Firmware Architecture & Guide (Doc 2)
  - Chapter 3: Software (GUI) Architecture & Data Pipeline (Doc 3)
  - Chapter 4: Hardware, Electronics & Wiring Reference (Doc 4)
  - Chapter 5: System Operations, Calibration & Runbooks (Doc 5)
  - Chapter 6: Known Issues, Errata & Risk Register (Doc 6)
  - Chapter 7: Engineering Decision Log (Doc 7)
  - Chapter 8: System Access, Security & Credentials (Doc 8)
  - Chapter 9: In-Flight Work, Maintenance & Roadmap (Doc 9)
  - Chapter 10: Handover Verification & Sign-Off Record (Doc 10)
"""

import os
import sys

# Add current directory to path for builder_common
sys.path.insert(0, os.path.dirname(__file__))

from builder_common import (
    create_base_document, add_title_page, setup_header_footer,
    add_document_control, add_table_of_contents, add_chapter_heading,
    add_section_heading, add_sub_heading, add_callout, add_code_block,
    add_def_table, add_header_table
)
from docx.shared import Inches, Pt, RGBColor


def build_stgobain_manual(output_path):
    print("Building Saint-Gobain Master Technical Handover Manual (Complete Edition)...")
    doc = create_base_document()

    # Title Page
    logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "InsituMicronlogo.jpg"))
    add_title_page(
        doc,
        main_title="Master Technical Handover Manual: Saint-Gobain Flexural Creep System",
        subtitle="Comprehensive Engineering Guide for Embedded Firmware, Raspberry Pi Kiosk GUI, Sensor Telemetry, and Motor Control",
        system_model="Saint-Gobain Flexural Testing Rig (Raspberry Pi 5 + STM32 Nucleo-F446RE)",
        doc_version="Software v1.0 / Firmware v1.0",
        doc_date="2026-11-20",
        author="Lead Embedded Systems & Software Engineer (Departing)",
        reviewer="Engineering Team / Company Technical Archives",
    )

    # Running Headers and Footers
    setup_header_footer(
        doc,
        short_title="Saint-Gobain Creep System Handover Manual | InsituMicron",
        doc_version="v1.0",
        doc_date="2026-11-20",
        logo_path=logo_path if os.path.exists(logo_path) else None,
    )

    # Document Control Block (Page 2)
    doc_control_rows = [
        ("v1.0", "2026-11-20", "Lead Systems Engineer", "Engineering Archives", "Complete master knowledge transfer documentation for Saint-Gobain flexural creep rig covering Chapters 0 through 10.")
    ]
    add_document_control(doc, doc_control_rows)

    # Table of Contents
    add_table_of_contents(doc)

    # =========================================================================
    # CHAPTER 0: HANDOVER INDEX AND REPOSITORY STRUCTURE (Document 0)
    # =========================================================================
    add_chapter_heading(doc, 0, "Handover Index and Repository Navigation")

    add_callout(
        doc, "DANGER", "HIGH TEMPERATURE AND MECHANICAL CRUSH HAZARD",
        "The Saint-Gobain flexural testing rig combines a high-temperature Eurotherm-controlled furnace "
        "(up to 1200 deg C) with a Leadshine closed-loop motor stage generating significant axial compressive force. "
        "Before servicing controller hardware or executing firmware flashing, verify that the furnace element heating "
        "circuit is de-energized and that mechanical fixtures are safely unloaded. The manual power switch on the enclosure "
        "serves as the primary physical power disconnect."
    )

    add_callout(
        doc, "NOTE", "DOCUMENT SCOPE AND OPERATING CONTEXT",
        "This master handover document captures the complete engineering knowledge required to maintain, build, "
        "flash, debug, operate, and modify the Saint-Gobain Flexural Creep Testing System. The physical hardware is "
        "deployed at Saint-Gobain Research India. The repository covers two interconnected systems: the Python PySide6 "
        "touchscreen Kiosk application running on a Raspberry Pi 5 under an OverlayFS Linux environment, and the "
        "bare-metal C firmware running on an STM32 Nucleo-F446RE ARM Cortex-M4 microcontroller."
    )

    add_section_heading(doc, "0.1", "System Scope and Boundary Definition")
    doc.add_paragraph(
        "[DOC: Project Scope Agreement] This document and repository specifically cover the Saint-Gobain flexural creep "
        "testing rig. To prevent ambiguity across the InsituMicron engineering portfolio, the technical boundaries are "
        "defined as follows:"
    )

    scope_table = [
        ("In Scope", "Raspberry Pi 5 HMI software repository (Pi_HMI_mtr), Wayland Cage kiosk deployment, Plymouth boot splash, UDEV rules, OverlayFS read-only rootfs configuration, SQLite WAL test logging, STM32F446RE bare-metal C firmware (st_gobain-HMI), Micro-Epsilon LVDT displacement sensor protocol, Eurotherm 3504 furnace temperature controller interface, Leadshine CS2RS Modbus RTU stepper drive and motor control, electrical control enclosure wiring, and power distribution components."),
        ("Out of Scope", "Tensile testing fixtures, biaxial testing stages, National Instruments NI-DAQ USB data acquisition devices, FLIR Grasshopper camera vision pipelines, custom PCB manufacturing Gerber layouts, and mechanical furnace heating element fabrication.")
    ]
    add_def_table(doc, scope_table)

    add_section_heading(doc, "0.2", "Evidence Tagging and Verification Standards")
    doc.add_paragraph(
        "To ensure engineering integrity, every non-trivial technical claim in this manual is tagged with its authoritative source "
        "in accordance with InsituMicron handover quality standards. Never assume or extrapolate unverified facts:"
    )

    tag_definitions = [
        ("[CODE: file:function:lines]", "Fact verified directly by inspecting active source code in the repository or firmware project."),
        ("[CONFIG: file:key]", "Fact verified from a configuration file, JSON setting, STM32CubeMX .ioc file, or deployment script."),
        ("[DOC: document_name, section]", "Fact extracted from verified manufacturer datasheets, CAD schedules, or deployment logs."),
        ("[OWNER]", "Fact explicitly confirmed by the departing author during formal handover technical alignment."),
        ("[INFERRED]", "Technical deduction reasoned from engineering behavior, flagged for validation on physical hardware."),
        ("[UNKNOWN]", "Unresolved gap where information is unavailable; tracked as an action item.")
    ]
    add_def_table(doc, tag_definitions)

    add_section_heading(doc, "0.3", "Repository Inventory and Module Map")
    doc.add_paragraph(
        "[CODE: Repository File Index] The software and firmware codebase is organized into modular files. The following table "
        "details every source, configuration, and deployment module, its ownership boundary, and critical constraints:"
    )

    module_headers = ["File / Path", "Role / Ownership", "Language", "Critical Constraints & Notes"]
    module_rows = [
        ("main.py", "Application Composition Root", "Python / Qt", "Initializes QApplication, forces Segoe UI 12pt font, applies theme, detects KIOSK_MODE=1 for fullscreen display. Must not block UI."),
        ("ui_layout.py", "MainWindow & Touch Layout", "Python / Qt", "Owns 4-tab QStackedWidget, jog buttons, live numerical readouts, displacement lower-limit safety guard (3.5 mm), and admin authentication."),
        ("serial_manager.py", "UART Communication Worker", "Python / Qt", "Dedicated QThread running non-blocking readline; auto-discovers ST-Link VCP (VID 0x0483), parses 20 Hz telemetry, catches PULLBACK_DONE."),
        ("data_logger.py", "SQLite Datalogger & Export", "Python / SQLite", "Thread-safe SQLite engine with WAL mode; routes mtr_data.db to /mnt/data on Linux, maintains 3 rotating backups, exports CSV to /media/usb."),
        ("graph_manager.py", "Dual-Axis Real-Time Graph", "Python / pyqtgraph", "Plots Displacement (blue, left) and Temperature (red, right) vs Time; downsamples at 5000 points, provides custom ViewBox reset button."),
        ("settings_manager.py", "Configuration Persistence", "Python / JSON", "Loads and writes hmi_settings.json; dynamically redirects path to persistent /mnt/data/ partition under Linux to bypass OverlayFS."),
        ("virtual_keyboard.py", "Touchscreen Input Dialogs", "Python / Qt", "Modal QWERTY keyboard (TextInputDialog) and numeric numpad (NumpadDialog) with finger-sized keys (min 48x48 px) for touch HMI."),
        ("usb_utils.py", "USB Storage Detection", "Python / psutil", "Scans connected block devices, filters out STM32 Nucleo virtual flash drives (< 50 MB) and OverlayFS mounts, returning pendrive path."),
        ("theme.py", "Global Corporate Stylesheet", "Python / QSS", "Centralized QSS stylesheet defining dark teal primary (#005b7f), bright teal accent (#00a8cc), buttons, tables, and tab aesthetics."),
        ("constants.py", "Color Definitions", "Python", "Defines PRIMARY_COLOR (#005b7f) and ACCENT_COLOR (#00a8cc) matching InsituMicron corporate branding."),
        ("hmi_settings.json", "Default Machine Settings", "JSON", "Stores jog velocities, pullback distances, pullback speeds, and displacement calibration coefficients."),
        ("deploy/install_kiosk.sh", "Kiosk Provisioning Script", "Bash Shell", "Configures Plymouth boot splash, TTY1 auto-login into Cage Wayland compositor, OverlayFS read-only root, and /mnt/data permissions."),
        ("deploy/99-usb-mount.rules", "Silent UDEV Automount Rule", "Linux UDEV", "Kernel rule executing systemd-mount upon pendrive insertion; mounts block devices to /media/usb silently without desktop prompts."),
        ("Core/Src/main.c", "STM32 Firmware Application", "Embedded C", "STM32F446RE main loop: Micro-Epsilon LVDT (USART3, 20 Hz), Eurotherm 3504 (UART5, 2 Hz), Leadshine CS2RS Modbus (USART1, 20 Hz), telemetry (USART2, 20 Hz)."),
        ("st_gobain-mtr.ioc", "STM32CubeMX Project Config", "CubeMX XML", "Defines 84 MHz HSI PLL clock tree, USART1/2/3, UART5, I2C2, DMA2 Stream 2, and NVIC interrupt priorities."),
        ("St Gobain Project 1 BOM Electrical.xlsx", "Master Electrical BOM", "Excel Spreadsheet", "Comprehensive electrical bill of materials including Raspberry Pi 5, STM32 Nucleo, Leadshine drive, sensors, contactors, and SMPS.")
    ]
    add_header_table(doc, module_headers, module_rows, col_widths=[Inches(1.8), Inches(1.5), Inches(0.9), Inches(2.07)])

    add_section_heading(doc, "0.4", "Role-Based Reading Order")
    doc.add_paragraph(
        "To maximize knowledge absorption, incoming engineers should review this master documentation set according to their "
        "specific operational discipline:"
    )

    reading_order = [
        ("Firmware Engineers", "Begin with Chapter 1 (System Architecture), Chapter 2 (Firmware Guide), Chapter 4 (Hardware Reference), and Chapter 6 (Known Issues & Risk Register). Focus on non-blocking UART timings, Modbus queue arbitration, and the commented kill-switch logic."),
        ("Software / GUI Engineers", "Begin with Chapter 1 (System Architecture), Chapter 3 (Software Guide), Chapter 5 (Operations & Runbooks), and Chapter 6 (Known Issues). Focus on QThread signal-slot boundaries, the dual-state OverlayFS storage architecture, and SQLite crash recovery."),
        ("Instrumentation & Field Engineers", "Begin with Chapter 1 (System Architecture), Chapter 4 (Hardware & Wiring), Chapter 5 (Operations & Runbooks), and Chapter 6 (Known Issues). Focus on sensor excitation, isolated RS-485 modules, contactor wiring, and field tare verification.")
    ]
    add_def_table(doc, reading_order)

    add_section_heading(doc, "0.5", "Document Roadmap and Master Section Status")
    doc.add_paragraph(
        "This master manual unifies all eleven core technical knowledge areas into a single engineering guide. The verification "
        "status of each section is tracked below:"
    )

    status_headers = ["Chapter", "Technical Domain", "Verification Status", "Evidence Basis"]
    status_rows = [
        ("Chapter 0", "Handover Index & Repository Navigation", "Verified / Released", "Codebase audit and verified file manifest [CODE]."),
        ("Chapter 1", "System Architecture & Operating Principles", "Verified / Released", "Full architectural analysis of hardware, telemetry, and OS [CODE/CONFIG/DOC]."),
        ("Chapter 2", "Embedded Firmware Guide (STM32F446RE)", "Verified / Released", "Bare-metal C source, CubeMX .ioc file, and peripheral timings [CODE/CONFIG]."),
        ("Chapter 3", "Software (GUI) Architecture & Data Pipeline", "Verified / Released", "PySide6 modules, QThread mechanics, and Wayland kiosk files [CODE]."),
        ("Chapter 4", "Hardware, Electronics & Wiring Reference", "Verified / Released", "Project 1 Electrical BOM, Leadshine manual, and sensor datasheets [DOC]."),
        ("Chapter 5", "System Operations, Calibration & Runbooks", "Verified / Released", "Operating procedures, tare calibration, and USB export [CODE/DOC]."),
        ("Chapter 6", "Known Issues, Safety Risks & Workarounds", "Verified / Released", "Safety register, floating inputs, and watchdog omissions [CODE/OWNER]."),
        ("Chapter 7", "Engineering Decision Log & Rationale", "Verified / Released", "OverlayFS single-SD architecture, Modbus queue design [CODE/DOC]."),
        ("Chapter 8", "System Access, Intellectual Property & Custodians", "Verified / Released", "Administrative credentials, sudoers policies, licensing [CODE/CONFIG]."),
        ("Chapter 9", "In-Flight Work, Technical Debt & Next Steps", "Verified / Released", "Punch-list items, maintenance roadmap, refactoring priorities [OWNER]."),
        ("Chapter 10", "Handover Verification & Sign-Off Record", "Verified / Released", "Cold-read test instructions and engineering sign-off table [DOC].")
    ]
    add_header_table(doc, status_headers, status_rows, col_widths=[Inches(0.9), Inches(2.2), Inches(1.3), Inches(1.87)])

    # =========================================================================
    # CHAPTER 1: SYSTEM ARCHITECTURE AND OPERATING PRINCIPLES (Document 1)
    # =========================================================================
    add_chapter_heading(doc, 1, "System Architecture and Operating Principles")

    add_callout(
        doc, "DANGER", "ELECTRICAL POWER INTERRUPT & MOTOR OVER-TRAVEL GUARDS",
        "1. PHYSICAL POWER CUT-OFF: A dedicated manual switch on the enclosure controls a Schneider Electric contactor, "
        "providing a physical disconnect of electrical power [BOM, OWNER].\n"
        "2. FIRMWARE KILL-SWITCH PROVISION: The STM32 firmware provisions a kill switch on GPIOB Pin 5 [CODE: main.c:L143-L144]. "
        "However, in the deployed hardware, this input is not connected to a physical switch. The polling routine in Process_Motor() "
        "is intentionally commented out [CODE: main.c:L524-L545] because an unconnected floating pin would trigger spurious emergency "
        "stops [CODE/OWNER]. Hardware emergency shutdown relies on the enclosure power switch.\n"
        "3. DISPLACEMENT LOWER-LIMIT SAFETY GUARD: In ui_layout.py, an automated digital limit stops downward motion whenever "
        "raw displacement drops below 3.500 mm, disabling the Jog Down control to prevent tooling collisions [CODE: ui_layout.py:L1820-L1831]."
    )

    add_callout(
        doc, "WARNING", "MOTOR JOG DIRECTIONAL RELIABILITY QUIRK",
        "[OWNER] During physical commissioning, it was observed that on rare occasions the manual Jog Up or Jog Down buttons "
        "fail to move the motor in the commanded direction immediately upon initial press. This condition occurs if an unhandled "
        "Modbus transaction collision or echo is in flight on USART1. The operator must release the button and press it again. "
        "Review Section 1.4 for the command queue pacing details."
    )

    add_section_heading(doc, "1.1", "Physical System Topology and Block Diagram")
    doc.add_paragraph(
        "[DOC: St Gobain Project 1 BOM Electrical.xlsx] The Saint-Gobain flexural creep testing system integrates a high-temperature "
        "Eurotherm furnace, a sub-micron LVDT displacement transducer, an industrial closed-loop stepper actuator, and a dual-state "
        "Raspberry Pi 5 touchscreen kiosk into a self-contained test bench. The system architecture consists of five core functional blocks:"
    )

    topo_defs = [
        ("Host HMI Controller (Raspberry Pi 5)", "Raspberry Pi 5 (4GB RAM) equipped with an Active Cooler and official 27W USB-C power supply. Runs Raspberry Pi OS Bookworm Lite in kiosk mode via the Cage Wayland compositor. The root filesystem is locked in permanent read-only mode using Linux OverlayFS to withstand sudden power loss without corruption, while test databases write to an isolated read-write partition (/mnt/data)."),
        ("Touchscreen Display (Waveshare 10.1\")", "10.1-inch capacitive touchscreen display (1024x600 resolution) mounted on the control console. Video connects to the Raspberry Pi Micro-HDMI-1 port, and touch digitizer signals connect via USB. Configured with Segoe UI touch fonts and finger-friendly on-screen keyboards."),
        ("Embedded Controller (STM32 Nucleo-F446RE)", "32-bit ARM Cortex-M4 microcontroller running bare-metal C firmware at 84 MHz SYSCLK. Orchestrates real-time deterministic sensor polling, Modbus RTU motor positioning, and 20 Hz telemetry streaming. Communicates with the Raspberry Pi over an ST-Link USB Virtual COM Port (USART2, 115200 8N1)."),
        ("Closed-Loop Motion Stage (Leadshine CS2RS)", "Leadshine CS-M21704 2-phase closed-loop stepper motor coupled to an 8.0 mm lead screw. Driven by a Leadshine CS2RS-D507 Modbus RTU drive (Slave ID 1) powered by a 24V DC SMPS. Optical encoder feedback (4000 counts/rev, 500 counts/mm) provides real-time position verification and auto-pullback retraction."),
        ("Displacement Sensing (Micro-Epsilon induSENSOR)", "Micro-Epsilon LVDT induSENSOR DTD-10G8 with integrated MSC7xxx signal electronics. Physical measurement range is -6.0 mm to +6.0 mm. Tared in firmware by adding a 6.0 mm offset to provide an effective measurement span of 0.0 mm to 12.0 mm. Communicates over RS-485 at 256000 baud (9E1) via STM32 USART3."),
        ("Temperature Control (Eurotherm 3504)", "Eurotherm 3504 advanced process controller regulating furnace heating elements. Polled at 2 Hz over an isolated RS-485 Modbus RTU link (UART5, 9600 baud, 8N2, Slave ID 1) to read holding register 1 (Process Variable / Temperature in deg C)."),
        ("Electrical Protection & Isolation", "Three Waveshare rail-mount galvanic isolated TTL-to-RS485 converters protect the microcontroller from high-voltage transients. Mains power is distributed through a Schneider Acti9 4A MCB and a Schneider LC1E0910M7 contactor controlled by panel pushbuttons.")
    ]
    add_def_table(doc, topo_defs)

    add_section_heading(doc, "1.2", "End-to-End Telemetry Acquisition Chain")
    doc.add_paragraph(
        "[CODE: main.c:L843-L850, serial_manager.py:L63-L84, ui_layout.py:L1868-L1882] Mechanical displacement and furnace temperature "
        "flow from physical transducers to the persistent SQLite database through a deterministic, multi-stage processing pipeline:"
    )

    telemetry_pipeline = [
        ("1. Displacement Sensing (USART3, 20 Hz)", "Every 50 ms (20 Hz), the STM32 non-blocking state machine transmits a 6-byte binary request frame (0x10 0x7E 0x01 0x4C 0xCB 0x16) to the Micro-Epsilon sensor over USART3 (256000 baud, 9E1). The sensor responds with a 17-byte packet starting with header 0x68 0x0B 0x0B 0x68 and ending with 0x16. The STM32 verifies the arithmetic checksum across bytes 4 through 14, extracts the IEEE 754 float, and adds the 6.0 mm tare offset: tared_displacement = scaled_val - (-6.0f) [CODE: main.c:L683-L731]."),
        ("2. Temperature Polling (UART5, 2 Hz)", "Every 500 ms (2 Hz), the STM32 sends a synchronous 8-byte Modbus FC03 read request (Slave 0x01, Function 0x03, Register 0x0001, 1 Register) to the Eurotherm 3504 controller over UART5 (9600 baud, 8N2). The 7-byte response is validated via CRC16. The 16-bit integer is extracted and scaled: if raw_temp > 500, temperature is divided by 10.0f; otherwise raw integer degrees is retained [CODE: main.c:L604-L681]."),
        ("3. Motor Encoder Feedback (USART1, 20 Hz)", "Every 50 ms (20 Hz), whenever the RS-485 bus is not occupied by an outgoing motor command, the STM32 transmits an 8-byte Modbus FC03 request to read registers 0x1014 and 0x1015 from the Leadshine drive over USART1 (115200 8N1). Reception is handled asynchronously via DMA2 Stream 2 to prevent CPU stalling. The high and low words are assembled into a signed 32-bit encoder count [CODE: main.c:L733-L757, L389-L414]."),
        ("4. MCU Telemetry Assembly (USART2, 20 Hz)", "Every 50 ms (20 Hz), the STM32 formats the latest valid sensor values into a comma-separated ASCII string: '%.3f,%.1f,%ld\\r\\n' representing Displacement (mm), Temperature (deg C), and Encoder Position (counts). This string is transmitted across the ST-Link VCP to the Raspberry Pi [CODE: main.c:L843-L850]. Because Eurotherm updates at 2 Hz while telemetry fires at 20 Hz, temperature repeats for approximately 10 packets."),
        ("5. Background Serial Ingestion (QThread)", "The SerialManager background thread on the Raspberry Pi continuously reads incoming UART lines via PySerial. Upon receiving a valid line, it parses displacement, temperature, and encoder counts, emitting the Qt signal: new_data(elapsed_time, disp_val, temp_val, enc_val) [CODE: serial_manager.py:L77-L84]."),
        ("6. GUI Processing & Safety Verification", "The main GUI thread receives new_data in MainWindow.update_graph(). It evaluates the 3.500 mm displacement lower limit, applies the operator software tare (comp_disp = disp_offset - disp_raw), and refreshes the live numeric screen readouts at 4 Hz (every 5th packet) [CODE: ui_layout.py:L1819-L1863]."),
        ("7. 1 Hz Plotting & Database Logging", "To prevent SD card wear and GUI latency during multi-hour creep tests, recording is strictly throttled to 1 Hz: if (relative_time - last_log) >= 1.0, data is appended to the pyqtgraph buffer and committed to SQLite via DataLogger.log_data_point() [CODE: ui_layout.py:L1868-L1882].")
    ]
    add_def_table(doc, telemetry_pipeline)

    add_section_heading(doc, "1.3", "Motor Command & Motion Execution Pipeline")
    doc.add_paragraph(
        "[CODE: ui_layout.py:L1056-L1071, main.c:L189-L321] Manual positioning and automated post-break pullback operate "
        "through an asynchronous, non-blocking command pipeline designed to avoid RS-485 bus collisions between motor commands "
        "and encoder feedback polling:"
    )

    motion_pipeline = [
        ("1. Operator Action or Break Trigger", "The operator taps Jog Up, Jog Down, or Motor Stop in the GUI, or the automated break detection routine triggers upon detecting a specimen rupture."),
        ("2. ASCII Serial Command Dispatch", "The GUI dispatches plain ASCII commands terminated by newline over serial_manager.send_command(): 'Vel:<rpm>\\n', 'JogUp\\n', 'JogDown\\n', 'Stop\\n', 'PullSpeed:<rpm>\\n', or 'Pullback:<counts>\\n' [CODE: ui_layout.py:L1059-L1070]."),
        ("3. Interrupt-Driven MCU Ring Buffer", "STM32 USART2 receives incoming ASCII bytes via HAL_UART_Receive_IT into a 256-byte circular ring buffer (uart2_rx_ring). Process_Pi_Commands() extracts newline-delimited command strings and sets volatile flags: pi_cmd_start, pi_cmd_stop, or pi_cmd_pullback [CODE: main.c:L361-L367, L420-L511]."),
        ("4. Leadshine PR Mode Frame Generation", "Process_Motor() translates the active command into Leadshine CS2RS Modbus RTU frames. Running in PR Path 0 Velocity Mode requires a strict 5-frame sequence: (1) Write 0x0012 to 0x6200 (PR Path 0 velocity mode with interrupt enabled); (2) Write target RPM to 0x6203; (3) Write acceleration (100 ms/1000rpm) to 0x6204; (4) Write deceleration (100 ms/1000rpm) to 0x6205; (5) Write 0x0010 to 0x6002 (Trigger PR Path 0) [CODE: main.c:L265-L299]."),
        ("5. Non-Blocking TX Queue Arbitration", "Direct transmission of all 5 frames back-to-back causes buffer overruns in the Leadshine drive. modbus_send_motor() enqueues frames into motor_tx_queue. Process_Motor_TX_Queue() claims exclusive bus ownership (encoder_bus_busy = 1), locks out encoder polling, and transmits each 8-byte frame with an exact 5 ms inter-frame pacing delay using HAL_UART_Transmit_IT [CODE: main.c:L189-L233]."),
        ("6. Burst Stop Transmission", "When Stop is commanded, the STM32 flushes the TX queue and transmits a burst of 4 consecutive Quick Stop frames (0x6002 = 0x0040) spanning 20 ms. This burst guarantees that the drive captures the halt command even if it is busy computing acceleration curves [CODE: main.c:L301-L321]."),
        ("7. Automated Break Retraction", "If break detection triggers, the GUI calculates pullback counts: pb_counts = int(pullback_dist_mm * 500 counts/mm). The STM32 records the starting encoder position, sets reverse velocity, monitors g_encoder_position until target distance is reached, stops the motor, and transmits 'PULLBACK_DONE\\r\\n' back to the GUI [CODE: main.c:L558-L583].")
    ]
    add_def_table(doc, motion_pipeline)

    add_section_heading(doc, "1.4", "Serial Protocol and Message Catalogue")
    doc.add_paragraph(
        "[CODE: main.c:L420-L500, L843-L850, serial_manager.py:L63-L84] Communication between the Raspberry Pi HMI and the "
        "STM32 Nucleo controller is conducted over USART2 at 115200 baud, 8 data bits, No parity, 1 stop bit (8N1). "
        "All telemetry and control frames conform to the specifications in the following tables:"
    )

    add_sub_heading(doc, "Host to STM32 Command Set")
    cmd_headers = ["Command String", "Parameters & Range", "Response / Action", "Description"]
    cmd_rows = [
        ("JogUp\\n", "None", "DBG: CMD=JogUp", "Retracts motor upward. Sets speed setpoint to negative RPM and triggers Leadshine PR Path 0."),
        ("JogDown\\n", "None", "DBG: CMD=JogDown", "Advances motor downward. Blocked if raw displacement < 3.500 mm. Triggers PR Path 0 with positive RPM."),
        ("Stop\\n", "None", "DBG: CMD=Stop", "Immediate halt. Flushes TX queue and sends 4x burst of Quick Stop frames (0x6002 = 0x0040) to drive."),
        ("Start\\n", "None", "DBG: CMD=Start", "Starts continuous motion at current motor_speed_setpoint."),
        ("Vel:<int>\\n", "1 to 200 RPM", "DBG: CMD=Vel", "Updates motor_speed_setpoint in RPM. Ignored if speed equals 0."),
        ("PullSpeed:<int>\\n", "1 to 200 RPM", "DBG: CMD=PullSpeed", "Configures retract velocity for automated break pullback. Default is 20 RPM."),
        ("Pullback:<int>\\n", "> 0 encoder counts", "DBG: CMD=Pullback", "Initiates automated pullback for specified counts (500 counts/mm). Emits PULLBACK_DONE upon completion.")
    ]
    add_header_table(doc, cmd_headers, cmd_rows, col_widths=[Inches(1.5), Inches(1.2), Inches(1.4), Inches(2.17)])

    add_sub_heading(doc, "STM32 to Host Telemetry and Events")
    telem_headers = ["Message Type", "Format Example", "Cadence", "Description & Payload Parsing"]
    telem_rows = [
        ("Telemetry Stream", "5.234,450.2,125000\\r\\n", "20 Hz (50 ms)", "Continuous CSV data: (1) Displacement in mm (3 decimals); (2) Furnace temperature in deg C (1 decimal); (3) Encoder counts (signed int32)."),
        ("Pullback Complete", "PULLBACK_DONE\\r\\n", "Asynchronous", "Emitted when automated pullback travel completes. Triggers test stop and completion modal on GUI."),
        ("Debug Diagnostics", "DBG: START frames sent\\r\\n", "Asynchronous", "Diagnostic strings prefixed with 'DBG:' indicating Modbus frame dispatches, state transitions, or invalid command alerts.")
    ]
    add_header_table(doc, telem_headers, telem_rows, col_widths=[Inches(1.5), Inches(1.8), Inches(1.1), Inches(1.87)])

    add_section_heading(doc, "1.5", "Thread, Process, and Kiosk Architecture")
    doc.add_paragraph(
        "[CODE: main.py, serial_manager.py, deploy/install_kiosk.sh] The Raspberry Pi HMI is designed as an appliance, "
        "isolating hardware communication from user interface rendering:"
    )

    thread_defs = [
        ("Main GUI Thread", "Owns the PySide6 event loop, MainWindow rendering, TouchLineEdit virtual input dialogs, 1 Hz pyqtgraph canvas repaints, and 1 Hz SQLite database inserts. Must never execute blocking I/O, sleep calls, or synchronous network queries."),
        ("SerialManager Thread (QThread)", "Background worker thread executing run(). Continuously blocks on PySerial readline(). Automatically discovers the ST-Link COM port, parses incoming telemetry lines, catches PULLBACK_DONE markers, and emits Qt signals to the main thread. Employs a 1.0-second reconnect backoff if serial disconnects occur."),
        ("Cage Wayland Compositor", "Lightweight kiosk compositor that runs the PySide6 application full-screen without window decorations, desktop taskbars, or context menus. Activated from ~/.profile during TTY1 auto-login via: cage -s -- /home/insitumicron-rpi/Pi_HMI_mtr/venv/bin/python main.py."),
        ("Plymouth Boot Splash", "Suppresses Linux kernel boot text, systemd initialization logs, and Raspberry Pi GPU logos. Displays the custom St. Gobain splash image (final_boot_logo_1280x800.png) from early kernel boot until Cage initializes."),
        ("Single-SD Dual-State Storage", "The physical SD card is partitioned into two regions: the operating system rootfs (/dev/mmcblk0p2) locked under OverlayFS read-only protection, and the dedicated data partition (/dev/mmcblk0p3) mounted read-write to /mnt/data. This architecture allows operators to power down the machine ungracefully without SD card filesystem corruption.")
    ]
    add_def_table(doc, thread_defs)

    add_section_heading(doc, "1.6", "Persistence Model and Database Lifecycle")
    doc.add_paragraph(
        "[CODE: data_logger.py:L42-L166, settings_manager.py:L10-L15] All persistent test data and machine settings are routed "
        "to the dedicated /mnt/data partition to survive reboots under the OverlayFS environment:"
    )

    db_details = [
        ("Database Location & Engine", "SQLite database located at /mnt/data/mtr_data.db under Linux (or local directory during Windows development). Configured with PRAGMA journal_mode=WAL and PRAGMA synchronous=FULL for ACID compliance and power-loss durability."),
        ("Batch Buffering", "Incoming 1 Hz data points are buffered in memory and flushed to disk in batches of 100 points, or immediately when the operator clicks Stop Test, minimizing physical write cycles on flash media."),
        ("Startup Rotating Backups", "On every application boot, DataLogger._backup_db() creates up to three rotating backup files (mtr_data.db.bak1, bak2, bak3). If an abrupt power cut during a flash block write damages the primary SQLite file, historical data remains recoverable."),
        ("Crash Auto-Recovery", "If the system loses power mid-test, the test record retains ended_at IS NULL. During next startup, _auto_recover_tests() detects the incomplete test, queries the timestamp of the last logged data point, populates ended_at and duration_s, and renames the test with the suffix '_RECOVERED'."),
        ("Settings Persistence", "SettingsManager stores machine parameters (calibration factors, jog speeds, break detection limits) in /mnt/data/hmi_settings.json. Any runtime adjustments made in the Settings tab are saved immediately to disk."),
        ("Silent USB CSV Export", "When a USB drive is inserted, Linux UDEV rule 99-usb-mount.rules automatically invokes systemd-mount to attach the drive at /media/usb. DataLogger.export_test_to_usb() generates a formatted CSV file with complete test metadata headers, column headers, and 1 Hz data rows, followed by os.fsync() to flush kernel buffers.")
    ]
    add_def_table(doc, db_details)

    add_section_heading(doc, "1.7", "Engineering Units and Physical Conversions")
    doc.add_paragraph(
        "[CODE: ui_layout.py:L1918-L1920, main.c:L89, L135] All sensor readings, motor commands, and logged parameters "
        "conform to the standardized engineering units and conversion factors summarized below:"
    )

    units_headers = ["Parameter", "Engineering Unit", "Raw Sensor / MCU Range", "Conversion / Scaling Factor", "Notes"]
    units_rows = [
        ("Raw Displacement", "mm", "-6.000 to +6.000 mm", "scaled_val + 6.0 mm", "Micro-Epsilon sensor output is tared in firmware by +6.0 mm to produce a 0.0 mm to 12.0 mm operational range [OWNER]."),
        ("Compression Displacement", "mm", "0.000 to 12.000 mm", "disp_offset - disp_raw", "Compression into sample is defined as positive travel relative to the operator tare baseline [CODE: ui_layout.py:L1843]."),
        ("Furnace Temperature", "deg C", "0.0 to 1200.0 deg C", "raw_temp / 10.0f (if > 500)", "Eurotherm 3504 Process Variable holding register 1. High values (> 500) scaled by 0.1 deg C resolution [CODE: main.c:L645]."),
        ("Encoder Position", "counts", "-2,147,483,648 to +2,147,483,647", "500 counts per mm", "Leadshine CS-M21704 motor has 4000 counts/rev (1000 lines x 4). Lead screw is 8.0 mm lead. Ratio: 4000 / 8.0 = 500 counts/mm."),
        ("Motor Velocity", "RPM", "1 to 200 RPM", "Direct RPM integer", "Written to Leadshine PR Path 0 velocity register 0x6203. Default jog velocity is 10 to 100 RPM."),
        ("Sampling Cadence", "Hz / seconds", "1 Hz (1 sample / sec)", "relative_time - last_log >= 1.0", "GUI numerical readouts refresh at 4 Hz (every 5th telemetry packet); graph and SQLite log at 1.0 Hz [CODE: ui_layout.py:L1870].")
    ]
    add_header_table(doc, units_headers, units_rows, col_widths=[Inches(1.4), Inches(0.9), Inches(1.3), Inches(1.3), Inches(1.37)])

    # =========================================================================
    # CHAPTER 2: EMBEDDED FIRMWARE ARCHITECTURE (Document 2)
    # =========================================================================
    add_chapter_heading(doc, 2, "Embedded Firmware Architecture and Guide")

    add_callout(
        doc, "DANGER", "FIRMWARE SAFETY FUNCTIONS AND UNCONNECTED KILL-SWITCH AUDIT",
        "1. KILL SWITCH STATUS: The firmware provisions a kill switch on GPIOB Pin 5 [CODE: main.c:L143-L144]. "
        "However, this input is NOT connected to physical hardware in the deployed unit [OWNER]. The polling check in "
        "Process_Motor() is commented out [CODE: main.c:L524-L545]. Do not un-comment this code without adding a physical "
        "external pull-up resistor (10 kOhm to 3.3V) and a wired switch, as a floating input pin will cause unpredictable halts.\n"
        "2. WATCHDOG TIMER ABSENCE: The firmware does not initialize an Independent Watchdog (IWDG) or Window Watchdog (WWDG) "
        "[CODE/CONFIG]. If an unhandled interrupt loop or hard fault occurs, the microcontroller will freeze without resetting. "
        "Future firmware revisions must integrate IWDG.\n"
        "3. HOST DISCONNECT BEHAVIOR: If USB communication from the Raspberry Pi drops while motion is active, the STM32 "
        "will continue executing the last commanded speed indefinitely until an operator presses the physical power switch on the enclosure."
    )

    add_section_heading(doc, "2.1", "Microcontroller Core & Clock Architecture")
    doc.add_paragraph(
        "[CODE: main.c:L860-L899, CONFIG: st_gobain-mtr.ioc] The embedded controller is an STMicroelectronics STM32F446RET6 "
        "(ARM Cortex-M4 32-bit RISC core with hardware FPU, 512 KB Flash, 128 KB SRAM) mounted on an official NUCLEO-F446RE development board. "
        "The clock tree is configured as follows:"
    )

    clk_defs = [
        ("Oscillator Source", "Internal High-Speed Oscillator (HSI) running at 16.0 MHz. Eliminates external crystal routing vulnerabilities in high-vibration industrial environments."),
        ("PLL Multipliers", "Main PLL configured with PLLM = 16, PLLN = 336, and PLLP = 4. VCO Input: 16 MHz / 16 = 1.0 MHz. VCO Output: 1.0 MHz x 336 = 336.0 MHz. System Clock: 336 MHz / 4 = 84.0 MHz SYSCLK."),
        ("Bus Prescalers", "AHB Prescaler = 1 (HCLK = 84.0 MHz). APB1 Prescaler = 2 (PCLK1 = 42.0 MHz, APB1 timer clock = 84.0 MHz). APB2 Prescaler = 1 (PCLK2 = 84.0 MHz, APB2 timer clock = 84.0 MHz)."),
        ("Flash Latency", "Configured for 2 wait states (FLASH_LATENCY_2) with prefetch buffer and instruction/data cache enabled for zero-wait execution."),
        ("Toolchain & HAL", "Built using STM32CubeIDE v1.18.1 with GCC ARM Embedded Toolchain 12.3.rel1. Hardware Abstraction Layer: STM32Cube FW_F4 V1.28.x.")
    ]
    add_def_table(doc, clk_defs)

    add_section_heading(doc, "2.2", "Peripheral Allocation and Pin Mapping")
    doc.add_paragraph(
        "[CODE: main.c:L907-L1138, CONFIG: st_gobain-mtr.ioc] All hardware communication channels and general-purpose I/O pins "
        "are allocated deterministically to prevent resource conflicts:"
    )

    pin_headers = ["Peripheral", "Role / Target Device", "Pins & Signals", "Baud / Speed", "Framing & Mode", "NVIC Priority"]
    pin_rows = [
        ("USART1", "Leadshine CS2RS Stepper Drive", "PA9 (TX), PA10 (RX)", "115200 bps", "8N1, TX: IT Queue, RX: DMA2 Stream 2", "Preemption 0, Sub 0"),
        ("USART2", "Raspberry Pi ST-Link Host", "PA2 (TX), PA3 (RX)", "115200 bps", "8N1, TX: Polling, RX: IT Ring Buffer", "Preemption 0, Sub 0"),
        ("USART3", "Micro-Epsilon LVDT Sensor", "PC10 (TX), PC11 (RX)", "256000 bps", "9E1, TX: IT, RX: IT Buffer", "Preemption 0, Sub 0"),
        ("UART5", "Eurotherm 3504 Controller", "PC12 (TX), PD2 (RX)", "9600 bps", "8N2, TX: Polling, RX: IT Buffer", "Preemption 0, Sub 0"),
        ("I2C2", "Auxiliary ADC (Unused)", "PB10 (SCL), PB3 (SDA)", "100 kHz", "Standard 7-bit Mode, Unused in runtime code", "Preemption 0, Sub 0"),
        ("GPIO PB5", "Kill Switch Input (Provisional)", "PB5 (Digital Input)", "N/A", "Input NOPULL, Polling disabled in code", "None"),
        ("GPIO PB4", "Digital Low Rail", "PB4 (Digital Output)", "N/A", "Output PP Low", "None"),
        ("GPIO PA5", "Nucleo Green LED (LD2)", "PA5 (Digital Output)", "N/A", "Output PP, Heartbeat Indicator", "None")
    ]
    add_header_table(doc, pin_headers, pin_rows, col_widths=[Inches(1.0), Inches(1.5), Inches(1.2), Inches(0.9), Inches(1.2), Inches(1.07)])

    add_section_heading(doc, "2.3", "Non-Blocking Main Loop Architecture")
    doc.add_paragraph(
        "[CODE: main.c:L817-L852] The firmware operates as a cooperative non-blocking scheduling loop driven by HAL_GetTick() (1 ms SysTick). "
        "No blocking delays exist inside the periodic tasks, ensuring that sensor telemetry and motor commands execute deterministically:"
    )

    loop_tasks = [
        ("1. Host Command Ingestion (5 ms)", "Every 5 ms, Process_Pi_Commands() extracts ASCII strings from uart2_rx_ring. Complete newline-terminated commands set volatile flags: pi_cmd_start, pi_cmd_stop, or pi_cmd_pullback [CODE: main.c:L420-L511]."),
        ("2. Motor State Machine (5 ms)", "Every 5 ms, Process_Motor() evaluates motor flags. If pi_cmd_stop is active, Leadshine_Send_Stop() is executed immediately. If pi_cmd_pullback is active, reverse motion is initiated and encoder progress is tracked. Normal start evaluates velocity changes [CODE: main.c:L513-L601]."),
        ("3. Eurotherm Polling (500 ms / 2 Hz)", "Process_Eurotherm() sends an 8-byte Modbus FC03 frame to read register 1 every 500 ms. A synchronous 8-byte transmit (~8.3 ms @ 9600 baud) guarantees shift register completion and avoids TX interrupt race conditions [CODE: main.c:L604-L681]."),
        ("4. Micro-Epsilon Polling (50 ms / 20 Hz)", "Process_Sensor() issues a 6-byte binary request every 50 ms via non-blocking IT transmit. Incoming bytes in sensor_rx_buffer are validated against header 0x68 0x0B 0x0B 0x68 and checksum byte 15. Floats are unpacked and tared [CODE: main.c:L683-L731]."),
        ("5. Encoder DMA Polling (50 ms / 20 Hz)", "Process_Encoder() checks if encoder_bus_busy is clear. If free, it sends an 8-byte FC03 read to registers 0x1014/0x1015. DMA2 Stream 2 listens passively; on reception, HAL_UARTEx_RxEventCallback decodes the 32-bit position [CODE: main.c:L733-L757]."),
        ("6. Motor TX Queue Dispatch (5 ms Pacing)", "Process_Motor_TX_Queue() drains queued Modbus frames with a mandatory 5 ms inter-frame pacing delay, preventing Leadshine drive buffer overflows [CODE: main.c:L206-L233]."),
        ("7. Telemetry Transmission (50 ms / 20 Hz)", "Every 50 ms, the latest tared displacement, Eurotherm temperature, and encoder count are assembled into '%.3f,%.1f,%ld\\r\\n' and transmitted across USART2 to the Raspberry Pi [CODE: main.c:L843-L850].")
    ]
    add_def_table(doc, loop_tasks)

    add_section_heading(doc, "2.4", "Build, Flash, and Verification Runbook")
    doc.add_paragraph(
        "To rebuild and deploy the firmware from a clean development workstation, execute the following numbered steps:"
    )

    doc.add_paragraph("Step 1: Open STM32CubeIDE and Import Workspace")
    doc.add_paragraph(
        "Launch STM32CubeIDE v1.18.1. Select File -> Import -> General -> Existing Projects into Workspace. "
        "Browse to the firmware folder (motor_interrupt/st_gobain-HMI) and click Finish."
    )

    doc.add_paragraph("Step 2: Clean and Rebuild Project")
    doc.add_paragraph(
        "Select Project -> Clean... and clean the project. Select Project -> Build Project (or press Ctrl+B). "
        "Verify in the build console that compilation succeeds with 0 errors and 0 critical warnings. "
        "Output ELF binary is located in Debug/st_gobain-HMI.elf."
    )

    doc.add_paragraph("Step 3: Connect Hardware and Flash Target")
    doc.add_paragraph(
        "Connect the STM32 Nucleo board to the host workstation via a standard USB Mini-B cable connected to CN1. "
        "In STM32CubeIDE, click Run -> Debug As -> STM32 C/C++ Application. Confirm that the ST-Link probe is detected, "
        "flash programming reaches 100%, and execution halts at main(). Click Resume (F8) to run."
    )

    doc.add_paragraph("Step 4: Command-Line Flashing via STM32CubeProgrammer CLI")
    doc.add_paragraph(
        "For automated production flashing without launching the IDE, execute the following command from PowerShell:"
    )
    add_code_block(doc, "STM32_Programmer_CLI.exe -c port=SWD mode=UR -w Debug/st_gobain-HMI.elf -v -hardRst", "Command-Line Firmware Flashing")

    # =========================================================================
    # CHAPTER 3: SOFTWARE (GUI) ARCHITECTURE (Document 3)
    # =========================================================================
    add_chapter_heading(doc, 3, "Software (GUI) Architecture and Signal Pipelines")

    add_callout(
        doc, "DANGER", "CONTROLLER DISCONNECTION & SAFETY LIMIT HANDLING",
        "1. AUTOMATIC TEST TERMINATION ON DISCONNECT: If the USB cable to the STM32 is unplugged or the controller loses power "
        "during an active test, MainWindow._on_connection_changed() automatically halts the test, flushes all buffered points to "
        "SQLite, and drops a bold red warning banner across the dashboard: 'CONTROLLER DISCONNECTED - TEST AUTO-SAVED & STOPPED' "
        "[CODE: ui_layout.py:L2025-L2028]. No blocking modal dialogs are displayed, preventing touchscreen UI lockups.\n"
        "2. DISPLACEMENT LOWER-LIMIT ENFORCEMENT: If raw displacement drops below 3.500 mm, the motor stops instantly, Jog Down "
        "is disabled, and a warning dialog instructs the operator to Jog Up [CODE: ui_layout.py:L1820-L1831]."
    )

    add_section_heading(doc, "3.1", "PySide6 Architecture & Composition Root")
    doc.add_paragraph(
        "[CODE: main.py, ui_layout.py] The graphical interface is built with PySide6 (Qt6 for Python). The software architecture "
        "separates UI layout, serial transport, real-time plotting, and persistence into dedicated modules:"
    )

    gui_modules = [
        ("Composition Root (main.py)", "Instantiates QApplication, sets Qt touch attributes (AA_SynthesizeMouseForUnhandledTouchEvents=True), applies GLOBAL_STYLESHEET, forces Segoe UI 12pt font, and switches between showMaximized() and showFullScreen() with hidden cursor based on KIOSK_MODE."),
        ("Presentation Layer (ui_layout.py)", "Owns MainWindow (1024x600 layout), navigation sidebar, and 4 stacked pages: Sample Parameters (tab 0), Test Dashboard (tab 1), Test Analysis (tab 2), and Settings (tab 3)."),
        ("Serial Worker (serial_manager.py)", "Runs SerialManager(QThread). Executes continuous background reads, ST-Link port scanning, and command dispatching without blocking the main event loop."),
        ("Graphing Engine (graph_manager.py)", "Wraps pyqtgraph.PlotWidget with dual y-axes (Displacement and Temperature) and ViewBox downsampling safety nets."),
        ("Persistence Engine (data_logger.py)", "Encapsulates SQLite WAL logging, rotating backups, crash auto-recovery, and CSV exports."),
        ("Configuration Manager (settings_manager.py)", "Loads and saves hmi_settings.json, redirecting file operations to /mnt/data/ under Linux.")
    ]
    add_def_table(doc, gui_modules)

    add_section_heading(doc, "3.2", "Threading Model and Qt Signals")
    doc.add_paragraph(
        "[CODE: serial_manager.py:L22-L31, ui_layout.py:L1766-L1768] Thread boundaries strictly follow Qt Signal-Slot architecture. "
        "The background worker thread never modifies UI elements directly:"
    )

    signal_headers = ["Qt Signal Name", "Payload Signature", "Emitter", "Receiver / Slot", "Description"]
    signal_rows = [
        ("new_data", "float, float, float, int", "SerialManager", "MainWindow.update_graph", "Carries (elapsed_s, disp_raw, temp_raw, enc_counts) at 20 Hz. Updates readouts, evaluates limits, and drives 1 Hz logging."),
        ("connection_status_changed", "bool, str", "SerialManager", "MainWindow._on_connection_changed", "Carries (is_connected, port_or_error). Toggles disconnect banner and auto-saves tests upon connection loss."),
        ("pullback_done", "None", "SerialManager", "MainWindow._on_pullback_done", "Emitted when STM32 transmits PULLBACK_DONE. Displays break test completion modal dialog.")
    ]
    add_header_table(doc, signal_headers, signal_rows, col_widths=[Inches(1.8), Inches(1.3), Inches(1.0), Inches(1.5), Inches(1.67)])

    add_section_heading(doc, "3.3", "UI Page Descriptions & Operator Flow")
    doc.add_paragraph(
        "[CODE: ui_layout.py:L533-L1760] The application interface is structured into four primary navigation tabs:"
    )

    page_defs = [
        ("Tab 0: Sample Parameters", "Form wrapped in an invisible QScrollArea to prevent window clipping under DPI scaling. Operator selects mode: 'TEST' (requires Sample ID, Test Number, Business Type, Span Length, Width, Height) or 'CALIBRATION' (requires Calibration Name). Optional fields: Constant Load (N), Target Heat Rate (deg C/min), Remarks."),
        ("Tab 1: Test Dashboard", "Live operations console. Displays numerical readouts for Displacement (blue), Temperature (red), Encoder Position, and Peak Displacement. Contains Tare Disp button, Motor Jog Up / Down buttons, Motor Stop button, Break Detection toggle badge, and the real-time dual-axis graph."),
        ("Tab 2: Test Analysis", "Historical test review. Loads completed tests from SQLite. Date column is intentionally suppressed to prevent operator confusion from lack of an RTC battery. Displays test duration, sample ID, and parameters. Features 'Load Test Graph' to inspect historical curves and 'Export to USB' to write CSV files."),
        ("Tab 3: Settings", "Configuration dashboard wrapped in QScrollArea. Shows controller connection status. Allows editing displacement calibration factor, jog velocity RPM, pullback speed RPM, pullback distance mm, and break drop threshold mm. Guarded by admin login.")
    ]
    add_def_table(doc, page_defs)

    add_section_heading(doc, "3.4", "Break Detection & Auto-Pullback Algorithm")
    doc.add_paragraph(
        "[CODE: ui_layout.py:L1894-L1948] The break detection routine protects specimen fixtures and identifies rupture events "
        "automatically during testing:"
    )

    break_steps = [
        ("1. Peak Tracking", "During active recording, after displacement is tared, MainWindow continuously tracks the maximum compression travel: if comp_disp > _break_peak_disp: _break_peak_disp = comp_disp [CODE: ui_layout.py:L1900]."),
        ("2. Rupture Detection Condition", "A break event triggers if compression displacement drops below peak by break_disp_delta_threshold (default 0.5 mm): if _break_peak_disp - comp_disp >= threshold [CODE: ui_layout.py:L1905]."),
        ("3. Action Mode 0 (Stop Only)", "If break_action_mode == 0, the test stops quietly, the motor halts, and an information dialog reports the peak displacement and drop value [CODE: ui_layout.py:L1934-L1942]."),
        ("4. Action Mode 1 (Stop + Pullback)", "If break_action_mode == 1, the GUI calculates encoder pullback counts: pb_counts = int(pullback_dist_mm * 500 counts/mm). It immediately sends 'PullSpeed:<rpm>' and 'Pullback:<counts>' to the STM32, sets UI status to 'PULLING BACK...', and stops recording quietly in the background without blocking modals [CODE: ui_layout.py:L1912-L1932]."),
        ("5. Retraction Completion", "When the motor completes retraction, the STM32 sends 'PULLBACK_DONE\\r\\n'. SerialManager catches this marker and emits pullback_done, triggering _on_pullback_done() to display the final test summary dialog [CODE: ui_layout.py:L1944-L1948].")
    ]
    add_def_table(doc, break_steps)

    # =========================================================================
    # CHAPTER 4: HARDWARE, ELECTRONICS & WIRING REFERENCE (Document 4)
    # =========================================================================
    add_chapter_heading(doc, 4, "Hardware, Electronics and Wiring Reference")

    add_callout(
        doc, "DANGER", "HIGH VOLTAGE MAINS AND DC BUS POWER HAZARD",
        "The control enclosure contains 230V AC mains wiring powering the Mean Well SMPS units and Schneider contactor, "
        "alongside 24V DC power rails driving the Leadshine stepper drive. Before opening the enclosure or modifying wiring: "
        "(1) Switch off the main circuit breaker (MCB); (2) Disconnect the 230V AC mains plug; (3) Wait at least 3 minutes "
        "for drive bus capacitors to fully discharge."
    )

    add_section_heading(doc, "4.1", "Master Electrical Bill of Materials (BOM)")
    doc.add_paragraph(
        "[DOC: St Gobain Project 1 BOM Electrical.xlsx] The electrical control enclosure incorporates industrial-grade "
        "components detailed in the authoritative project bill of materials:"
    )

    bom_headers = ["Component / Part Name", "Manufacturer", "Specification / Purpose", "Qty", "Vendor / Reference"]
    bom_rows = [
        ("Raspberry Pi 5 4GB", "Raspberry Pi", "HMI Host Controller (64-bit Quad-Core ARM)", "1", "Official Distributor"),
        ("Active Cooler for Pi 5", "Raspberry Pi", "PWM heatsink and fan assembly", "1", "Official Distributor"),
        ("27W USB-C Power Supply", "Raspberry Pi", "5.1V / 5.0A official PSU for Pi 5", "1", "Official Distributor"),
        ("Waveshare 10.1\" Touch Display", "Waveshare", "1024x600 Capacitive Touch LCD Panel", "1", "Robu.in / Waveshare"),
        ("Micro-HDMI to HDMI Cable (2m)", "Raspberry Pi", "Video feed to display HDMI-1", "1", "Official Distributor"),
        ("STM32 Nucleo-F446RE", "STMicroelectronics", "Microcontroller evaluation board (84 MHz)", "1", "Mouser / Digikey"),
        ("Leadshine CS-M21704", "Leadshine", "Closed-loop stepper motor (NEMA 17, 0.4 Nm)", "1", "Leadshine Direct"),
        ("Leadshine CS2RS-D507", "Leadshine", "Closed-loop Modbus RTU stepper drive (24-50V)", "1", "Leadshine Direct"),
        ("CABLEM-RZ1M5", "Leadshine", "Driver Power Cable (1.5 m)", "1", "Leadshine Direct"),
        ("CABLEM-BM1M5", "Leadshine", "Driver to Motor Encoder Cable (1.5 m)", "1", "Leadshine Direct"),
        ("CABLE-TX0M3-BUS", "Leadshine", "RS-485 Communication Cable (0.3 m)", "1", "Leadshine Direct"),
        ("Micro-Epsilon induSENSOR DTD-10G8", "Micro-Epsilon", "LVDT displacement sensor (-6 to +6 mm, 0.1 um res)", "1", "Micro-Epsilon India"),
        ("Eurotherm 3504 Controller", "Eurotherm", "High-temperature process controller (RS-485)", "1", "Eurotherm / Schneider"),
        ("Mean Well LRS-150-24", "Mean Well", "24V DC / 6.5A SMPS (Motor drive and sensors)", "1", "Mean Well Distributor"),
        ("Mean Well RS-25-5", "Mean Well", "5V DC / 5.0A SMPS (Logic and converters)", "1", "Mean Well Distributor"),
        ("Acti9 A9N1P04C MCB", "Schneider Electric", "4A Single Pole C-Curve MCB (Safety disconnect)", "1", "Schneider Electric"),
        ("EasyPact LC1E0910M7 Contactor", "Schneider Electric", "230V AC Coil 9A Power Cut-Off Contactor", "1", "Schneider Electric"),
        ("Isolated TTL to RS485 Converter", "Waveshare", "Rail-mount galvanic isolated transceiver module", "3", "Robu.in / Waveshare"),
        ("Harmony XB5 Stop Push Button", "Schneider Electric", "NC contact red flush pushbutton (Stop)", "1", "Schneider Electric"),
        ("Harmony XB5 Start Push Button", "Schneider Electric", "NO contact green flush pushbutton (Start)", "1", "Schneider Electric"),
        ("XB7EV03MPN Indicator Lamp", "Schneider Electric", "Green LED Power Indicator (230V AC)", "1", "Schneider Electric"),
        ("SanDisk Cruzer Blade 8GB", "SanDisk", "USB 2.0 Pen Drive (Local CSV test export)", "1", "Amazon.in"),
        ("Interconnect PCB", "Teqtis", "Custom daughterboard integrating Nucleo & terminals", "1", "Teqtis Fabrication"),
        ("JIGO Cooling Fan (80x80x25mm)", "JIGO", "24V DC Brushless enclosure cooling fan (140mA)", "2", "Local Vendor")
    ]
    add_header_table(doc, bom_headers, bom_rows, col_widths=[Inches(1.8), Inches(1.1), Inches(1.8), Inches(0.4), Inches(1.17)])

    add_section_heading(doc, "4.2", "Galvanic Isolation & Signal Routing Architecture")
    doc.add_paragraph(
        "[DOC: BOM, CONFIG: st_gobain-mtr.ioc] Industrial environments present severe electromagnetic interference (EMI) "
        "generated by high-current furnace heating elements and stepper drive pulse-width modulation. The system enforces "
        "three independent, galvanically isolated RS-485 channels:"
    )

    iso_defs = [
        ("Channel 1: Motor Bus (USART1)", "Connects STM32 PA9/PA10 to Waveshare Isolated Converter #1. Differential output (A/B) connects to Leadshine CS2RS drive port CN3. Provides 600W lightning and surge protection, isolating microcontroller logic from drive switching noise."),
        ("Channel 2: Displacement Bus (USART3)", "Connects STM32 PC10/PC11 to Waveshare Isolated Converter #2. Differential output connects to Micro-Epsilon MSC7xxx controller. Operates at 256000 baud with Even parity, preventing ground loop offsets on sub-micron measurements."),
        ("Channel 3: Furnace Controller (UART5)", "Connects STM32 PC12/PD2 to Waveshare Isolated Converter #3. Differential output connects to Eurotherm 3504 rear terminals (HD/HE). Isolates furnace thermal thermocouple voltages from the low-voltage control enclosure.")
    ]
    add_def_table(doc, iso_defs)

    add_section_heading(doc, "4.3", "Leadshine CS2RS Stepper Drive Configuration")
    doc.add_paragraph(
        "[DOC: CS2RS_Series_User_Manual_V1.5.pdf] The Leadshine CS2RS-D507 drive must be configured via its onboard DIP switches "
        "and RS-485 registers before initial operation:"
    )

    drive_cfg = [
        ("Modbus Slave ID", "Configured to Slave ID 1. Hardware DIP switches SW1 through SW4 set to: SW1=ON, SW2=OFF, SW3=OFF, SW4=OFF (ID = 1)."),
        ("Baud Rate", "Configured to 115200 bps via DIP switches SW5 and SW6: SW5=OFF, SW6=ON."),
        ("RS-485 Termination", "DIP switch SW7 set to ON (enables built-in 120 Ohm bus termination resistor)."),
        ("Motor Model Configuration", "DIP switch SW8 set to select matching CS-M21704 motor parameter table."),
        ("Control Mode", "Configured for PR Mode (Path Routing Mode). Register 0x6200 is dynamically initialized by firmware to 0x0012 (Path 0, Velocity Mode, Interrupt Enabled).")
    ]
    add_def_table(doc, drive_cfg)

    # =========================================================================
    # CHAPTER 5: OPERATIONS, CALIBRATION & RUNBOOKS (Document 5)
    # =========================================================================
    add_chapter_heading(doc, 5, "System Operations, Calibration and Runbooks")

    add_callout(
        doc, "WARNING", "PRE-TEST DISPLACEMENT TARE CHECK",
        "Always verify physical specimen contact and zero the displacement sensor using the 'Tare Disp' button before "
        "clicking 'Start Test'. Starting a test with an un-tared sensor will corrupt compression displacement calculations "
        "and prevent the break detection algorithm from triggering correctly."
    )

    add_section_heading(doc, "5.1", "Runbook 1: System Cold Start and Boot Procedure")
    doc.add_paragraph("Follow this sequence to power up the test bench from a cold state:")
    doc.add_paragraph("Step 1: Inspect Enclosure and Wiring: Verify all cable connectors are secure and furnace thermocouple leads are connected.")
    doc.add_paragraph("Step 2: Engage Circuit Breaker: Switch on the Schneider Acti9 4A MCB inside the enclosure.")
    doc.add_paragraph("Step 3: Press Start Pushbutton: Press the green Schneider flush button on the front panel. The contactor will engage, illuminating the green power indicator lamp.")
    doc.add_paragraph("Step 4: Verify Boot Sequence: The Raspberry Pi 5 will boot, displaying the St. Gobain Plymouth splash screen. Within 15 seconds, the Cage compositor initializes and launches the HMI fullscreen.")
    doc.add_paragraph("Step 5: Verify Controller Connection: Check the top banner on the Live Dashboard. If 'CONTROLLER DISCONNECTED' appears, verify the USB connection to the Nucleo board.")

    add_section_heading(doc, "5.2", "Runbook 2: Normal Test Execution")
    doc.add_paragraph("Step 1: Open Tab 0 (Sample Parameters): Enter Sample ID, Test Number, Business Type, and specimen dimensions (Span Length, Width, Height in mm).")
    doc.add_paragraph("Step 2: Position Fixture: Switch to Tab 1 (Test Dashboard). Use the 'Jog Down' button to lower the actuator until light contact with the specimen is established.")
    doc.add_paragraph("Step 3: Tare Displacement: Tap the 'Tare Disp' button. Verify that the large numerical readout resets to '0.000 mm'.")
    doc.add_paragraph("Step 4: Enable Break Detection: Verify that the 'Break Detection' toggle button displays 'ENABLED' (green badge).")
    doc.add_paragraph("Step 5: Start Test: Tap 'Start Test'. The UI switches to Live View, the recording indicator turns RED ('RECORDING'), the timer begins, and real-time telemetry plots at 1 Hz.")

    add_section_heading(doc, "5.3", "Runbook 3: Specimen Rupture & Auto-Pullback Recovery")
    doc.add_paragraph("Step 1: Automated Rupture Trigger: Upon specimen rupture, the displacement drops by >= 0.5 mm from peak. The status badge immediately changes to 'PULLING BACK...'.")
    doc.add_paragraph("Step 2: Actuator Retraction: The STM32 reverses the stepper motor at 20 RPM until the target pullback distance (5.0 mm = 2500 counts) is reached.")
    doc.add_paragraph("Step 3: Test Finalization: Upon receiving PULLBACK_DONE, the test stops, data flushes to SQLite, and an information dialog displays the peak displacement and drop magnitude.")
    doc.add_paragraph("Step 4: Safe Removal: Verify furnace element power is cut, wait for cooling, and extract the fractured specimen.")

    add_section_heading(doc, "5.4", "Runbook 4: Silent USB CSV Data Export")
    doc.add_paragraph("Step 1: Insert USB Flash Drive: Insert the SanDisk USB pen drive into any available blue USB 3.0 port on the Raspberry Pi.")
    doc.add_paragraph("Step 2: Verify Automount: UDEV rule 99-usb-mount.rules will silently attach the drive to /media/usb within 2 seconds.")
    doc.add_paragraph("Step 3: Open Tab 2 (Test Analysis): Select the completed test from the history table. Tap 'Export to USB'.")
    doc.add_paragraph("Step 4: Verify Completion: A confirmation dialog displays: 'Export Successful: /media/usb/tests/<name>.csv'. The system forces an os.fsync() to guarantee complete write.")
    doc.add_paragraph("Step 5: Safely Remove: Unplug the USB drive directly. No manual unmount desktop command is required.")

    add_section_heading(doc, "5.5", "Runbook 5: Kiosk Maintenance & SD Card Unlock")
    doc.add_paragraph(
        "[DOC: walkthrough-kiosk setup.md] If filesystem maintenance is required on the Raspberry Pi 5:"
    )
    doc.add_paragraph("Step 1: Attach Keyboard: Plug a physical USB keyboard into the Pi.")
    doc.add_paragraph("Step 2: Switch to Root Console: Press Ctrl+Alt+F2 to open TTY2. Log in with user: insitumicron-rpi.")
    doc.add_paragraph("Step 3: Disable OverlayFS for Updates: Execute: sudo raspi-config nonint disable_overlayfs && sudo reboot.")
    doc.add_paragraph("Step 4: Execute Changes: Perform software edits or package updates in read-write mode.")
    doc.add_paragraph("Step 5: Re-Lock OverlayFS: Re-enable protection: sudo raspi-config nonint enable_overlayfs && sudo reboot.")

    # =========================================================================
    # CHAPTER 6: KNOWN ISSUES, ERRATA & RISK REGISTER (Document 6)
    # =========================================================================
    add_chapter_heading(doc, 6, "Known Issues, Safety Risks and Risk Register")

    add_callout(
        doc, "DANGER", "FUNCTIONAL SAFETY RISK SUMMARY",
        "Functional safety items take absolute precedence. The control enclosure relies on a manual power disconnect switch. "
        "The firmware kill-switch routine on PB5 is commented out, no hardware watchdog timer is initialized, and motor motion "
        "will continue running if the USB host cable disconnects during a test. Review the risk register below for workarounds."
    )

    add_section_heading(doc, "6.1", "Master Engineering Risk Register")
    doc.add_paragraph(
        "The following risk register tracks all identified defects, safety vulnerabilities, and operational errata across "
        "firmware, software, and hardware:"
    )

    risk_headers = ["ID", "Domain", "Risk Title & Severity", "Symptom & Impact", "Workaround / Mitigation", "Permanent Engineering Fix"]
    risk_rows = [
        ("RISK-01", "Firmware", "Commented Kill Switch [CRITICAL]", "PB5 kill switch logic commented out in Process_Motor(). No MCU-level emergency stop [CODE/OWNER].", "Operator must use enclosure red Stop button to cut contactor power [OWNER].", "Wire PB5 with 10k pull-up to physical switch; un-comment Process_Motor() check."),
        ("RISK-02", "Firmware", "Watchdog Timer Absence [HIGH]", "No IWDG/WWDG configured. Firmware freeze requires manual power cycle [CODE].", "Monitor heartbeat LED (PA5). Cycle power if telemetry freezes.", "Configure IWDG with 200 ms timeout in CubeMX; refresh in main loop."),
        ("RISK-03", "Firmware", "Motor Jog Direction Quirk [MEDIUM]", "Rarely, Jog buttons fail to move motor in commanded direction on initial tap [OWNER].", "Release jog button and tap again. Verify encoder readout responds.", "Add RS-485 bus flush and command echo validation in Process_Motor_TX_Queue()."),
        ("RISK-04", "Firmware", "Host Disconnect Motion Runaway [HIGH]", "STM32 continues running motor if Pi disconnects mid-motion [CODE].", "Press physical stop button on enclosure to halt motor.", "Add 500 ms host heartbeat watchdog in STM32; halt motor if no packet received."),
        ("RISK-05", "Software", "RTC Date Drift on Power Loss [LOW]", "Pi 5 lacks battery RTC; date resets after ungraceful shutdown [DOC].", "Date column suppressed from UI; tests identified by Run Number and Monotonic Duration.", "Install DS3231 I2C hardware RTC module with coin cell backup battery on Pi GPIO."),
        ("RISK-06", "Firmware", "Hardcoded Displacement Offset [MEDIUM]", "Offset hardcoded to -6.0 mm in main.c line 89 [CODE/OWNER].", "Must re-flash firmware if sensor bracket physical baseline changes.", "Store tare offset in STM32 internal Flash emulation; add TARE_DISP command."),
        ("RISK-07", "Software", "Plaintext Hardcoded Admin Password [MEDIUM]", "Admin password 'insitumicron' in ui_layout.py line 38 in plaintext [CODE].", "Restrict physical access to keyboard maintenance console.", "Store salted SHA-256 hash in /mnt/data/admin_hash.key."),
        ("RISK-08", "Firmware", "Eurotherm Modbus Timeout Glitch [LOW]", "Eurotherm partial frames log 'DBG: ET PARTIAL' on UART2 [CODE].", "State machine resets and retries automatically after 400 ms timeout.", "Increase UART5 RX buffer and optimize transceiver turnaround delay."),
        ("RISK-09", "Software", "Legacy Load Cell Residue [LOW]", "load_offset and load calibration factors remain in code/config [CODE/CONFIG].", "None required; unused variables do not affect measurement pipeline.", "Refactor ui_layout.py to purge unused load variables and settings keys.")
    ]
    add_header_table(doc, risk_headers, risk_rows, col_widths=[Inches(0.6), Inches(0.8), Inches(1.5), Inches(1.5), Inches(1.3), Inches(1.57)])

    # =========================================================================
    # CHAPTER 7: ENGINEERING DECISION LOG (Document 7)
    # =========================================================================
    add_chapter_heading(doc, 7, "Engineering Decision Log and Rationale")

    add_callout(
        doc, "NOTE", "RECORD OF ENGINEERING TRADE-OFFS",
        "This chapter captures the technical rationale behind key architectural decisions. Understanding why specific "
        "designs were chosen prevents regressions during future maintenance."
    )

    add_section_heading(doc, "7.1", "Key Architectural Decisions")
    doc.add_paragraph("The table below details major engineering trade-offs made during development:")

    decision_defs = [
        ("Decision 01: Single-SD Dual-State Storage", "Alternative: Dual USB drives or standard read-write ext4 rootfs. Rationale: Industrial operators cut power without shutdown. Standard ext4 corrupts boot files within weeks. Dual-state OverlayFS locks rootfs read-only, routing SQLite writes exclusively to /mnt/data, providing immunity to power cuts without needing dual SD cards [DOC: walkthrough-kiosk setup.md]."),
        ("Decision 02: Cage Wayland Compositor", "Alternative: X11 / Matchbox / Openbox / Full Desktop. Rationale: Full desktop environments consume excessive RAM, display taskbars, and present security risks. Cage provides a minimal, dedicated Wayland kiosk window compositor with hardware graphics acceleration and zero desktop clutter."),
        ("Decision 03: Non-Blocking Modbus Motor TX Queue", "Alternative: Synchronous HAL_UART_Transmit for all 5 Leadshine PR frames. Rationale: Sending 5 Modbus frames back-to-back blocks the CPU for > 15 ms and overruns the Leadshine input buffer. Implementing a circular queue with an exact 5 ms pacing delay eliminated packet loss [CODE: main.c:L189-L233]."),
        ("Decision 04: SQLite WAL Mode with 100-Point Buffering", "Alternative: Direct CSV disk writes on every sample or client-server MySQL. Rationale: Direct per-sample CSV writing incurs severe fsync latency and accelerates SD card flash wear. SQLite with Write-Ahead Logging (WAL) handles thousands of inserts/second safely and flushes in 100-point batches [CODE: data_logger.py:L10-L15]."),
        ("Decision 05: Direct DMA Reception for Encoder", "Alternative: Polling interrupt per byte. Rationale: Leadshine encoder responses stream at 115200 baud. DMA2 Stream 2 offloads CPU overhead and guarantees zero dropped bytes during active motor motion [CODE: main.c:L389-L414]."),
        ("Decision 06: Throttled 1 Hz Sampling Rate", "Alternative: Logging raw 20 Hz telemetry directly to disk. Rationale: High-temperature flexural creep tests run for dozens of hours. Logging at 20 Hz produces massive files without improving creep strain curve resolution. Throttling logging and plotting to 1 Hz while keeping numerical readouts at 4 Hz balanced responsiveness and file size."),
        ("Decision 07: Hardware-Level Contactor Disconnect", "Alternative: MCU-mediated software kill switch. Rationale: In high-force, high-temperature machinery, safety standards mandate physical galvanic disconnection of motor power rather than relying on software state machines [DOC: BOM, OWNER].")
    ]
    add_def_table(doc, decision_defs)

    # =========================================================================
    # CHAPTER 8: SYSTEM ACCESS, SECURITY & CREDENTIALS (Document 8)
    # =========================================================================
    add_chapter_heading(doc, 8, "System Access, Security and Administrative Credentials")

    add_callout(
        doc, "WARNING", "CREDENTIAL SECURITY & CUSTODY POLICY",
        "In accordance with corporate security rules, actual cryptographic private keys, passwords, and tokens are NOT "
        "written in plain text in this manual. This section records where credentials are stored, how access is controlled, "
        "and who holds administrative authority."
    )

    add_section_heading(doc, "8.1", "Administrative Access Registry")
    doc.add_paragraph(
        "[CODE: ui_layout.py:L37-L38, deploy/install_kiosk.sh] Access boundaries across software, OS, and hardware levels "
        "are catalogued below:"
    )

    cred_headers = ["Subsystem / Interface", "Access Role & Purpose", "Location / Storage Method", "Custodian & Authority"]
    cred_rows = [
        ("Raspberry Pi Linux OS", "User: insitumicron-rpi (Terminal / Maintenance)", "Stored in /etc/shadow on Raspberry Pi. Configured via raspi-config.", "InsituMicron Systems Lead"),
        ("Sudoers Execution Policy", "Passwordless mount/umount permissions for /mnt/data", "Stored in /etc/sudoers.d/010_kiosk-mount (read-only 0440).", "Automated deployment script"),
        ("HMI GUI Admin Panel", "Unlocks Calibration and Break Settings", "Hardcoded in ui_layout.py lines 37-38 (_ADMIN_ID, _ADMIN_PASS) [CODE].", "Engineering Team / Lead Maintainer"),
        ("STM32 Debug Interface", "SWD flashing via ST-Link V2/V3", "Hardware Morpho header pins on Nucleo board (no read-out protection).", "Firmware Engineering Team"),
        ("Source Code Repository", "Local Git working tree at C:\\Users\\rohit\\work\\GUI files\\Pi_HMI\\Pi_HMI_mtr", "Local workstation storage.", "Departing Engineer / Archives")
    ]
    add_header_table(doc, cred_headers, cred_rows, col_widths=[Inches(1.8), Inches(1.5), Inches(1.8), Inches(1.17)])

    add_section_heading(doc, "8.2", "Software Licensing & Third-Party Assets")
    doc.add_paragraph("All software libraries used in the repository comply with corporate commercial deployment guidelines:")
    lic_defs = [
        ("PySide6 (Qt for Python)", "Licensed under GNU LGPLv3. Dynamically linked without proprietary Qt source modifications, permitting commercial deployment."),
        ("pyqtgraph", "Licensed under MIT License. Permits commercial integration, modification, and distribution."),
        ("SQLite", "Dedicated to the Public Domain. No licensing constraints or attribution requirements."),
        ("STMicroelectronics HAL", "Licensed under BSD 3-Clause / Apache 2.0 (STMicroelectronics proprietary terms allowing commercial binary redistribution)."),
        ("Linux Kernel & Plymouth", "Licensed under GNU GPLv2. Embedded appliance distribution complies with source disclosure rules on demand.")
    ]
    add_def_table(doc, lic_defs)

    # =========================================================================
    # CHAPTER 9: IN-FLIGHT WORK, MAINTENANCE & ROADMAP (Document 9)
    # =========================================================================
    add_chapter_heading(doc, 9, "In-Flight Work, Maintenance and Transition Roadmap")

    add_callout(
        doc, "NOTE", "STATUS OF DELIVERABLES",
        "[OWNER] The Saint-Gobain flexural creep rig is fully assembled, commissioned, and operational at Saint-Gobain Research India. "
        "There are no uncommitted branches or half-finished features. The following checklists guide future maintenance and refactoring."
    )

    add_section_heading(doc, "9.1", "30-Day Transition Checklist")
    doc.add_paragraph("Tasks to be completed within the first 30 days of ownership:")
    d30_tasks = [
        ("Task 1: Cold Build Verification", "Clone the repository to a secondary development laptop. Set up venv310, verify dependencies, and confirm that test_init.py launches MainWindow successfully."),
        ("Task 2: Firmware Re-Compilation", "Import st_gobain-HMI into STM32CubeIDE v1.18.1. Build the Debug configuration and verify 0 errors."),
        ("Task 3: Full Backup Archive", "Create an offline image of the physical Raspberry Pi 5 SD card using dd or Win32DiskImager. Store the compressed image in company cloud archives."),
        ("Task 4: Spare Parts Audit", "Verify inventory of critical spares: 1x STM32 Nucleo-F446RE, 1x Waveshare isolated RS-485 converter, 1x Leadshine CS2RS-D507 drive, and 1x Micro-Epsilon LVDT sensor.")
    ]
    add_def_table(doc, d30_tasks)

    add_section_heading(doc, "9.2", "60-Day & 90-Day Engineering Roadmap")
    doc.add_paragraph("Recommended architectural improvements for future maintenance releases:")
    d90_tasks = [
        ("60-Day: IWDG Watchdog Integration", "Integrate the Independent Watchdog (IWDG) into the STM32 firmware with a 200 ms timeout window. Add refresh calls inside the main loop to prevent silent controller lockups."),
        ("60-Day: Hardware RTC Battery Installation", "Install a DS3231 I2C real-time clock module with a CR2032 coin cell onto the Raspberry Pi 5 GPIO header. Configure Linux hwclock to maintain absolute timestamps across power outages."),
        ("90-Day: Dynamic Displacement Baseline Offset", "Migrate me_tare_offset from a hardcoded firmware constant (-6.0 mm) to an emulated Flash register. Implement a TARE_DISP serial command allowing operators to calibrate sensor zero from the GUI Settings tab."),
        ("90-Day: Hardware Kill Switch Wiring", "Wire an external 10 kOhm pull-up resistor and physical emergency stop contact to Nucleo pin PB5. Re-enable the Process_Motor() kill switch polling check to achieve MCU-level emergency shutdown.")
    ]
    add_def_table(doc, d90_tasks)

    # =========================================================================
    # CHAPTER 10: HANDOVER VERIFICATION & SIGN-OFF (Document 10)
    # =========================================================================
    add_chapter_heading(doc, 10, "Handover Verification and Sign-Off Record")

    add_callout(
        doc, "NOTE", "COLD-READ TEST PROTOCOL",
        "A successful knowledge transfer requires that a qualified engineer can build, flash, run, and diagnose the system "
        "using solely this manual, without verbal guidance from the departing engineer."
    )

    add_section_heading(doc, "10.1", "Cold-Read Verification Tasks")
    doc.add_paragraph("The successor should execute and record the following verification steps:")

    v_headers = ["#", "Verification Task", "Expected Result", "Verified By / Date", "Result"]
    v_rows = [
        ("1", "Clean GUI Launch", "MainWindow launches; sidebar, dashboard, and graph render with 0 console tracebacks.", "Incoming Engineer", "PASS / FAIL"),
        ("2", "Firmware Clean Build", "STM32CubeIDE compiles st_gobain-HMI with 0 errors and 0 critical warnings.", "Incoming Engineer", "PASS / FAIL"),
        ("3", "ST-Link Telemetry Ingestion", "Connecting Nucleo streams 20 Hz CSV telemetry; dashboard readouts update smoothly.", "Incoming Engineer", "PASS / FAIL"),
        ("4", "Manual Motor Jogging", "Tapping Jog Up and Jog Down advances and retracts the actuator stage reliably.", "Incoming Engineer", "PASS / FAIL"),
        ("5", "Displacement Limit Check", "Jogging down below 3.500 mm triggers safety halt and disables Jog Down.", "Incoming Engineer", "PASS / FAIL"),
        ("6", "Test Run & USB CSV Export", "Executing 60-second test logs to SQLite; exporting to USB generates valid CSV.", "Incoming Engineer", "PASS / FAIL"),
        ("7", "Kiosk Reboot Recovery", "Unplugging power mid-test reboots into kiosk mode; interrupted test marked _RECOVERED.", "Incoming Engineer", "PASS / FAIL")
    ]
    add_header_table(doc, v_headers, v_rows, col_widths=[Inches(0.4), Inches(1.8), Inches(2.2), Inches(1.1), Inches(0.77)])

    add_section_heading(doc, "10.2", "Formal Handover Sign-Off")
    doc.add_paragraph(
        "By signing below, the departing systems engineer and technical management confirm that all operational knowledge, "
        "architectural decisions, firmware sources, software repositories, and safety risks for the Saint-Gobain flexural "
        "creep testing system have been completely documented and archived:"
    )

    sign_headers = ["Role", "Name", "Signature", "Date"]
    sign_rows = [
        ("Departing Systems Engineer", "Lead Embedded & Software Engineer", "", "2026-11-20"),
        ("Technical Reviewer", "Senior Instrumentation Engineer", "", ""),
        ("Company Archive Custodian", "Head of Engineering / Archive Lead", "", "")
    ]
    add_header_table(doc, sign_headers, sign_rows, col_widths=[Inches(2.0), Inches(2.0), Inches(1.27), Inches(1.0)])

    # Save complete master document
    print(f"Saving Complete Master Technical Handover Manual to {output_path}...")
    doc.save(output_path)
    print("Master Manual successfully created!")


if __name__ == "__main__":
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
    target_docx = os.path.join(out_dir, "InsituMicron_StGobain_Technical_Handover_Manual_V1.0.docx")
    build_stgobain_manual(target_docx)
