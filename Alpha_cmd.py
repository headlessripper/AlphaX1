import sys
import subprocess
from PyQt6 import QtWidgets
from PyQt6.QtGui import QIcon

class CommandLineApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Alpha Command Prompt")
        self.setGeometry(100, 100, 600, 400)
        self.setWindowIcon(QIcon('background/icon.png'))

        self.layout = QtWidgets.QVBoxLayout()

        self.command_input = QtWidgets.QLineEdit(self)
        self.command_input.setPlaceholderText("Enter command here...")
        self.command_input.returnPressed.connect(self.run_command)
        self.layout.addWidget(self.command_input)

        self.output_area = QtWidgets.QTextEdit(self)
        self.output_area.setReadOnly(True)
        self.layout.addWidget(self.output_area)

        # Clear Screen button
        self.clear_button = QtWidgets.QPushButton("Clear Screen", self)
        self.clear_button.clicked.connect(self.clear_output)
        self.layout.addWidget(self.clear_button)

        self.setLayout(self.layout)

    def run_command(self):
        command = self.command_input.text()
        if command.strip():
            self.output_area.append(f"> {command}")
            self.execute_command(command)
            self.command_input.clear()

    def execute_command(self, command):
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            output = result.stdout + result.stderr
            self.output_area.append(output if output else "No output.")
        except Exception as e:
            self.output_area.append(f"Error: {str(e)}")

    def clear_output(self):
        self.output_area.clear()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    cli_app = CommandLineApp()
    cli_app.show()
    sys.exit(app.exec())
