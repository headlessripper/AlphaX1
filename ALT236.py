import os
import sys
import ctypes
import subprocess
import logging

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    script_path = os.path.abspath(sys.argv[0])
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script_path}"', None, 1)
        sys.exit(0)
    except Exception as e:
        logging.error(f"Failed to elevate privileges: {e}")
        sys.exit(1)

def ensure_admin_privileges():
    if not is_admin():
        logging.warning("Script not running with administrative privileges. Attempting to relaunch.")
        run_as_admin()
    else:
        logging.info("Script is running with administrative privileges.")

def disable_network():
    try:
        # Disable Wi-Fi
        subprocess.run(["netsh", "interface", "set", "interface", "name=\"Wi-Fi\"", "admin=disabled"], check=True)
        # Disable Ethernet
        subprocess.run(["netsh", "interface", "set", "interface", "name=\"Ethernet\"", "admin=disabled"], check=True)
        print("All network connections have been disabled.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ensure_admin_privileges()
    disable_network()
