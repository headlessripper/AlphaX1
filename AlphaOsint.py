import sys
import requests
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton,
    QLabel, QMessageBox
)

class PhoneNumberValidator:
    API_KEY = 'ad16040e50d2d0ff022ec7f4546d2520'
    BASE_URL = 'http://apilayer.net/api/validate'

    @classmethod
    def validate(cls, phone_number, country_code=''):
        params = {
            'access_key': cls.API_KEY,
            'number': phone_number,
            'country_code': country_code,
            'format': 1
        }
        
        try:
            response = requests.get(cls.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}

class IPTracker:
    API_KEY = 'iBDQ29ox9MkLI9yzkcb0OlVQurlwOmK2'
    BASE_URL = 'https://api.apilayer.com/ip_to_location/'

    @classmethod
    def track(cls, ip_address):
        headers = {'apikey': cls.API_KEY}
        
        try:
            response = requests.get(cls.BASE_URL + ip_address, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}

class PositionStackAPI:
    API_KEY = '740aba678070535476f4ee637aeaa6e8'
    BASE_URL = 'http://api.positionstack.com/v1/reverse'

    @classmethod
    def get_location(cls, latitude, longitude):
        params = {
            'access_key': cls.API_KEY,
            'query': f"{latitude},{longitude}",
            'limit': 1
        }
        
        try:
            response = requests.get(cls.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Phone Number Validator & IP Tracker & Location Finder')
        self.setGeometry(100, 100, 400, 400)
        self.setWindowIcon(QIcon('background/icon.png'))

        layout = QVBoxLayout()

        # Phone number input
        self.phone_input = QLineEdit(self)
        self.phone_input.setPlaceholderText('Enter phone number (with country code)')
        layout.addWidget(self.phone_input)

        self.country_code_input = QLineEdit(self)
        self.country_code_input.setPlaceholderText('Enter country code (optional)')
        layout.addWidget(self.country_code_input)

        self.validate_button = QPushButton('Validate Phone Number', self)
        self.validate_button.clicked.connect(self.validate_phone)
        layout.addWidget(self.validate_button)

        # IP input
        self.ip_input = QLineEdit(self)
        self.ip_input.setPlaceholderText('Enter IP address')
        layout.addWidget(self.ip_input)

        self.track_button = QPushButton('Track IP Location', self)
        self.track_button.clicked.connect(self.track_ip)
        layout.addWidget(self.track_button)

        # Location input
        self.location_input = QLineEdit(self)
        self.location_input.setPlaceholderText('Enter latitude,longitude (e.g., 40.7638435,-73.9729691)')
        layout.addWidget(self.location_input)

        self.find_location_button = QPushButton('Find Location', self)
        self.find_location_button.clicked.connect(self.find_location)
        layout.addWidget(self.find_location_button)

        self.result_label = QLabel(self)
        layout.addWidget(self.result_label)

        self.setLayout(layout)

    def validate_phone(self):
        phone_number = self.phone_input.text()
        country_code = self.country_code_input.text()
        result = PhoneNumberValidator.validate(phone_number, country_code)

        if 'error' in result:
            QMessageBox.critical(self, 'Error', f"Error: {result['error']}")
        else:
            info = (
                f"Valid: {result['valid']}\n"
                f"Number: {result['number']}\n"
                f"Local Format: {result['local_format']}\n"
                f"International Format: {result['international_format']}\n"
                f"Country Name: {result['country_name']}\n"
                f"Carrier: {result['carrier']}\n"
                f"Line Type: {result['line_type']}\n"
                f"Location: {result['location']}\n"
            )
            self.result_label.setText(info)

    def track_ip(self):
        ip_address = self.ip_input.text()
        result = IPTracker.track(ip_address)

        if 'error' in result:
            QMessageBox.critical(self, 'Error', f"Error: {result['error']}")
        else:
            info = (
                f"IP: {result['ip']}\n"
                f"Country Name: {result['country_name']}\n"
                f"Region: {result['region_name']}\n"
                f"City: {result['city']}\n"
                f"Latitude: {result['latitude']}\n"
                f"Longitude: {result['longitude']}\n"
            )
            
            if 'connection' in result and 'isp' in result['connection']:
                info += f"ISP: {result['connection']['isp']}\n"
            else:
                info += "ISP information not available.\n"

            self.result_label.setText(info)

    def find_location(self):
        coords = self.location_input.text()
        try:
            latitude, longitude = coords.split(',')
            result = PositionStackAPI.get_location(latitude.strip(), longitude.strip())

            if 'error' in result:
                QMessageBox.critical(self, 'Error', f"Error: {result['error']}")
            else:
                if isinstance(result, dict) and 'data' in result:
                    location_data = result['data']
                    if location_data:
                        loc = location_data[0]
                        info = (
                            f"Location: {loc['label']}\n"
                            f"Name: {loc['name']}\n"
                            f"Street: {loc['street']}\n"
                            f"Postal Code: {loc['postal_code']}\n"
                            f"Region: {loc['region']}\n"
                            f"Country: {loc['country']}\n"
                            f"Map URL: {loc['map_url']}\n"
                        )
                        self.result_label.setText(info)
                    else:
                        self.result_label.setText("No results found.")
                else:
                    QMessageBox.critical(self, 'Error', "Unexpected response format from PositionStack API.")
        except ValueError:
            QMessageBox.critical(self, 'Error', "Please enter valid latitude and longitude.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())
