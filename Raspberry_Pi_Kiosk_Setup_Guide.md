# Raspberry Pi 5 Industrial Kiosk Setup Guide

This guide covers the exact steps to transition from a blank SD card on your Windows PC to a fully locked-down Industrial HMI running your PySide6 application.

## Architecture Overview (Option B: Partitioned SD Card + OverlayFS)

To meet the strict requirements of an industrial environment without over-engineering the hardware, we have adopted **Option B**: A single SD card split into isolated partitions, protected by OverlayFS.

> [!TIP]
> **Why this approach?** Industrial operators frequently shut down machines by pulling the main power plug instead of performing a clean shutdown. If Linux is writing a background file when power is lost, the SD card will corrupt and the machine will refuse to boot. This architecture makes the OS physically indestructible by locking it as Read-Only.

### Advantages
- **Power-Cut Immunity:** The operating system lives on a Read-Only partition. You can yank the power cord 1,000 times, and it will boot perfectly every single time.
- **Single Storage Device:** No dangling external USB drives required for internal storage. Everything is neatly contained on a single SD card.
- **Isolated Data:** Your test data lives securely on its own separate `DATA` partition. If the database ever corrupts, the operating system remains unharmed, allowing the GUI to boot up and technicians to repair the database without re-flashing the whole machine.

### Disadvantages / Constraints
- **Initial Setup Effort:** Because the OS is locked to Read-Only, you cannot save data normally. You must spend an extra 5 minutes using a Windows Partition tool to split the SD card *before* putting it into the Raspberry Pi.
- **Update Complexity:** If you ever want to update the Python code in the future, you must temporarily disable the OverlayFS, push the new code, and re-enable OverlayFS.

### Outcomes
A robust, offline industrial appliance that boots straight to your company logo, silently automounts operator export pendrives, and survives decades of electrical abuse.

---

## Prerequisites
1. **MicroSD Card** (16GB+ recommended, e.g., SanDisk Extreme).
2. Your **Company Logo** as a `.png` file (e.g., `logo.png`).

---

## Phase 1: Flashing the OS (On your Windows PC)
1. Download and open **Raspberry Pi Imager** on your Windows laptop.
2. Under **Choose Device**, select **Raspberry Pi 5**.
3. Under **Choose OS**, go to *Raspberry Pi OS (Other)* -> **Raspberry Pi OS Lite (64-bit)**. 
   - *Note: You MUST use the Lite version. The full desktop version includes window managers that will fight with our `cage` Kiosk compositor.*
4. Under **Choose Storage**, select your MicroSD card.
5. Click **Next** -> **Edit Settings**:
   - **Hostname:** `stgobain-hmi-lc`
   - **Username/Password:** `insitumicron-rpi` / `<your_password>`
   - **Configure Wireless LAN:** Enter your Wi-Fi details (needed for setup, can be disabled later).
   - **Enable SSH:** Check this box (Use password authentication).
6. Click **Save** and **Write**.

---

## Phase 2: Partitioning the SD Card (Native Pi Method)
To protect the operating system from power-cut corruption, we are locking the OS to Read-Only mode. Therefore, we must create a dedicated Read-Write partition on the SD card for your database. Because Windows struggles to resize modern Linux partitions, we will do this directly on the Pi.

