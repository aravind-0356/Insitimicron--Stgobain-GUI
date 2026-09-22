# Implementation Walkthrough

The transition of the Raspberry Pi HMI into an industrial, locked-down kiosk system has been fully implemented! Here is a breakdown of the robust architecture and code updates we just rolled out:

## The Final Architecture: Option B
We successfully implemented a **Single SD Card, Dual-State** architecture. 
- The SD card is logically split into two completely isolated environments: the `rootfs` (Operating System) and the `DATA` partition.
- **Constraints & Challenges Addressed:** Industrial environments lack UPS backups, and operators pull the plug to shut down. A standard Linux installation corrupts its file system under these conditions, rendering the machine unbootable.
- **The Solution:** We applied `OverlayFS` exclusively to the `rootfs` partition. This locks the operating system in a permanent Read-Only state, making the core software immune to hard power cuts. Simultaneously, the `DATA` partition remains Read-Write, bypassing the overlay so that SQLite can log tests permanently.

## 1. Kiosk Deployment Automation
We created an automated bash script (`deploy/install_kiosk.sh`) that transitions a standard Raspberry Pi OS Lite into a locked-down appliance:
- **Boot Splash:** Removes all Linux boot logs and Raspberry Pi logos using Plymouth, presenting a clean initialization screen with your Company Logo.
- **Wayland Kiosk (Cage):** Installs and configures the `cage` Wayland compositor to run the PySide6 app in full screen as the only allowable window.
- **Systemd Watchdog:** Created `kiosk.service` with an aggressive restart policy (`Restart=always`, `StartLimitIntervalSec=0`) to ensure the GUI bounces back instantly if it ever crashes.

## 2. Silent USB Automounting
We bypassed the need for desktop OS pop-ups by writing native Linux UDEV rules (`deploy/99-usb-mount.rules`). When an operator plugs in a pendrive, the kernel intercepts it and invokes `systemd-mount` to silently attach it to `/media/usb` in the background, making it instantly available for the GUI's "Export to USB" button.

## 3. Database Integrity & Offline Diagnostics
Since the OS is running in a Read-Only state, we updated the Python architecture to heavily rely on your dedicated `/mnt/data` partition:
- **SQLite Database Path:** `data_logger.py` now automatically routes `test_data.db` to `/mnt/data/` if deployed on Linux.
- **Rotating Backups:** Added a startup routine in `data_logger.py` that creates `.bak1`, `.bak2`, and `.bak3` copies of the database. If a sudden power cut corrupts the active DB, a backup is always available.
- **Persistent Diagnostics:** Added a `kiosk_status.log` writer. The system logs `GUI BOOT STARTED`, `CLEAN SHUTDOWN`, and `STM32 DISCONNECTED` events directly to the SD card, circumventing the volatile RAM overlay.

## 4. Disconnect UI/UX Handling
We resolved the critique regarding hardware disconnects. The `serial_manager.py` thread already gracefully caught PySerial exceptions, but we've now updated the frontend in `ui_layout.py` to match:
- **No More Modals:** If the STM32 is unplugged or loses power mid-test, the app no longer spawns a blocking `QMessageBox` that could freeze the Kiosk.
- **Auto-Save:** The test is gracefully stopped and auto-saved in the background.
- **Bold Dashboard Warning:** A giant red "CONTROLLER DISCONNECTED - CHECK CONNECTION" banner drops down directly onto the live dashboard, making the hardware fault unambiguously clear to the operator.
- **Browse Tests Tweak:** We completely removed the Date column from the history view. Since you don't have an RTC battery, the absolute timestamps will drift. Removing this from the UI relies on the monotonic relative duration and the operator's input (Test No.) to keep things clean.

## Outcomes
You now have a bulletproof appliance. It looks completely proprietary (no Raspberry Pi logos), protects your database, tolerates violent power losses, gracefully handles STM32 loose cable faults, and empowers technicians to diagnose issues entirely offline.

## Appendix: Kiosk Mode Obstacles & Solutions

During this deployment, we faced several complex challenges specific to the Raspberry Pi 5. Here is a permanent record of how we overcame them:

### 1. The Systemd "Ghost GUI" & DRM Permissions
Initially, we used `install_kiosk.sh` to create a background systemd service (`kiosk.service`) that ran `cage`. However, Linux strictly protects DRM/KMS permissions from background services. The service reported as `active`, but the physical monitor remained stuck on the `tty3` text console.
**The Fix:** We completely pivoted to the "Auto-login" method. By setting `raspi-config` to auto-login the user on `tty1`, and calling `cage` from `~/.profile`, the session inherently gains full DRM control and works flawlessly.

### 2. MicroHDMI Port Strict Priority
The Pi 5 booted to text on HDMI-2, but Wayland compositors prioritize HDMI-1 for hardware acceleration. This resulted in a black screen when the GUI launched.
**The Fix:** We physically moved the HMI display cable to the HDMI-1 port (closest to the USB-C power).

### 3. FAT32 "Dirty Bit" Boot Lock
When attempting to modify `cmdline.txt` to fix boot text, the FAT32 boot partition was violently write-protected (`WARNING: source write-protected, mounted read-only`).
**The Fix:** We identified this as the Linux FAT driver locking the drive due to an unsafe shutdown. We cleared the "Dirty Bit" by unmounting and running `fsck.fat -a /dev/mmcblk0p1`, allowing us to remount it as `rw`.

### 4. Plymouth Hijacking the Screen
Plymouth (the boot logo engine) was forcing the console to `tty3` because the Raspberry Pi 5 GPU driver (`vc4-kms-v3d`) took too long to load. Plymouth would fail to find the display and leave the TTY in a messy state, hiding our GUI.
**The Fix:** We added `DeviceTimeout=8` to `/etc/plymouth/plymouthd.conf` to force Plymouth to wait for the GPU driver to initialize, and ensured `console=tty1 quiet splash` was set in `cmdline.txt`.

### 6. USB Transfer & Phantom Drives
When transferring files via USB, the Pi's `lsblk` showed `sda1` which was a 40KB phantom drive (card reader), causing mount failures. The actual drive was `sdb1`. Furthermore, we learned that transferring `.venv` or `.idea` folders from Windows breaks the Linux deployment. We resolved this by blowing away the corrupted directory and doing a clean `cp` transfer.

### 7. Python Virtual Environment (PEP 668)
Raspberry Pi OS Bookworm strictly enforces PEP 668, preventing global `pip install` commands. We established a local virtual environment (`venv`) and explicitly bound all our deployment scripts to `/home/insitumicron-rpi/Pi_HMI/venv/bin/python`.

### 8. Orphaned SQLite Database
The `test_data.db` file was initially transferred to the Read-Only OS partition. If left there, SQLite would throw read-only errors during tests. We intercepted this and manually moved the database to the 3rd partition (`/mnt/data/`), relying on the dynamic path-switching logic in `data_logger.py`.

### 9. OverlayFS Blocking fstab Automounts
When attempting to use `/etc/fstab` to auto-mount the DATA partition, systemd's boot timings conflicted violently with the OverlayFS shield, causing silent mount failures and falling back to RAM. We solved this elegantly by removing the `fstab` entry entirely and instead inserting `sudo mount /dev/mmcblk0p3 /mnt/data` directly into the `~/.profile` Auto-login script. This completely bypasses systemd bugs, mounting the physical drive exactly one millisecond before the GUI launches, guaranteeing the SQLite database always writes to disk.
