import os
import json
import platform

class SettingsManager:
    """
    Handles persistent settings (Calibration Factors, Break Detection).
    On the Pi (Linux), saves to /mnt/data/ to bypass the OverlayFS shield.
    """
    def __init__(self):
        kiosk_data_dir = "/mnt/data"
        if platform.system() == "Linux" and os.path.isdir(kiosk_data_dir):
            self.settings_path = os.path.join(kiosk_data_dir, "hmi_settings.json")
        else:
            self.settings_path = os.path.join(os.path.dirname(__file__), "hmi_settings.json")
            
        self.settings = {
            # Sensor
            "load_calibration_factor":  1.0,
            "disp_calibration_factor":  1.0,
            # Motor
            "motor_jog_velocity_rpm":   10.0,
            "pullback_speed_rpm":        20.0,
            # Break detection
            "break_disp_delta_threshold": 0.5,
            "break_arm_threshold":       20.0,
            "break_drop_fraction":       0.40,
            # Break action & pullback
            "break_action_mode":         1,     # 0 = Stop Only, 1 = Stop + Pullback
            "pullback_distance_mm":      5.0,
        }
        self.load()

    def load(self):
        """Load settings from JSON file if it exists.
        Merges ALL keys from the file into self.settings (not just pre-listed ones),
        so any key written by set() is always restored after reboot.
        """
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Merge everything from file — new keys added by set() are preserved
                    self.settings.update(data)
            except Exception as e:
                print(f"Failed to load settings: {e}")

    def save(self):
        """Save current settings to JSON file."""
        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()