1. After Pi Imager finishes flashing, open the **`bootfs`** drive in Windows Explorer.
2. Right-click the **`cmdline.txt`** file and open it with Notepad.
3. Scroll to the very end of the text. Delete the word **`resize`** (and the space after it). This prevents the Pi from auto-expanding on its first boot. Save the file.
4. Insert the SD card into the Raspberry Pi, power it on, and wait a minute for it to connect to Wi-Fi.
5. SSH into the Pi from your Windows PC: `ssh insitumicron-rpi@stgobain-hmi-lc.local` (or use the Pi's IP address)
6. We must expand the OS to 8GB and create the DATA partition using standard Linux tools. Run:
   ```bash
   sudo fdisk /dev/mmcblk0
   ```
7. Inside the `fdisk` prompt, type the following exact sequence (pressing Enter after each bold character):
   - **`d`** -> **`2`** (Deletes the OS partition)
   - **`n`** -> **`p`** -> **`2`** (Creates the new OS partition)
   - Type **`1064960`** (or whatever your original starting sector was)
   - Type **`+8G`**
   - Type **`N`** (Do NOT remove the ext4 signature)
   - Type **`w`** (Saves and exits)
8. Run these four commands to let `parted` automatically create the DATA partition and format the drives:
   ```bash
   sudo partprobe
   sudo parted /dev/mmcblk0 mkpart primary ext4 8GB 100%
   sudo resize2fs /dev/mmcblk0p2
   sudo mkfs.ext4 /dev/mmcblk0p3
   ```
9. You now have an 8GB OS partition and a massive DATA partition taking up the rest of the SD card!

---

## Phase 3: Transferring Files & Initial Setup
1. Insert the MicroSD card into the Raspberry Pi 5, connect the Waveshare display, and power it on.
2. Wait a minute for the Pi to boot and connect to your Wi-Fi.
3. On your Windows PC, open Command Prompt or PowerShell and transfer your files using SCP (or use a tool like WinSCP/FileZilla):
   ```bash
   scp -r "C:\Users\rohit\work\GUI files\Pi_HMI" insitumicron-rpi@stgobain-hmi-lc.local:/home/insitumicron-rpi/
   ```
4. SSH into the Pi to begin setup:
   ```bash
   ssh insitumicron-rpi@stgobain-hmi-lc.local
   ```

---

## Phase 4: Prepare the Data Mount
Once logged into the Pi via SSH, we need to create the mount point for the 50GB partition. We will not use `fstab` to mount it, as systemd's boot timings conflict violently with the OverlayFS shield. Instead, we just prepare the folder now and mount it right before the GUI starts.

1. Create the mount folder:
   ```bash
   sudo mkdir -p /mnt/data
   ```
   *(Note: Do not take ownership of this folder yet; you must take ownership AFTER it is successfully mounted in the later steps).*

---

## Phase 5: Setting up the Custom Boot Logo
We will create a custom Plymouth theme for your company logo so it displays during boot.
1. Copy your logo into the GUI folder on Windows and SCP it over, or download it directly to the Pi. Let's assume it's at `/home/insitumicron-rpi/Pi_HMI/logo.png`.
2. Run these commands on the Pi to create a custom splash theme:
   ```bash
   sudo mkdir -p /usr/share/plymouth/themes/stgobain
   sudo cp /home/insitumicron-rpi/Pi_HMI/logo.png /usr/share/plymouth/themes/stgobain/splash.png
   ```
3. Create the theme configuration file:
   ```bash
   sudo nano /usr/share/plymouth/themes/stgobain/stgobain.plymouth
   ```
4. Paste the following:
   ```ini
   [Plymouth Theme]
   Name=StGobain
   Description=Custom Boot Logo
   ModuleName=script

   [script]
   ImageDir=/usr/share/plymouth/themes/stgobain
   ScriptFile=/usr/share/plymouth/themes/stgobain/stgobain.script
   ```
5. Create the script file to center the image:
   ```bash
   sudo nano /usr/share/plymouth/themes/stgobain/stgobain.script
   ```
6. Paste the following:
   ```javascript
   splash_image = Image("splash.png");
   screen_width = Window.GetWidth();
   screen_height = Window.GetHeight();
   placed_image = sprite(splash_image);
   placed_image.SetX(screen_width/2 - splash_image.GetWidth()/2);
   placed_image.SetY(screen_height/2 - splash_image.GetHeight()/2);
   ```
7. Finally, tell `install_kiosk.sh` to use this theme. Edit `install_kiosk.sh`:
   ```bash
   nano /home/pi/Pi_HMI/deploy/install_kiosk.sh
   ```
   *Change `plymouth-set-default-theme -R bgrt` to `plymouth-set-default-theme -R stgobain`.*

---

## Phase 6: The Battle-Tested Kiosk Method (Auto-login)
Fighting Linux systemd background services for DRM/KMS permissions on Raspberry Pi 5 (Bookworm/Wayland) is fragile. Instead, we use the robust "Console Auto-login" method.

1. Configure the Pi to automatically log into the console on boot:
   ```bash
   sudo raspi-config nonint do_boot_behaviour B2
   ```
2. Tell the Pi to launch the GUI immediately after this auto-login. Edit your profile:
   ```bash
   nano ~/.profile
   ```
   Add the following at the bottom. **Crucially, we manually mount the 50GB partition here, right before the GUI launches, to completely bypass systemd/fstab bugs:**
   ```bash
   # Start Kiosk on TTY1
   if [ "$(tty)" = "/dev/tty1" ]; then
       sudo mount /dev/mmcblk0p3 /mnt/data
       export QT_QPA_PLATFORM=wayland
       export KIOSK_MODE=1
       exec cage -s -- /home/insitumicron-rpi/Pi_HMI/venv/bin/python /home/insitumicron-rpi/Pi_HMI/main.py
   fi
   ```
   *Note: Using `exec` means if the Python app crashes, the user logs out and instantly logs back in, providing infinite auto-restart.*

3. **CRITICAL: Take Ownership of the Drive**
   Before you lock the machine, you must trigger the mount once manually so you can give the Python app permission to write to it:
   ```bash
   sudo mount /dev/mmcblk0p3 /mnt/data
   sudo chown -R insitumicron-rpi:insitumicron-rpi /mnt/data
   ```

3. Make sure the boot screen points to TTY1 so it takes over naturally. Edit `cmdline.txt`:
   ```bash
   sudo nano /boot/firmware/cmdline.txt
   ```
   Ensure it contains `console=tty1` (and NOT `console=tty3`).

4. Enable the Read-Only shield and reboot:
   ```bash
   sudo raspi-config nonint enable_overlayfs
   sudo raspi-config nonint enable_bootro
   sudo reboot
   ```

---

## Troubleshooting & Obstacles Overcome

During the development and deployment of this kiosk, we encountered and solved several complex obstacles specific to the Raspberry Pi 5 and Wayland architecture.

### 1. The "Ghost GUI" (Systemd vs. DRM Permissions)
- **Problem:** When trying to launch `cage` via a systemd background service (`kiosk.service`), the service would report `active (running)`, but the physical monitor remained stuck on the text console (`tty3`).
- **Cause:** Linux strictly limits which processes can seize control of the physical screen (DRM/KMS). Background services lack an active "seat" session.
- **Solution:** Switched to the "Auto-login" method. By having the Pi automatically log the user in on `tty1` and launching `cage` via `~/.profile`, the session natively acquires 100% of the DRM/KMS permissions and flawlessly displays the GUI.

### 2. HDMI Port 1 Strict Priority
- **Problem:** The Pi 5 booted to the text console, but when the GUI launched, the screen went black or stayed on the console.
- **Cause:** The Raspberry Pi 5 has two microHDMI ports. Hardware acceleration and Wayland compositors (like Cage) strictly prioritize HDMI-1 (the port closest to the USB-C power port). If the display is plugged into HDMI-2, the GUI fails to route the video output correctly.
- **Solution:** Always physically plug the HMI display into the **HDMI-1** port.

### 3. The FAT32 "Dirty Bit" Lock (Read-Only Boot Partition)
- **Problem:** Commands to update `/boot/firmware/cmdline.txt` silently failed. When manually mounted, it threw a `WARNING: source write-protected, mounted read-only` error.
- **Cause:** If the Pi loses power abruptly, the Linux FAT driver detects a "Dirty Bit" on the boot partition and forcefully locks it as read-only to prevent further corruption.
- **Solution:** Clear the dirty bit by unmounting the partition and running a disk repair:
  ```bash
  sudo umount /boot/firmware
  sudo fsck.fat -a /dev/mmcblk0p1
  sudo mount -o rw /dev/mmcblk0p1 /boot/firmware
  ```

### 4. Plymouth Hijacking the Screen & RPi 5 GPU Delays
- **Problem:** The custom St. Gobain boot logo wouldn't show, and Plymouth would forcefully redirect the terminal to `tty3`, causing the GUI on `tty1` to remain hidden.
- **Cause:** On the Raspberry Pi 5, the graphics driver (`vc4-kms-v3d`) takes longer to load than on older Pis. Plymouth would start, fail to find the display, give up, and leave the terminal state messy.
- **Solution:** In `/etc/plymouth/plymouthd.conf`, we added `DeviceTimeout=8` to force Plymouth to wait for the GPU driver. We also ensured `console=tty1 quiet splash` was set in `cmdline.txt` so everything happens linearly on the primary screen.

### 6. USB Transfer & Phantom Drives
- **Problem:** When attempting to mount a USB drive to transfer files manually on the Pi, mounting `/dev/sda1` failed.
- **Cause:** `sda` was a 40KB phantom drive (built-in card reader). The actual 7.5GB USB drive was `/dev/sdb1`.
- **Solution:** Always run `lsblk` and check the size of the drive before mounting. Furthermore, ensure you do not copy `.venv` or `.idea` folders from the Windows machine, as they contain incompatible binaries or bloat.

### 7. Missing Python Virtual Environment (PEP 668)
- **Problem:** Attempting to `pip install -r requirements.txt` globally on Bookworm fails due to PEP 668 ("externally-managed-environment").
- **Solution:** A dedicated Python virtual environment is mandatory. We had to create it explicitly (`python -m venv venv`) inside the `Pi_HMI` folder, and update all service scripts to call `/venv/bin/python` instead of global `python`.

### 8. Orphaned SQLite Database Location
- **Problem:** The `test_data.db` file was accidentally transferred along with the Python code to the Read-Only OS partition (`/home/insitumicron-rpi/Pi_HMI/`).
- **Cause:** If left there, SQLite throws read-only database errors when Kiosk mode is activated.
- **Solution:** Manually moved the database to the 3rd partition (`mv test_data.db* /mnt/data/`) and ensured `data_logger.py` contains auto-routing logic to detect if `/mnt/data` exists and use it dynamically.

### 9. OverlayFS Blocking `fstab` Updates
- **Problem:** When trying to update `/etc/fstab` to auto-mount the DATA partition, the command failed or `raspi-config` threw "overlay in use, cannot update fstab".
- **Cause:** The root filesystem is actively shielded by OverlayFS.
- **Solution:** Bypassed the overlay entirely by mounting the underlying raw physical partition to a temporary folder:
  ```bash
  sudo mount /dev/mmcblk0p2 /mnt/realroot
  sudo nano /mnt/realroot/etc/fstab
  ```

### 10. The Plymouth Serial Console Trap
- **Problem:** Even with the GPU timeout fixed, Plymouth refused to render the custom logo and fell back to text mode.
- **Cause:** `console=serial0,115200` in the `cmdline.txt` string tricks Plymouth into assuming the machine is a headless server, violently disabling all graphics. 
- **Solution:** Bypass this trap by injecting `plymouth.ignore-serial-consoles` into the kernel boot parameters (`cmdline.txt`).

### 11. The initramfs Pi 5 Saving Miracle
- **Problem:** While generating the bootloader (`update-initramfs`), the FAT32 driver crashed mid-save, throwing a "Read-only file system" error.
- **Cause:** Linux builds two bootloader files sequentially: `initramfs_2712` (for Pi 5) and `initramfs8` (for older Pis). The error occurred while saving the older Pi 4 file. 
- **Solution:** The Pi 5 file containing the crucial 8-second GPU delay successfully sneaked onto the drive milliseconds before the lock slammed down, perfectly resolving the boot splash issue on the Pi 5.

### 12. The Root Permissions Trap (Permission Denied)
- **Problem:** When the raw UDEV rule automatically mounted the USB drive, the GUI was denied write access when attempting to export CSV files.
- **Cause:** Linux defaults to assigning ownership of low-level mounts to `root`. Because the Python GUI runs safely as a normal user (`insitumicron-rpi`), it was locked out.
- **Solution:** We added `-o uid=1000,gid=1000,dmask=000,fmask=000,flush` to the UDEV rule, forcing Linux to surrender ownership of the physical USB to the GUI user upon insertion.

### 13. The "Ghost Drive" Trap (No USB Detected)
- **Problem:** The systemd-mount command utilized `autofs`. Python's `psutil` library failed to detect the USB drive entirely.
- **Cause:** `autofs` places an invisible "ghost" folder at `/media/usb` that only turns into a real drive at the exact millisecond a program tries to open it. Because it was a ghost drive, `psutil` (when run with `all=False`) assumed it was a fake system drive and aggressively deleted it from the search list.
- **Solution:** We edited `usb_utils.py` and changed `all=False` to `all=True`, forcing Python to acknowledge ghost drives and trigger the autofs mount.

### 14. The Shadow Shield Trap (Read-Only File System)
- **Problem:** The USB export crashed with a confusing "Read-only file system" error pointing to `/media/root-ro/mnt/data`.
- **Cause:** Because Python couldn't see the real USB drive (due to the ghost trap), the export logic desperately searched the system for *any* large drive to export to. It eventually stumbled upon `/media/root-ro/mnt/data`—which is the internal backup shadow of the database created by the OverlayFS shield. Because it's a shield, it is read-only.
- **Solution:** We explicitly banned the string `root-ro` from the valid mount points list in `usb_utils.py` so the GUI ignores the shadow shield.

### 15. Red Diagnostic Boot Screen (NVMe Error)
- **Problem:** When booting the Pi 5, a bright red diagnostic screen flashes displaying `M.2 PCIe HAT not detected`.
- **Cause:** The Pi 5 bootloader (EEPROM) defaults to searching for an NVMe SSD (`0xf416`). When it fails to find one, it throws a diagnostic warning before falling back to the SD card.
- **Solution:** Edit the EEPROM configuration (`sudo rpi-eeprom-config --edit`) and change the `BOOT_ORDER` to `BOOT_ORDER=0xf41` (which entirely skips the NVMe check).

### 16. EEPROM Updates Reverting (The Dirty Bit Trap)
- **Problem:** Custom `rpi-eeprom-config` changes (like `BOOT_ORDER`) appear to succeed but disappear after a cold reboot.
- **Cause:** If the Pi experiences an unsafe shutdown (e.g. pulling the power plug to test cold boots), Linux flags the FAT32 boot partition with a "Dirty Bit" and forcefully mounts it as Read-Only. `rpi-eeprom-config` silently fails to write the staging file (`pieeprom.upd`) to the locked partition, meaning the chip never actually flashes.
- **Solution:** Unmount and repair the drive manually before editing the EEPROM:
  ```bash
  sudo umount /boot/firmware
  sudo fsck.fat -a /dev/mmcblk0p1
  sudo mount -o rw /dev/mmcblk0p1 /boot/firmware
  sudo rpi-eeprom-config --edit
  ```
  *(Note: You must also ensure that `raspi-config` has explicitly disabled the Boot Partition Write-Protect before doing this).*

### 17. Dropped Wi-Fi on Mobile Hotspots
- **Problem:** Upon reboot, the Pi fails to reconnect to a mobile phone hotspot, cutting off RPI Connect access.
- **Cause:** Most modern phones disable their hotspot broadcast if no devices are actively connected for a short period (such as during the Pi's reboot cycle).
- **Solution:** Toggle the phone's hotspot OFF and ON. Keep the phone screen awake on the hotspot settings page, then reboot the Pi by cycling the power so it can grab the broadcast.
