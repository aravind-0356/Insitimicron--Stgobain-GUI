#!/bin/bash
# install_kiosk.sh - Raspberry Pi 5 Industrial Kiosk Setup Script
# Must be run as root (sudo ./install_kiosk.sh)

set -e

echo "Starting Industrial Kiosk Installation..."

if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root"
  exit
fi

# 1. Update and install dependencies
echo "Installing dependencies..."
apt-get update
apt-get install -y cage wayland-protocols plymouth plymouth-themes sqlite3

# 2. Configure Plymouth (Boot Splash Screen)
echo "Configuring boot splash screen..."
# Ensure cmdline points to tty1 and hides boot logs
sed -i 's/console=tty1/console=tty1 quiet splash loglevel=0 logo.nologo vt.global_cursor_default=0/' /boot/firmware/cmdline.txt

# Create the St. Gobain theme
mkdir -p /usr/share/plymouth/themes/stgobain
cp /home/insitumicron-rpi/Pi_HMI/logo.png /usr/share/plymouth/themes/stgobain/splash.png 2>/dev/null || echo "Logo not found, using placeholder"

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

# Force Plymouth to wait for the GPU on RPi 5
cat > /etc/plymouth/plymouthd.conf << EOF
[Daemon]
Theme=stgobain
DeviceTimeout=8
EOF

plymouth-set-default-theme -R stgobain

# 3. Setup Persistent Data Directory
echo "Setting up /mnt/data..."
mkdir -p /mnt/data
chown -R insitumicron-rpi:insitumicron-rpi /mnt/data

# 4. Install Auto-Login Kiosk (Replaces old kiosk.service)
echo "Installing Kiosk Auto-Login..."
raspi-config nonint do_boot_behaviour B2

mkdir -p /etc/systemd/system/getty@tty1.service.d/
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin insitumicron-rpi --noclear %I \$TERM
EOF

cat << "EOF" >> /home/insitumicron-rpi/.profile

# Start Kiosk on TTY1
if [ "$(tty)" = "/dev/tty1" ]; then
    export QT_QPA_PLATFORM=wayland
    export KIOSK_MODE=1
    exec cage -s -- /home/insitumicron-rpi/Pi_HMI/venv/bin/python /home/insitumicron-rpi/Pi_HMI/main.py
fi
EOF

# 5. Install udev rules for USB automounting
echo "Installing USB automount rules..."
mkdir -p /media/usb
cp 99-usb-mount.rules /etc/udev/rules.d/
udevadm control --reload-rules
udevadm trigger

# 6. Setup Persistent Journal (so logs survive across reboots in OverlayFS)
echo "Configuring persistent journal..."
mkdir -p /mnt/data/journal
rm -rf /var/log/journal
ln -s /mnt/data/journal /var/log/journal
systemctl restart systemd-journald

# 7. Enable OverlayFS (Read-Only Root)
echo "Enabling OverlayFS..."
# This locks the root filesystem to prevent corruption. 
raspi-config nonint enable_overlayfs
raspi-config nonint enable_bootro

echo "Installation complete!"
echo "IMPORTANT: Ensure you have created a 3rd partition on your SD card and added it to /etc/fstab to mount at /mnt/data BEFORE rebooting."
echo "Once ready, reboot the system to enter Kiosk mode."
