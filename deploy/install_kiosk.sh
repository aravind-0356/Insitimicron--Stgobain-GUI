#!/bin/bash
# install_kiosk.sh - Raspberry Pi 5 Industrial Kiosk Setup Script (Pi_HMI_mtr)
# Must be run as root (sudo ./install_kiosk.sh)

set -e

echo "Starting Industrial Kiosk Installation for Pi_HMI_mtr..."

if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root: sudo ./install_kiosk.sh"
  exit 1
fi

PROJECT_DIR="/home/insitumicron-rpi/Pi_HMI_mtr"
USER_NAME="insitumicron-rpi"

# 1. Update and install dependencies
echo "Installing dependencies..."
apt-get update
apt-get install -y cage wayland-protocols plymouth plymouth-themes sqlite3 parted libgl1 libegl1 libfontconfig1 libdbus-1-3

# 2. Configure Plymouth (Boot Splash Screen)
echo "Configuring boot splash screen..."
# Ensure cmdline points to tty1, hides boot logs, and ignores serial console trap
if grep -q "console=tty1" /boot/firmware/cmdline.txt; then
    sed -i 's/console=tty1/console=tty1 quiet splash loglevel=0 logo.nologo vt.global_cursor_default=0 plymouth.ignore-serial-consoles/' /boot/firmware/cmdline.txt
fi

# Create the St. Gobain theme
mkdir -p /usr/share/plymouth/themes/stgobain
if [ -f "$PROJECT_DIR/final_boot_logo_1280x800.png" ]; then
    cp "$PROJECT_DIR/final_boot_logo_1280x800.png" /usr/share/plymouth/themes/stgobain/splash.png
elif [ -f "$PROJECT_DIR/logo.png" ]; then
    cp "$PROJECT_DIR/logo.png" /usr/share/plymouth/themes/stgobain/splash.png
else
    echo "Warning: Logo file not found in $PROJECT_DIR, checking for any png..."
    cp "$PROJECT_DIR"/*.png /usr/share/plymouth/themes/stgobain/splash.png 2>/dev/null || echo "No logo found!"
fi

cat > /usr/share/plymouth/themes/stgobain/stgobain.plymouth << EOF
[Plymouth Theme]
Name=StGobain
Description=Custom Boot Logo
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/stgobain
ScriptFile=/usr/share/plymouth/themes/stgobain/stgobain.script
EOF

cat > /usr/share/plymouth/themes/stgobain/stgobain.script << EOF
splash_image = Image("splash.png");
screen_width = Window.GetWidth();
screen_height = Window.GetHeight();
placed_image = Sprite(splash_image);
placed_image.SetX(screen_width/2 - splash_image.GetWidth()/2);
placed_image.SetY(screen_height/2 - splash_image.GetHeight()/2);
EOF

# Force Plymouth to wait for the GPU on RPi 5 (DeviceTimeout=8)
cat > /etc/plymouth/plymouthd.conf << EOF
[Daemon]
Theme=stgobain
DeviceTimeout=8
EOF

plymouth-set-default-theme -R stgobain

# 3. Setup Persistent Data Directory
echo "Setting up /mnt/data..."
mkdir -p /mnt/data
chown -R $USER_NAME:$USER_NAME /mnt/data

# 4. Install Auto-Login Kiosk on TTY1
echo "Installing Kiosk Auto-Login on TTY1..."
raspi-config nonint do_boot_behaviour B2

mkdir -p /etc/systemd/system/getty@tty1.service.d/
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $USER_NAME --noclear %I \$TERM
EOF

# Update user's .profile to mount data partition and launch cage
if ! grep -q "Start Kiosk on TTY1" /home/$USER_NAME/.profile; then
cat << "EOF" >> /home/$USER_NAME/.profile

# Start Kiosk on TTY1
if [ "$(tty)" = "/dev/tty1" ]; then
    sudo mount /dev/mmcblk0p3 /mnt/data 2>/dev/null || true
    export QT_QPA_PLATFORM=wayland
    export KIOSK_MODE=1
    exec cage -s -- /home/insitumicron-rpi/Pi_HMI_mtr/venv/bin/python /home/insitumicron-rpi/Pi_HMI_mtr/main.py
fi
EOF
    chown $USER_NAME:$USER_NAME /home/$USER_NAME/.profile
fi

# Ensure user can mount /dev/mmcblk0p3 without password prompt in .profile
if [ ! -f /etc/sudoers.d/010_kiosk-mount ]; then
    echo "$USER_NAME ALL=(ALL) NOPASSWD: /bin/mount /dev/mmcblk0p3 /mnt/data, /bin/umount /mnt/data" > /etc/sudoers.d/010_kiosk-mount
    chmod 0440 /etc/sudoers.d/010_kiosk-mount
fi

# 5. Install udev rules for USB automounting
echo "Installing USB automount rules..."
mkdir -p /media/usb
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/99-usb-mount.rules" ]; then
    cp "$SCRIPT_DIR/99-usb-mount.rules" /etc/udev/rules.d/
    udevadm control --reload-rules
    udevadm trigger
fi

# 6. Enable OverlayFS (Read-Only Root)
echo "Enabling OverlayFS..."
raspi-config nonint enable_overlayfs
raspi-config nonint enable_bootro

echo "Industrial Kiosk Installation Complete!"
echo "Rebooting will now start the system in Kiosk mode."
