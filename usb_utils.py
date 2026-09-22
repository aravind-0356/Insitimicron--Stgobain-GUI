import os
import platform

def detect_usb_drive():
    """
    Attempts to auto-detect a connected USB storage device (pendrive).
    Returns the mount path as a string if found, or None if no USB drive is detected.
    Requires 'psutil' to be installed.
    """
    try:
        import psutil
    except ImportError:
        print("Warning: 'psutil' module not found. USB auto-detection is disabled.")
        return None

    partitions = psutil.disk_partitions(all=False)
    system = platform.system()

    largest_mount = None
    max_size = 0

    for p in partitions:
        try:
            # STM32 Nucleo boards expose a tiny filesystem (~1-2 MB).
            # Pendrives are > 1GB. Filter out drives < 50MB.
            usage = psutil.disk_usage(p.mountpoint)
            if usage.total < 50 * 1024 * 1024:
                continue
        except Exception:
            # If we can't read usage, it might be unready or permission denied
            continue

        mount_name = os.path.basename(p.mountpoint.rstrip('/\\')).upper()
        if 'NOD_' in mount_name or 'NUCLEO' in mount_name:
            continue

        valid = False
        if system == 'Windows':
            # On Windows, psutil returns 'removable' in options for USB drives
            if 'removable' in p.opts:
                valid = True
        elif system == 'Linux':
            # Ignore OverlayFS and internal data mounts!
            if 'root-ro' in p.mountpoint or 'root-rw' in p.mountpoint or 'realroot' in p.mountpoint or p.mountpoint == '/mnt/data':
                continue
                
            # On Raspberry Pi (Raspbian), USBs are auto-mounted under /media/
            if p.mountpoint.startswith('/media/') or p.mountpoint.startswith('/mnt/'):
                # Ignore loop devices or snap mounts
                if not p.device.startswith('/dev/loop'):
                    valid = True
        if valid:
            if usage.total > max_size:
                max_size = usage.total
                largest_mount = p.mountpoint

    return largest_mount
