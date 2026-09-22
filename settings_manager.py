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
            "load_calibration_factor": 1.0,
            "disp_calibration_factor": 1.0,
            "break_arm_threshold": 20.0,
            "break_drop_fraction": 0.40,
            "ctd_enabled": True,
            "ctd_threshold": 10.0
        }
        self.load()

    def load(self):
        """Load settings from JSON file if it exists."""
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Update defaults with loaded data
                    for key in self.settings:
                        if key in data:
                            self.settings[key] = data[key]
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
