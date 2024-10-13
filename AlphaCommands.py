import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QListWidget, QVBoxLayout, QWidget, QLabel, QScrollArea
from PyQt6.QtGui import QFont, QIcon, QPixmap

class CommandListWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Possible Commands")
        self.setGeometry(100, 100, 400, 400)
        self.setWindowTitle('Alpha')
        self.setWindowIcon(QIcon('background/icon.png'))

        # Create a QWidget for the main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create a vertical layout
        layout = QVBoxLayout()

        # Create a label for the title
        title_label = QLabel("Alpha Commands")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title_label)

        # Create a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Create a widget to hold the list
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)

        # List of commands
        commands = [
            "calculate", "website", "hello", "search for", "tell me about", "suspend",
            "unsuspend", "shutdown my computer", "goodbye", "put my computer to sleep", "start code 255: info gathering", "start code 236: fail safe only for when being hacked",
            "time", "date", "News", "hibernate", "alpha view", "lookup: for phone number and ip tracking", "password manager",
            "password generator", "maps", "exit", "install", "ask Wolfram",
            "alpha install", "who created you", "Alpha say hi", "i am doing ok",
            "what is your name", "what is your purpose", "open", "play",
            "increase volume", "decrease volume", "mute", "undo", "increase brightness",
            "decrease brightness", "turn on Wi-Fi", "turn off Wi-Fi", "turn on Bluetooth",
            "turn off Bluetooth", "enable online security", "box", "workstation",
            "remember", "recall", "access", "install", "news", "Alpha cmd", "open",
            "activate", "deactivate", "set alarm"
        ]

        # Add commands to the list layout
        for command in commands:
            list_layout.addWidget(QLabel(command))

        # Set the list widget in the scroll area
        scroll_area.setWidget(list_widget)

        # Add scroll area to the main layout
        layout.addWidget(scroll_area)

        # Set the layout for the central widget
        central_widget.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CommandListWindow()
    window.show()
    sys.exit(app.exec())
