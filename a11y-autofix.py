#!/usr/bin/env python3
"""
PC Auto-Fix Script for Android TV Accessibility Services
=========================================================
Runs on your Windows PC. Checks the TV over ADB every 5 minutes.
If an app update knocked out accessibility services, re-enables them automatically.

No taps, no Siri, no manual commands. Just leave it running.

Setup:
  1. Install Python 3 from python.org (check "Add to PATH")
  2. Install ADB (Android Platform Tools) and add to PATH
  3. Connect TV via USB or: adb connect <TV-IP>:5555
  4. Run: python a11y-autofix.py
     Or double-click to run in background.

To run on startup (Windows):
  - Press Win+R, type shell:startup, Enter
  - Create a shortcut to this script there
"""

import subprocess
import time
import sys
from datetime import datetime

# Verified service component names (do NOT guess)
SERVICES = [
    ("com.sagi.appleremotebridge",
     "com.sagi.appleremotebridge/com.sagi.appleremotebridge.RemoteAccessibilityService",
     "Apple Remote Bridge"),
    ("com.spocky.projengmenu",
     "com.spocky.projengmenu/com.spocky.projengmenu.services.ProjectivyAccessibilityService",
     "Projectivy Launcher"),
    ("flar2.homebutton",
     "flar2.homebutton/flar2.homebutton.a.ai",
     "Button Mapper"),
    ("com.fluxii.androidtv.mousetoggle",
     "com.fluxii.androidtv.mousetoggle/com.fluxii.androidtv.mousetoggle.AccessService",
     "Mouse Toggle"),
]

CHECK_INTERVAL = 300  # 5 minutes


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def adb(*args, timeout=15):
    """Run an adb command, return stdout stripped. None on failure."""
    try:
        r = subprocess.run(
            ["adb"] + list(args),
            capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return None
        return r.stdout.strip()
    except Exception:
        return None


def device_connected():
    out = adb("devices")
    if not out:
        return False
    for line in out.splitlines()[1:]:
        if line.strip().endswith("device"):
            return True
    return False


def get_enabled_services():
    out = adb("shell", "settings", "get", "secure",
              "enabled_accessibility_services")
    if not out or out == "null":
        return ""
    return out


def is_installed(pkg):
    out = adb("shell", "pm", "list", "packages", pkg)
    return out is not None and f"package:{pkg}" in out


def ensure_service(pkg, svc, label):
    """Ensure a service is enabled. Returns True if a fix was applied."""
    if not is_installed(pkg):
        return False
    cur = get_enabled_services()
    if f":{svc}:" in f":{cur}:":
        return False  # already enabled
    # Append (preserve existing)
    if not cur:
        new_val = svc
    else:
        new_val = f"{cur}:{svc}"
    adb("shell", "settings", "put", "secure",
        "enabled_accessibility_services", new_val)
    adb("shell", "appops", "set", pkg,
        "ACCESS_RESTRICTED_SETTINGS", "allow")
    log(f"FIXED: Re-enabled {label} ({svc})")
    return True


def main():
    log("Accessibility auto-fix started. Checking every "
        f"{CHECK_INTERVAL // 60} minutes. Press Ctrl+C to stop.")
    while True:
        try:
            if not device_connected():
                log("No ADB device connected. Waiting...")
            else:
                fixed_any = False
                for pkg, svc, label in SERVICES:
                    try:
                        if ensure_service(pkg, svc, label):
                            fixed_any = True
                    except Exception as e:
                        log(f"Error checking {label}: {e}")
                # Make sure the master toggle is on
                adb("shell", "settings", "put", "secure",
                    "accessibility_enabled", "1")
                if fixed_any:
                    log("All missing services restored.")
        except Exception as e:
            log(f"Loop error: {e}")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Stopped by user.")
        sys.exit(0)
