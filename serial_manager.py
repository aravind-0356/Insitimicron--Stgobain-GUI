# serial_manager.py
"""
Serial communication manager for the Pi HMI.
Handles UART data from the STM32 in a background QThread.
Currently includes a mock data generator for PC development.

Design:
  - Runs in a dedicated QThread so the GUI never blocks.
  - Emits (timestamp, sensor_value) via Qt signals.
  - In mock mode, generates a sine wave + noise at ~100Hz.
  - In real mode (Phase 3), will use pyserial to read UART lines.
"""

import time
import serial
import serial.tools.list_ports
from PySide6.QtCore import QThread, Signal

class SerialManager(QThread):
    """Background thread that provides sensor data to the GUI."""

    # Signal: (elapsed_time_seconds, disp_value, temp_value, encoder_counts)
    # encoder_counts replaces the old motor_status int — the GUI uses it for
    # the live encoder readout and auto-pullback distance tracking.
    new_data = Signal(float, float, float, int)
    
    # Signal: (is_connected, port_name_or_error_msg)
    connection_status_changed = Signal(bool, str)

    # Signal: emitted when STM32 sends PULLBACK_DONE marker
    pullback_done = Signal()

    def __init__(self):
        super().__init__()
        self.is_running = True
        self.is_logging = False  # Only log data when a test is active
        self.start_time = time.time()
        self.serial_port = None
        
        self.baudrate = 115200

    def run(self):
        """Main loop — attempts to connect to STM32 and reads data."""
        while self.is_running:
            if self.serial_port is None or not self.serial_port.is_open:
                # Attempt to find and connect
                port = self._find_stlink_port()
                if port:
                    try:
                        self.serial_port = serial.Serial(port, self.baudrate, timeout=1.0)
                        self.connection_status_changed.emit(True, port)
                        self.serial_port.reset_input_buffer()
                    except Exception as e:
                        self.connection_status_changed.emit(False, str(e))
                        self.serial_port = None
                        time.sleep(2)
                        continue
                else:
                    self.connection_status_changed.emit(False, "Searching for Controller...")
                    time.sleep(2)
                    continue

            # Connected - read data
            try:
                raw = self.serial_port.readline().decode('utf-8').strip()
                if not raw:
                    continue

                # Strip optional leading '$' (legacy framing)
                line = raw[1:] if raw.startswith('$') else raw

                # --- One-shot event markers ---
                if line == "PULLBACK_DONE":
                    self.pullback_done.emit()
                    continue

                # --- Normal telemetry: "disp,temp,encoder_counts" ---
                parts = line.split(',')
                if len(parts) >= 3:
                    disp_val  = float(parts[0])
                    temp_val  = float(parts[1])
                    enc_val   = int(parts[2])   # signed int32 encoder position
                    elapsed   = time.time() - self.start_time
                    self.new_data.emit(elapsed, disp_val, temp_val, enc_val)
            except (serial.SerialException, OSError, UnicodeDecodeError, ValueError) as e:
                # Disconnection or garbage data
                if isinstance(e, (serial.SerialException, OSError)):
                    if self.serial_port and self.serial_port.is_open:
                        try:
                            self.serial_port.close()
                        except Exception:
                            pass
                    self.serial_port = None
                    self.connection_status_changed.emit(False, "Connection Lost")
                    time.sleep(1)  # Reconnect delay to prevent tight CPU looping
            except Exception as e:
                if not self.is_running:
                    break
                print(f"Unexpected serial error: {e}")
                if self.serial_port:
                    try:
                        self.serial_port.close()
                    except:
                        pass
                self.serial_port = None
                time.sleep(1)

        # Clean up on exit
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except:
                pass
            self.serial_port = None

    def _find_stlink_port(self):
        """Scans COM/tty ports for ST-Link VCP."""
        ports = serial.tools.list_ports.comports()
        for p in ports:
            # STMicroelectronics VID is 0483
            if p.vid == 0x0483 or (p.description and "STLink" in p.description):
                return p.device
                
        # Fallback: if no STLink found, just return the first available USB serial (for dev purposes)
        # In strict prod, we might only return STLink
        for p in ports:
            if "USB" in p.description or "ACM" in p.device:
                return p.device
        return None

    def start_reading(self):
        """Start the background thread."""
        self.start_time = time.time()
        self.start()

    def stop(self):
        """Stop the thread gracefully."""
        self.is_running = False
        self.wait()

    def send_command(self, cmd_str):
        """Send a string command to the STM32."""
        if self.serial_port and self.serial_port.is_open:
            try:
                if not cmd_str.endswith('\n'):
                    cmd_str += '\n'
                self.serial_port.write(cmd_str.encode('utf-8'))
                self.serial_port.flush()
            except Exception as e:
                print(f"Failed to send command {cmd_str}: {e}")
