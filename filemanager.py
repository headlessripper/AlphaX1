import os
import shutil
from PyQt6 import QtWidgets, QtGui, QtCore
import sys
from PyQt6.QtGui import QFont, QIcon, QPixmap

class FileManager(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle("File Manager")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowTitle('Alpha')
        self.setWindowIcon(QIcon('background/icon.png'))

        self.layout = QtWidgets.QVBoxLayout()
        
        self.path_line_edit = QtWidgets.QLineEdit(self)
        self.layout.addWidget(self.path_line_edit)

        self.list_widget = QtWidgets.QListWidget(self)
        self.layout.addWidget(self.list_widget)

        self.button_layout = QtWidgets.QHBoxLayout()

        self.refresh_button = QtWidgets.QPushButton("Refresh", self)
        self.refresh_button.clicked.connect(self.refresh)
        self.button_layout.addWidget(self.refresh_button)

        self.create_button = QtWidgets.QPushButton("Create File", self)
        self.create_button.clicked.connect(self.create_file)
        self.button_layout.addWidget(self.create_button)

        self.delete_button = QtWidgets.QPushButton("Delete File", self)
        self.delete_button.clicked.connect(self.delete_file)
        self.button_layout.addWidget(self.delete_button)

        self.move_button = QtWidgets.QPushButton("Move File", self)
        self.move_button.clicked.connect(self.move_file)
        self.button_layout.addWidget(self.move_button)

        self.copy_button = QtWidgets.QPushButton("Copy File", self)
        self.copy_button.clicked.connect(self.copy_file)
        self.button_layout.addWidget(self.copy_button)

        self.layout.addLayout(self.button_layout)
        self.setLayout(self.layout)

        self.refresh()

    def refresh(self):
        self.list_widget.clear()
        path = self.path_line_edit.text() or os.getcwd()
        self.path_line_edit.setText(path)

        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                self.list_widget.addItem(f"{'DIR' if os.path.isdir(item_path) else 'FILE'}: {item}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Could not list files: {e}")

    def create_file(self):
        filename, ok = QtWidgets.QInputDialog.getText(self, "Create File", "Enter filename:")
        if ok and filename:
            path = self.path_line_edit.text()
            full_path = os.path.join(path, filename)
            try:
                with open(full_path, 'w'):
                    pass
                self.refresh()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Could not create file: {e}")

    def delete_file(self):
        item = self.list_widget.currentItem()
        if item:
            filename = item.text().split(": ")[1]
            path = self.path_line_edit.text()
            full_path = os.path.join(path, filename)
            try:
                os.remove(full_path)
                self.refresh()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Could not delete file: {e}")

    def move_file(self):
        item = self.list_widget.currentItem()
        if item:
            filename = item.text().split(": ")[1]
            path = self.path_line_edit.text()
            full_path = os.path.join(path, filename)

            new_location, ok = QtWidgets.QFileDialog.getExistingDirectory(self, "Select New Directory")
            if ok:
                try:
                    shutil.move(full_path, new_location)
                    self.refresh()
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Error", f"Could not move file: {e}")

    def copy_file(self):
        item = self.list_widget.currentItem()
        if item:
            filename = item.text().split(": ")[1]
            path = self.path_line_edit.text()
            full_path = os.path.join(path, filename)

            new_location, ok = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Destination Directory")
            if ok:
                try:
                    shutil.copy(full_path, os.path.join(new_location, filename))
                    self.refresh()
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Error", f"Could not copy file: {e}")

def main():
    app = QtWidgets.QApplication(sys.argv)
    file_manager = FileManager()
    file_manager.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
