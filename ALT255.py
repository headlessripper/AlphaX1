import subprocess
import pyperclip
import os
import json
from PyQt6 import QtWidgets, QtGui
from PyQt6.QtGui import QIcon

def run_command(command):
    """Run a command in the shell and return the output."""
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout.strip()

def get_system_info():
    system_info = {
        "Hostname": run_command(["hostname"]),
        "OS": run_command(["wmic", "os", "get", "caption"]),
        "Architecture": run_command(["wmic", "os", "get", "OSArchitecture"]),
    }
    safe_info = {}
    for key, value in system_info.items():
        lines = value.splitlines()
        if len(lines) > 1:
            safe_info[key] = lines[1].strip()
        else:
            safe_info[key] = "Unavailable"
    return safe_info

def get_running_processes():
    process_output = run_command(["tasklist"])
    processes = []
    for line in process_output.splitlines()[3:]:
        parts = line.split()
        if len(parts) > 0:
            processes.append({"Image Name": parts[0], "PID": parts[1], "Session Name": parts[2]})
    return processes

def get_installed_software():
    software_output = run_command(["wmic", "product", "get", "name"])
    return [line.strip() for line in software_output.splitlines()[1:] if line.strip()]

def get_open_ports():
    netstat_output = run_command(["netstat", "-ano"])
    ports = []
    for line in netstat_output.splitlines()[4:]:
        parts = line.split()
        if len(parts) >= 5:
            ports.append({"Protocol": parts[0], "Local Address": parts[1], "PID": parts[4]})
    return ports

def get_wifi_credentials():
    ssid_output = run_command(["netsh", "wlan", "show", "interfaces"])
    ssid = extract_value(ssid_output, "SSID")

    if ssid:
        password_output = run_command(["netsh", "wlan", "show", "profiles", ssid, "key=clear"])
        password = extract_value(password_output, "Key Content")
        return ssid, password
    return None, None

def extract_value(output, key):
    for line in output.splitlines():
        if key in line:
            parts = line.split(":")
            if len(parts) > 1:
                return parts[1].strip()
    return ""

def get_connected_devices():
    arp_output = run_command(["arp", "-a"])
    devices = []
    for line in arp_output.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2:
            devices.append({"IP Address": parts[1], "MAC Address": parts[0]})
    return devices

def get_firewall_status():
    status = run_command(["netsh", "advfirewall", "show", "allprofiles"])
    firewall_status = {}
    for line in status.splitlines():
        if "State" in line:
            parts = line.split(":")
            if len(parts) > 1:
                firewall_status["Firewall State"] = parts[1].strip()
            else:
                firewall_status["Firewall State"] = "Unknown"
    return firewall_status

def write_to_file(data):
    file_path = os.path.join(os.getcwd(), "network_analysis.json")
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)
    return file_path

class NetworkAnalyzerApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Network Analyzer")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon('background/icon.png'))

        layout = QtWidgets.QVBoxLayout()

        self.text_area = QtWidgets.QTextEdit(self)
        self.text_area.setReadOnly(True)
        layout.addWidget(self.text_area)

        self.analyze_button = QtWidgets.QPushButton("Analyze Network", self)
        self.analyze_button.clicked.connect(self.analyze_network)
        layout.addWidget(self.analyze_button)

        self.setLayout(layout)

    def analyze_network(self):
        data = {}
        data["System Info"] = get_system_info()
        data["Running Processes"] = get_running_processes()
        data["Installed Software"] = get_installed_software()
        data["Open Ports"] = get_open_ports()

        ssid, password = get_wifi_credentials()
        if ssid and password:
            data["Wi-Fi SSID"] = ssid
            data["Wi-Fi Password"] = password

        devices = get_connected_devices()
        data["Connected Devices"] = devices

        firewall_status = get_firewall_status()
        data["Firewall Status"] = firewall_status

        file_path = write_to_file(data)
        self.text_area.setPlainText(json.dumps(data, indent=4))
        
        if password:
            pyperclip.copy(password)
            self.text_area.append("\nWi-Fi password copied to clipboard.")

def main():
    app = QtWidgets.QApplication([])
    window = NetworkAnalyzerApp()
    window.show()
    app.exec()

if __name__ == "__main__":
    main()
