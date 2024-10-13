import sys
import subprocess
import requests
import random
import json
import logging
import os
import bcrypt
from requests.exceptions import RequestException
from PyQt6 import QtWidgets
from cryptography.fernet import Fernet
from PyQt6.QtGui import QFont, QIcon, QPixmap

# Set up logging
logging.basicConfig(level=logging.INFO)

class LoginManager:
    def __init__(self, filename='pin.json'):
        self.filename = filename
        self.hashed_pin = self.load_hashed_pin()

    def load_hashed_pin(self):
        """Load hashed PIN from the JSON file."""
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as file:
                return json.load(file).get('hashed_pin')
        return None

    def set_pin(self, pin):
        """Hash and save the PIN to the JSON file."""
        hashed = bcrypt.hashpw(pin.encode(), bcrypt.gensalt())
        with open(self.filename, 'w') as file:
            json.dump({'hashed_pin': hashed.decode()}, file)
        logging.info("PIN set successfully.")

    def verify_pin(self, pin):
        """Verify the provided PIN against the stored hashed PIN."""
        if self.hashed_pin:
            return bcrypt.checkpw(pin.encode(), self.hashed_pin.encode())
        return False

class PasswordManager:
    def __init__(self, filename='passwords.json'):
        self.filename = filename
        self.key = self.load_key()
        self.cipher = Fernet(self.key)

    def load_key(self):
        """Load or create a new encryption key."""
        if os.path.exists('secret.key'):
            with open('secret.key', 'rb') as key_file:
                key = key_file.read()
                try:
                    Fernet(key)
                    return key
                except ValueError:
                    logging.warning("Invalid key found, generating a new one.")

        key = Fernet.generate_key()
        with open('secret.key', 'wb') as key_file:
            key_file.write(key)
        return key

    def save_password(self, service, password):
        """Save a new password."""
        encrypted_password = self.cipher.encrypt(password.encode())
        passwords = self.load_passwords()
        passwords[service] = encrypted_password.decode()
        self.save_passwords(passwords)
        logging.info(f"Password saved for {service}.")

    def load_passwords(self):
        """Load passwords from the JSON file."""
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as file:
                return json.load(file)
        return {}

    def save_passwords(self, passwords):
        """Save passwords to the JSON file."""
        with open(self.filename, 'w') as file:
            json.dump(passwords, file)

    def get_password(self, service):
        """Retrieve a password for a specific service."""
        passwords = self.load_passwords()
        if service in passwords:
            encrypted_password = passwords[service].encode()
            return self.cipher.decrypt(encrypted_password).decode()
        return None

    def delete_password(self, service):
        """Delete a password for a specific service."""
        passwords = self.load_passwords()
        if service in passwords:
            del passwords[service]
            self.save_passwords(passwords)
            logging.info(f"Password deleted for {service}.")
        else:
            logging.warning(f"No password found for {service}.")

class NetworkManager:
    def __init__(self, proxy_list):
        self.proxy_list = proxy_list
        self.active = False

    def activate_incognito_mode(self):
        self.active = True
        logging.info("Incognito mode activated.")
        self.disable_non_wifi_connections()

    def deactivate_incognito_mode(self):
        self.active = False
        logging.info("Incognito mode deactivated.")
        self.enable_all_connections()

    def disable_non_wifi_connections(self):
        try:
            interfaces = subprocess.check_output("netsh interface show interface", shell=True, text=True)
            for line in interfaces.splitlines():
                if "Connected" in line and "Wi-Fi" not in line:
                    interface_name = line.split()[0]
                    logging.info(f"Disabling connection: {interface_name}")
                    subprocess.run(["netsh", "interface", "set", "interface", interface_name, "admin=disabled"], check=True)
            logging.info("Non-Wi-Fi connections disabled.")
        except Exception as e:
            logging.error(f"Error disabling connections: {e}")

    def enable_all_connections(self):
        try:
            interfaces = subprocess.check_output("netsh interface show interface", shell=True, text=True)
            for line in interfaces.splitlines():
                if "Disabled" in line:
                    interface_name = line.split()[0]
                    logging.info(f"Enabling connection: {interface_name}")
                    subprocess.run(["netsh", "interface", "set", "interface", interface_name, "admin=enabled"], check=True)
            logging.info("All connections enabled.")
        except Exception as e:
            logging.error(f"Error enabling connections: {e}")

    def get_random_proxy(self):
        return random.choice(self.proxy_list)

    def validate_proxies(self):
        valid_proxies = []
        for proxy in self.proxy_list:
            try:
                response = requests.get("http://httpbin.org/ip", proxies={"http": proxy, "https": proxy}, timeout=3)
                if response.ok:
                    valid_proxies.append(proxy)
                    logging.info(f"Proxy {proxy} is valid.")
            except RequestException:
                logging.warning(f"Proxy {proxy} is invalid.")
        self.proxy_list = valid_proxies

    def make_request(self, url):
        if not self.active:
            logging.warning("Incognito mode is not active. Please activate it first.")
            return

        if not self.proxy_list:
            logging.error("No valid proxies available.")
            return

        proxy = self.get_random_proxy()
        logging.info(f"Using proxy: {proxy}")

        proxies = {
            "http": proxy,
            "https": proxy,
        }

        try:
            response = requests.get(url, proxies=proxies, timeout=5)
            response.raise_for_status()
            return response.text
        except RequestException as e:
            logging.error(f"An error occurred: {e}")

