import sys
import datetime
import threading
import subprocess
import psutil
import time
import requests
import speech_recognition as sr
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QTextBrowser, QPushButton, QSplashScreen, QLineEdit, QGridLayout
import logging
import os

# Replace these with your actual API key and CSE ID
API_KEY = 'AIzaSyBwehvm4IIKA_FZeeJL3ddFUtiIxtgWtUA'
CSE_ID = '028c5f61bafcb4194'

# Setup logging
logging.basicConfig(filename='app.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class Communicator(QObject):
    new_speech = pyqtSignal(str)
    new_stdout = pyqtSignal(str)
    new_stderr = pyqtSignal(str)

class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.is_dark_mode = True
        self.setup_ui()
        self.setup_signals()
        self.setup_timers()
        self.start_alpha_process()
        self.start_alpha_commands_process()
        self.start_power_monitoring()
        self.show_splash_screen()

    def setup_ui(self):
        """Initialize and set up the UI components."""
        self.setGeometry(100, 100, 600, 450)  # Adjusted size for better layout
        self.setWindowTitle('Alpha')
        self.setWindowIcon(QIcon('background/icon.png'))

        # Create main layout
        layout = QGridLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Set up the search bar
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText('Enter search query...')
        self.search_bar.setStyleSheet("padding: 10px; font-size: 14px; border-radius: 5px;")
        layout.addWidget(self.search_bar, 0, 0, 1, 2)

        # Set up the search button
        self.search_button = QPushButton('Search', self)
        self.search_button.setStyleSheet("background-color: #555555; color: #FFFFFF; padding: 10px; border-radius: 5px;")
        self.search_button.clicked.connect(self.perform_search)
        layout.addWidget(self.search_button, 0, 2)

        # Set up the text browser
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)  # Allow opening links
        self.text_browser.setFont(QFont('Arial', 12))
        self.text_browser.setStyleSheet(""" 
            QTextBrowser {
                padding: 10px;
                border-radius: 5px;
                background-image: url('background/2003ca7f-9c50-41c2-bf4b-08b2411e82cd.jpeg');
                background-repeat: no-repeat;
                background-position: center;
                background-attachment: fixed;
                background-color: #2E2E2E;
                border: 1px solid #444444;
                color: #E0E0E0;
            }
        """)
        layout.addWidget(self.text_browser, 1, 0, 1, 3)

        # Set up the time label
        self.time_label = QLabel()
        self.time_label.setFont(QFont('Arial', 24))
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("color: #E0E0E0; padding: 10px;")
        layout.addWidget(self.time_label, 2, 0, 1, 3)

        # Set up the power label
        self.power_label = QLabel()
        self.power_label.setFont(QFont('Arial', 12))
        self.power_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.power_label.setStyleSheet("color: #E0E0E0; padding: 10px;")
        layout.addWidget(self.power_label, 3, 0, 1, 3)

        # Set up the dark mode toggle button
        self.toggle_button = QPushButton(QIcon('background/icons8-moon-30.png'), '', self)
        self.toggle_button.setStyleSheet("background-color: #333333; color: #E0E0E0; padding: 10px; border-radius: 5px;")
        self.toggle_button.clicked.connect(self.toggle_dark_mode)
        layout.addWidget(self.toggle_button, 4, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)
        self.update_stylesheet()

    def show_splash_screen(self):
        """Show a splash screen while the app is initializing."""
        splash_pix = QPixmap('background/splash.png')
        splash = QSplashScreen(splash_pix, Qt.WindowType.FramelessWindowHint)
        splash.show()
        QTimer.singleShot(2000, splash.close)  # Adjust timing as needed

    def update_stylesheet(self):
        """Update the application stylesheet based on the current mode."""
        if self.is_dark_mode:
            self.setStyleSheet(""" 
                QWidget {
                    background-color: #1E1E1E;  /* Darker background for contrast */
                    color: #E0E0E0;             /* Light text color for readability */
                }
                QPushButton {
                    background-color: #333333;  /* Dark button background */
                    color: #E0E0E0;             /* Light button text */
                    border-radius: 5px;        /* Rounded corners */
                    padding: 10px;             /* Padding for a better click area */
                }
                QPushButton:hover {
                    background-color: #444444;  /* Lighter button background on hover */
                }
            """)
        else:
            self.setStyleSheet(""" 
                QWidget {
                    background-color: #FFFFFF;  /* Light background for a brighter look */
                    color: #000000;             /* Dark text color for readability */
                }
                QPushButton {
                    background-color: #DDDDDD;  /* Light button background */
                    color: #000000;             /* Dark button text */
                    border-radius: 5px;        /* Rounded corners */
                    padding: 10px;             /* Padding for a better click area */
                }
                QPushButton:hover {
                    background-color: #CCCCCC;  /* Slightly darker button background on hover */
                }
            """)

    def setup_signals(self):
        """Set up signal-slot connections."""
        self.r = sr.Recognizer()
        self.communicator = Communicator()
        self.communicator.new_speech.connect(self.speak_text)
        self.communicator.new_stdout.connect(self.handle_stdout_message)
        self.communicator.new_stderr.connect(self.handle_stderr_message)

    def setup_timers(self):
        """Set up timers for updating UI components."""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        self.power_timer = QTimer()
        self.power_timer.timeout.connect(self.update_power_consumption)
        self.power_timer.start(10000)  # Update every 10 seconds

    def check_alpha_commands_process(self):
        """Check if AlphaCommands.py is running."""
        for proc in psutil.process_iter(['pid', 'name']):
            if 'AlphaCommands.py' in proc.info['name']:
                return True
        return False

    def check_alpha_process(self):
        """Check if Alpha.py is running."""
        for proc in psutil.process_iter(['pid', 'name']):
            if 'Alpha.py' in proc.info['name']:
                return True
        return False

    def start_alpha_process(self):
        """Start the Alpha.py subprocess in a separate thread and handle exceptions."""
        if not self.check_alpha_process():
            try:
                self.alpha_thread = threading.Thread(target=self.run_alpha_process, daemon=True)
                self.alpha_thread.start()
                logging.info('Started Alpha.py process in a new thread.')
            except Exception as e:
                logging.error(f"Error starting Alpha.py: {e}")
                self.text_browser.append(f"Error starting Alpha.py: {e}")
        else:
            logging.info('Alpha.py process is already running.')

    def run_alpha_process(self):
        """Run Alpha.py and handle its output."""
        self.alpha_process = subprocess.Popen(
            [sys.executable, 'Alpha.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        # Start threads to handle stdout and stderr
        self.stdout_thread = threading.Thread(target=self.handle_stdout, daemon=True)
        self.stderr_thread = threading.Thread(target=self.handle_stderr, daemon=True)
        self.stdout_thread.start()
        self.stderr_thread.start()

    def check_alpha_commands_process(self):
        """Check if AlphaCommands.exe is running."""
        for proc in psutil.process_iter(['pid', 'name']):
            if 'AlphaCommands.exe' in proc.info['name']:
                return True
        return False

    def start_alpha_commands_process(self):
        """Start the AlphaCommands.exe subprocess in a separate thread and handle exceptions."""
        if not self.check_alpha_commands_process():
            try:
                self.alpha_commands_thread = threading.Thread(target=self.run_alpha_commands_process, daemon=True)
                self.alpha_commands_thread.start()
                logging.info('Started AlphaCommands.exe process in a new thread.')
            except Exception as e:
                logging.error(f"Error starting AlphaCommands.exe: {e}")
                self.text_browser.append(f"Error starting AlphaCommands.exe: {e}")
        else:
            logging.info('AlphaCommands.exe process is already running.')

    def run_alpha_commands_process(self):
        """Run AlphaCommands.exe and handle its output."""
        self.alpha_commands_process = subprocess.Popen(
            ['AlphaCommands.exe'],  # Call the executable directly
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        # Start threads to handle stdout and stderr
        self.stdout_thread_commands = threading.Thread(target=self.handle_stdout_commands, daemon=True)
        self.stderr_thread_commands = threading.Thread(target=self.handle_stderr_commands, daemon=True)
        self.stdout_thread_commands.start()
        self.stderr_thread_commands.start()

    def handle_stdout(self):
        """Handle stdout output from Alpha.py."""
        for line in iter(self.alpha_process.stdout.readline, ''):
            self.communicator.new_stdout.emit(line.strip())

    def handle_stderr(self):
        """Handle stderr output from Alpha.py."""
        for line in iter(self.alpha_process.stderr.readline, ''):
            self.communicator.new_stderr.emit(line.strip())

    def handle_stdout_commands(self):
        """Handle stdout output from AlphaCommands.py."""
        for line in iter(self.alpha_commands_process.stdout.readline, ''):
            self.communicator.new_stdout.emit(line.strip())

    def handle_stderr_commands(self):
        """Handle stderr output from AlphaCommands.py."""
        for line in iter(self.alpha_commands_process.stderr.readline, ''):
            self.communicator.new_stderr.emit(line.strip())

    def handle_stdout_message(self, message):
        """Handle stdout messages from both processes."""
        self.text_browser.append(f"Alpha: {message}")

    def handle_stderr_message(self, message):
        """Handle stderr messages from both processes."""
        self.text_browser.append(f"<p style='color: red;'>Error: {message}</p>")

    def update_time(self):
        """Update the time display."""
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.setText(current_time)

    def update_power_consumption(self):
        """Update the power consumption display."""
        cpu_usage = self.get_cpu_usage_percent()
        memory_usage = self.get_memory_usage_gb()
        power_consumption = self.estimate_power_consumption(cpu_usage, memory_usage)
        self.power_label.setText(
            f"CPU Usage: {cpu_usage:.2f}%\n"
            f"Memory Usage: {memory_usage:.2f} GB\n"
            f"Estimated Power Consumption: {power_consumption:.2f} Watts"
        )

    def speak_text(self, text):
        """Send text to AlphaCommands.py."""
        if not self.alpha_commands_process:
            self.start_alpha_commands_process()
            if not self.alpha_commands_process:
                self.text_browser.append("Failed to restart AlphaCommands.py.")
                return

        try:
            self.alpha_commands_process.stdin.write(text + "\n")
            self.alpha_commands_process.stdin.flush()
        except Exception as e:
            logging.error(f"Error communicating with AlphaCommands.py: {e}")
            self.text_browser.append(f"Error communicating with AlphaCommands.py: {e}")
            self.start_alpha_commands_process()

    def get_cpu_usage_percent(self):
        """Get the CPU usage percentage."""
        return psutil.cpu_percent(interval=1)

    def get_memory_usage_gb(self):
        """Get the memory usage in gigabytes."""
        memory_info = psutil.virtual_memory()
        return memory_info.used / (1024 ** 3)  # Convert bytes to GB

    def estimate_power_consumption(self, cpu_usage_percent, memory_usage_gb):
        """Estimate the power consumption based on CPU and memory usage."""
        CPU_POWER_CONSUMPTION_WATTS = 0.1
        MEMORY_POWER_CONSUMPTION_WATTS = 0.05
        cpu_power = cpu_usage_percent * CPU_POWER_CONSUMPTION_WATTS
        memory_power = memory_usage_gb * MEMORY_POWER_CONSUMPTION_WATTS
        return cpu_power + memory_power

    def start_power_monitoring(self):
        """Start monitoring system power usage in a separate thread."""
        self.power_thread = threading.Thread(target=self.monitor_system, daemon=True)
        self.power_thread.start()

    def monitor_system(self):
        """Monitor the system in a separate thread."""
        while True:
            cpu_usage = self.get_cpu_usage_percent()
            memory_usage = self.get_memory_usage_gb()
            power_consumption = self.estimate_power_consumption(cpu_usage, memory_usage)
            # Optionally log this data if needed
            time.sleep(60)  # Sleep for 60 seconds

    def toggle_dark_mode(self):
        """Toggle between dark and light mode."""
        self.is_dark_mode = not self.is_dark_mode
        self.update_stylesheet()

    def perform_search(self):
        """Perform a Google Custom Search Engine query."""
        query = self.search_bar.text()
        if query:
            try:
                results = self.search_google(query)
                self.display_results(results)
            except Exception as e:
                self.text_browser.setHtml(f"<p style='color: red;'>Error performing search: {e}</p>")
        else:
            self.text_browser.setHtml("<p style='color: red;'>Please enter a search query.</p>")

    def search_google(self, query):
        """Query Google Custom Search Engine API."""
        url = 'https://www.googleapis.com/customsearch/v1'
        params = {
            'key': API_KEY,
            'cx': CSE_ID,
            'q': query
        }
        response = requests.get(url, params=params)
        response.raise_for_status()  # Check for request errors
        return response.json()

    def display_results(self, results):
        """Display search results in the text browser."""
        self.text_browser.clear()
        items = results.get('items', [])
        if items:
            html_content = '<h2>Search Results:</h2>'
            for item in items:
                title = item.get('title', 'No title')
                link = item.get('link', 'No link')
                snippet = item.get('snippet', 'No snippet')
                html_content += f"""
                    <div style="margin-bottom: 20px;">
                        <h3><a href="{link}" style="color: #1E90FF;" target="_blank">{title}</a></h3>
                        <p>{snippet}</p>
                        <a href="{link}" style="color: #1E90FF;" target="_blank">Read more</a>
                    </div>
                """
            self.text_browser.setHtml(html_content)
        else:
            self.text_browser.setHtml('<p>No results found.</p>')

    def closeEvent(self, event):
        """Handle cleanup when the application is closing."""
        if hasattr(self, 'alpha_process'):
            self.alpha_process.terminate()
            self.alpha_process.wait()
        if hasattr(self, 'alpha_commands_process'):
            self.alpha_commands_process.terminate()
            self.alpha_commands_process.wait()
        logging.info('Application closed.')
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())
