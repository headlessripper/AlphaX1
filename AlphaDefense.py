import sys
import numpy as np
import tensorflow as tf
from scapy.all import sniff, IP, TCP
import logging
import requests
from datetime import datetime, timedelta
from sklearn.cluster import KMeans, DBSCAN
import smtplib
from email.mime.text import MIMEText
import subprocess
import os
import ctypes
import threading
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QWidget, QHBoxLayout, QLabel, QLineEdit
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QIcon

# API key for IP geolocation
GEOLOCATION_API_KEY = '740aba678070535476f4ee637aeaa6e8'

# Set up logging
logging.basicConfig(filename='advanced_cyber_defender.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global variables to hold models and state
model = None
signatures = None
kmeans_model = None
dbscan_model = None
last_alert_time = datetime.min
alert_email = ''
notification_email = ''

# Define Threat Severities
THREAT_SEVERITY = {
    "General Threat": "medium",
    "Hacking Attempt": "high",
    "Malware Injection": "high",
    "Exploitation Attempt": "high",
    "Signature Match": "medium",
    "Behavioral Anomaly": "high"
}

# Thread class to handle network monitoring
class MonitoringThread(QThread):
    log_signal = pyqtSignal(str)

    def run(self):
        global model, signatures, kmeans_model, dbscan_model
        ensure_admin_privileges()
        logging.info("Starting network monitoring...")
        self.log_signal.emit("Network monitoring started.")
        sniff(prn=lambda packet: handle_packet(packet, model, signatures, kmeans_model, dbscan_model), store=0)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Alpha Cyber Defender")
        self.setGeometry(100, 100, 450, 400)
        self.setStyleSheet("background-color: #2e2e2e; color: #ffffff; font-family: Arial, sans-serif;")
        
        # Set the window icon
        self.setWindowIcon(QIcon('background/icon.png'))

        # Create widgets
        self.start_button = QPushButton("Start Monitoring")
        self.start_button.setIcon(QIcon('background/on.png'))
        self.start_button.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 5px; padding: 10px;")

        self.stop_button = QPushButton("Stop Monitoring")
        self.stop_button.setIcon(QIcon('background/close_icon.png'))
        self.stop_button.setStyleSheet("background-color: #f44336; color: white; border-radius: 5px; padding: 10px;")

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background-color: #333333; color: #ffffff; border: 1px solid #555555; border-radius: 5px;")

        self.alert_email_input = QLineEdit()
        self.alert_email_input.setPlaceholderText("Enter alert email address")
        
        self.notification_email_input = QLineEdit()
        self.notification_email_input.setPlaceholderText("Enter notification email address")

        self.save_email_button = QPushButton("Save Email Addresses")
        self.save_email_button.setStyleSheet("background-color: #2196F3; color: white; border-radius: 5px; padding: 10px;")

        # Set up layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)

        email_layout = QVBoxLayout()
        email_layout.addWidget(QLabel("Email Configuration:"))
        email_layout.addWidget(self.alert_email_input)
        email_layout.addWidget(self.notification_email_input)
        email_layout.addWidget(self.save_email_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)
        main_layout.addLayout(email_layout)
        main_layout.addWidget(QLabel("Logs:"))
        main_layout.addWidget(self.log_text)
        
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Connect buttons
        self.start_button.clicked.connect(self.start_monitoring)
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.save_email_button.clicked.connect(self.save_email_addresses)

        # Initialize thread
        self.monitoring_thread = MonitoringThread()
        self.monitoring_thread.log_signal.connect(self.update_log)

        # Load email addresses from file
        self.load_email_addresses()

    def start_monitoring(self):
        global model, signatures, kmeans_model, dbscan_model
        # Initialize models and signatures
        model = build_model((4,))
        signatures = load_threat_signatures()
        kmeans_model = KMeans(n_clusters=3)
        dbscan_model = DBSCAN(eps=0.5, min_samples=5)
        
        # Example historical data for training
        historical_data = np.array([
            [100, 1, 80, 2],
            [200, 1, 80, 4],
            [300, 2, 90, 8],
            [400, 2, 90, 16],
        ], dtype=np.float32)
        
        kmeans_model.fit(historical_data)
        
        self.monitoring_thread.start()
        
        # Start the alert scheduler
        self.alert_scheduler_thread = threading.Thread(target=schedule_alerts, daemon=True)
        self.alert_scheduler_thread.start()

    def stop_monitoring(self):
        self.monitoring_thread.terminate()
        self.update_log("Monitoring stopped.")

    def update_log(self, message):
        self.log_text.append(message)

    def save_email_addresses(self):
        global alert_email, notification_email
        alert_email = self.alert_email_input.text()
        notification_email = self.notification_email_input.text()

        with open('email_addresses.txt', 'w') as f:
            f.write(f"{alert_email}\n{notification_email}")
        
        self.update_log("Email addresses saved.")

    def load_email_addresses(self):
        global alert_email, notification_email
        if os.path.exists('email_addresses.txt'):
            with open('email_addresses.txt', 'r') as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    alert_email = lines[0].strip()
                    notification_email = lines[1].strip()
                    self.alert_email_input.setText(alert_email)
                    self.notification_email_input.setText(notification_email)

def build_model(input_shape):
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(128, activation='relu', input_shape=input_shape),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model

def load_threat_signatures():
    try:
        response = requests.get("https://threat-intel-feed.example.com/signatures")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error loading threat signatures: {e}")
        return ["default_signature_1", "default_signature_2"]

def preprocess_data(packet):
    flags = int(packet[TCP].flags)
    features = np.array([packet[IP].len, packet[TCP].sport, packet[TCP].dport, flags], dtype=np.float32)
    return features.reshape(1, -1)

def check_signatures(packet, signatures):
    packet_data = f"{packet[IP].src}:{packet[TCP].sport} -> {packet[IP].dst}:{packet[TCP].dport}"
    for signature in signatures:
        if signature in packet_data:
            return True
    return False

def detect_hacking(packet):
    malicious_ips = ['192.168.1.100', '10.0.0.50']  # Replace with actual malicious IPs
    if packet[IP].src in malicious_ips:
        return True

    if packet[TCP].dport in [21, 22, 23, 80, 443] and packet[TCP].flags == 'S':
        return True

    return False

def detect_malware_injection(packet):
    payload = bytes(packet[TCP].payload)
    if len(payload) > 1000 or b'malicious' in payload:  # Customize payload detection
        return True

    return False

def detect_exploitation_attempt(packet):
    payload = bytes(packet[TCP].payload)
    exploit_signatures = [b'exploit', b'vuln', b'payload']  # Replace with actual signatures
    if any(signature in payload for signature in exploit_signatures):
        return True

    return False

def detect_threat(features, model):
    prediction = model.predict(features)
    return prediction > 0.5

def behavioral_analysis(packet, kmeans_model, dbscan_model):
    features = preprocess_data(packet)
    features = features.astype(np.float32)
    try:
        kmeans_pred = kmeans_model.predict(features)
        dbscan_pred = dbscan_model.fit_predict(features)
    except Exception as e:
        logging.error(f"Error during behavioral analysis: {e}")
        return False
    if kmeans_pred[0] == -1 or dbscan_pred[0] == -1:
        return True
    return False

def get_geolocation(ip_address=None):
    BASE_URL = 'http://api.positionstack.com/v1/forward'
    try:
        params = {'api_key': GEOLOCATION_API_KEY}
        if ip_address:
            params['ip_address'] = ip_address
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        location_data = response.json()
        return {
            'country': location_data.get('country', 'Unknown'),
            'state': location_data.get('region', 'Unknown'),
            'city': location_data.get('city', 'Unknown'),
            'isp': location_data.get('connection', {}).get('isp_name', 'Unknown'),
            'ip': location_data.get('ip_address', 'Unknown')
        }
    except requests.RequestException as e:
        logging.error(f"Error fetching geolocation: {e}")
        return {}

def send_alert(packet, location):
    global last_alert_time, alert_email
    now = datetime.now()
    if now - last_alert_time >= timedelta(hours=1):
        last_alert_time = now
        msg = MIMEText(f"Threat detected from {packet[IP].src}. Location: {location}. Immediate attention required.")
        msg['Subject'] = 'Security Alert: Cyber Attack'
        msg['From'] = alert_email
        msg['To'] = alert_email
        try:
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(os.getenv('EMAIL_USER'), os.getenv('EMAIL_PASS'))
                server.sendmail(msg['From'], [msg['To']], msg.as_string())
            logging.info("Alert email sent.")
        except smtplib.SMTPAuthenticationError as e:
            logging.error(f"SMTP Authentication Error: {e}")
        except Exception as e:
            logging.error(f"Error sending email: {e}")

def schedule_alerts():
    while True:
        now = datetime.now()
        if now - last_alert_time >= timedelta(hours=1):
            # This would ideally be replaced by an actual alert condition
            logging.info("Hourly alert check.")
        threading.Event().wait(3600)  # Wait for 1 hour

def automated_response(packet, location, threat_type):
    threat_severity = THREAT_SEVERITY.get(threat_type, 'low')
    log_message = f"Critical {threat_type} detected from {packet[IP].src}. Location: {location}. Executing automated response."
    logging.warning(log_message)
    forward_to_local(log_message)
    block_ip(packet[IP].src)
    redirect_to_virtual_network(packet)
    perform_countermeasures(location)

    if threat_severity in ['high', 'medium']:
        send_alert(packet, location)
        if threat_severity == 'high':
            notify_security_authorities(location)

def forward_to_local(log_message):
    try:
        with open('local_logs.txt', 'a') as log_file:
            log_file.write(f"{datetime.now()} - {log_message}\n")
    except Exception as e:
        logging.error(f"Error writing to local log file: {e}")

def block_ip(ip_address):
    try:
        ensure_admin_privileges()
        rule_name = f"Block {ip_address}"
        result = subprocess.run([
            'netsh', 'advfirewall', 'firewall', 'add', 'rule',
            f'name={rule_name}', 'dir=in', 'action=block', f'remoteip={ip_address}'
        ], capture_output=True, text=True, check=True)
        logging.info(f"Blocked IP {ip_address}. Output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error blocking IP {ip_address}: {e}. Output: {e.output}")
    except Exception as e:
        logging.error(f"Unexpected error blocking IP {ip_address}: {e}")

def redirect_to_virtual_network(packet):
    adapter_name = "vEthernet (Alpha) 3"
    try:
        logging.info(f"Checking for virtual network adapter '{adapter_name}'.")
        check_result = subprocess.run([
            'powershell', '-Command',
            f'Get-NetAdapter -Name "{adapter_name}"'
        ], capture_output=True, text=True)
        
        if "Not Found" in check_result.stdout:
            logging.info(f"Creating virtual network adapter '{adapter_name}'.")
            create_adapter_result = subprocess.run([
                'powershell', '-Command',
                f'New-NetAdapter -Name "{adapter_name}" -InterfaceDescription "Virtual Adapter"'
            ], capture_output=True, text=True, check=True)
            logging.info(f"Created virtual network adapter '{adapter_name}'. Output: {create_adapter_result.stdout}")
            
            logging.info(f"Configuring virtual network adapter '{adapter_name}'.")
            set_ip_result = subprocess.run([
                'powershell', '-Command',
                f'Set-NetIPInterface -InterfaceAlias "{adapter_name}" -Dhcp Disabled'
            ], capture_output=True, text=True, check=True)
            logging.info(f"Disabled DHCP on virtual network adapter '{adapter_name}'. Output: {set_ip_result.stdout}")
            
            logging.info(f"Adding routing rule to virtual network adapter '{adapter_name}'.")
            route_result = subprocess.run([
                'powershell', '-Command',
                f'New-NetRoute -DestinationPrefix "192.168.100.0/24" -InterfaceAlias "{adapter_name}" -NextHop "192.168.100.1"'
            ], capture_output=True, text=True)
            logging.info(f"Configured routing for virtual network adapter '{adapter_name}'. Output: {route_result.stdout}")
        else:
            logging.info(f"Network adapter '{adapter_name}' found. Configuring it.")
            set_ip_result = subprocess.run([
                'powershell', '-Command',
                f'Set-NetIPInterface -InterfaceAlias "{adapter_name}" -Dhcp Disabled'
            ], capture_output=True, text=True, check=True)
            logging.info(f"Disabled DHCP on virtual network adapter '{adapter_name}'. Output: {set_ip_result.stdout}")

            logging.info(f"Adding routing rule to virtual network adapter '{adapter_name}'.")
            route_result = subprocess.run([
                'powershell', '-Command',
                f'New-NetRoute -DestinationPrefix "192.168.100.0/24" -InterfaceAlias "{adapter_name}" -NextHop "192.168.100.1"'
            ], capture_output=True, text=True)
            logging.info(f"Configured routing for virtual network adapter '{adapter_name}'. Output: {route_result.stdout}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Error redirecting traffic to virtual network adapter '{adapter_name}': {e}. Output: {e.output}")
    except Exception as e:
        logging.error(f"Unexpected error redirecting traffic to virtual network adapter '{adapter_name}': {e}")

def perform_countermeasures(location):
    if location:
        country = location.get('country', 'Unknown')
        city = location.get('city', 'Unknown')
        logging.info(f"Performing countermeasures for attack from {city}, {country}.")
        if country in ['US', 'RU', 'CN']:
            logging.info(f"Blocking IP range for country {country}.")
        logging.info("Notifying security authorities.")
        notify_security_authorities(location)

def notify_security_authorities(location):
    global notification_email
    msg = MIMEText(f"Critical threat detected from {location}. Immediate attention required.")
    msg['Subject'] = 'Security Alert: Cyber Attack'
    msg['From'] = notification_email
    msg['To'] = notification_email
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(os.getenv('EMAIL_USER'), os.getenv('EMAIL_PASS'))
            server.sendmail(msg['From'], [msg['To']], msg.as_string())
        logging.info("Notification sent to security authorities.")
    except smtplib.SMTPAuthenticationError as e:
        logging.error(f"SMTP Authentication Error: {e}")
    except Exception as e:
        logging.error(f"Error sending notification: {e}")

def handle_packet(packet, model, signatures, kmeans_model, dbscan_model):
    if IP in packet and TCP in packet:
        features = preprocess_data(packet)
        location = get_geolocation(packet[IP].src)
        threat_detected = False
        threat_type = None

        if detect_threat(features, model):
            threat_detected = True
            threat_type = "General Threat"
        elif detect_hacking(packet):
            threat_detected = True
            threat_type = "Hacking Attempt"
        elif detect_malware_injection(packet):
            threat_detected = True
            threat_type = "Malware Injection"
        elif detect_exploitation_attempt(packet):
            threat_detected = True
            threat_type = "Exploitation Attempt"
        elif check_signatures(packet, signatures):
            threat_detected = True
            threat_type = "Signature Match"
        elif behavioral_analysis(packet, kmeans_model, dbscan_model):
            threat_detected = True
            threat_type = "Behavioral Anomaly"

        if threat_detected:
            automated_response(packet, location, threat_type)

def ensure_admin_privileges():
    if not is_admin():
        logging.warning("Script not running with administrative privileges. Attempting to relaunch.")
        run_as_admin()
    else:
        logging.info("Script is running with administrative privileges.")

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    script_path = os.path.abspath(sys.argv[0])
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script_path}" elevated', None, 1)
        sys.exit(0)
    except Exception as e:
        logging.error(f"Failed to elevate privileges: {e}")
        sys.exit(1)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