def load_config(filename):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"Failed to load config file {filename}: {e}")
        return {}

class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Network Manager & Password Manager")
        self.setGeometry(100, 100, 400, 300)
        self.setWindowTitle('Alpha')
        self.setWindowIcon(QIcon('background/icon.png'))

        # Layout
        self.layout = QtWidgets.QVBoxLayout()

        # Password Manager UI
        self.service_input = QtWidgets.QLineEdit(self)
        self.service_input.setPlaceholderText("Service Name")
        self.password_input = QtWidgets.QLineEdit(self)
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

        self.save_password_button = QtWidgets.QPushButton("Save Password")
        self.get_password_button = QtWidgets.QPushButton("Get Password")
        self.delete_password_button = QtWidgets.QPushButton("Delete Password")
        self.activate_button = QtWidgets.QPushButton("Activate Incognito")
        self.deactivate_button = QtWidgets.QPushButton("Deactivate Incognito")

        # Connect buttons to functions
        self.save_password_button.clicked.connect(self.save_password)
        self.get_password_button.clicked.connect(self.get_password)
        self.delete_password_button.clicked.connect(self.delete_password)
        self.activate_button.clicked.connect(self.activate_incognito)
        self.deactivate_button.clicked.connect(self.deactivate_incognito)

        # Add widgets to layout
        self.layout.addWidget(self.service_input)
        self.layout.addWidget(self.password_input)
        self.layout.addWidget(self.save_password_button)
        self.layout.addWidget(self.get_password_button)
        self.layout.addWidget(self.delete_password_button)
        self.layout.addWidget(self.activate_button)
        self.layout.addWidget(self.deactivate_button)

        # Set central widget
        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)

        # Load configuration
        self.config = load_config('config.json')
        self.network_manager = NetworkManager(self.config.get('proxy_list', []))
        self.password_manager = PasswordManager()

    def save_password(self):
        service = self.service_input.text()
        password = self.password_input.text()
        if service and password:
            self.password_manager.save_password(service, password)
            QtWidgets.QMessageBox.information(self, "Success", "Password saved successfully.")
            self.service_input.clear()
            self.password_input.clear()
        else:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please enter both service and password.")

    def get_password(self):
        service = self.service_input.text()
        if service:
            password = self.password_manager.get_password(service)
            if password:
                QtWidgets.QMessageBox.information(self, "Password", f"Password for {service}: {password}")
            else:
                QtWidgets.QMessageBox.warning(self, "Warning", "No password found for that service.")
        else:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please enter a service name.")

    def delete_password(self):
        service = self.service_input.text()
        if service:
            self.password_manager.delete_password(service)
            QtWidgets.QMessageBox.information(self, "Success", "Password deleted successfully.")
        else:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please enter a service name.")

    def activate_incognito(self):
        self.network_manager.activate_incognito_mode()
        QtWidgets.QMessageBox.information(self, "Info", "Incognito mode activated.")

    def deactivate_incognito(self):
        self.network_manager.deactivate_incognito_mode()
        QtWidgets.QMessageBox.information(self, "Info", "Incognito mode deactivated.")

class LoginWindow(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setGeometry(100, 100, 300, 150)
        self.setWindowTitle('Alpha')
        self.setWindowIcon(QIcon('background/icon.png'))

        self.layout = QtWidgets.QVBoxLayout()

        self.pin_input = QtWidgets.QLineEdit(self)
        self.pin_input.setPlaceholderText("Enter PIN")
        self.pin_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

        self.set_pin_button = QtWidgets.QPushButton("Set PIN")
        self.login_button = QtWidgets.QPushButton("Login")

        self.layout.addWidget(self.pin_input)
        self.layout.addWidget(self.set_pin_button)
        self.layout.addWidget(self.login_button)

        self.setLayout(self.layout)

        self.login_manager = LoginManager()

        # Check if PIN already exists
        if self.login_manager.hashed_pin:
            self.set_pin_button.hide()
            self.login_button.setText("Login")
        else:
            self.login_button.setText("Enter")

        self.set_pin_button.clicked.connect(self.set_pin)
        self.login_button.clicked.connect(self.login)

    def set_pin(self):
        pin = self.pin_input.text()
        if pin:
            self.login_manager.set_pin(pin)
            QtWidgets.QMessageBox.information(self, "Success", "PIN set successfully.")
            self.close()
        else:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please enter a PIN.")

    def login(self):
        pin = self.pin_input.text()
        if self.login_manager.verify_pin(pin):
            QtWidgets.QMessageBox.information(self, "Success", "Access granted.")
            self.close()
            self.open_main_app()
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Incorrect PIN. Access denied.")

    def open_main_app(self):
        self.main_app = App()
        self.main_app.show()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    login_window = LoginWindow()
    login_window.exec()
    sys.exit(app.exec())
