import sys
import pandas as pd
import logging
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QTextEdit, QVBoxLayout, QWidget, QPushButton, QFileDialog,
    QTreeWidget, QTreeWidgetItem, QInputDialog, QMessageBox, QStatusBar, QMenu
)
from PyQt6.QtGui import QPainter, QColor, QPixmap, QImage, QContextMenuEvent, QAction
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

logging.basicConfig(filename='app.log', level=logging.ERROR)

# Define a color palette
PRIMARY_COLOR = "#007BFF"
BACKGROUND_COLOR = "#000000"  # Black background
TEXT_COLOR = "#FFFFFF"  # White text

class Whiteboard(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.image = QImage(800, 600, QImage.Format.Format_RGB888)
        self.image.fill(Qt.GlobalColor.black)
        self.pixmap = QPixmap.fromImage(self.image)
        self.last_point = None
        self.current_color = Qt.GlobalColor.white  # White color for drawing
        self.current_tool = 'pen'

        self.setMinimumSize(800, 600)
        self.setStyleSheet(f"background-color: {BACKGROUND_COLOR};")

        # Add a Clear button
        self.clear_button = self.create_button("Clear", self.clear)
        self.clear_button.setGeometry(10, 10, 100, 30)

    def create_button(self, label, callback):
        button = QPushButton(label, self)
        button.setStyleSheet(f"""
            background-color: {PRIMARY_COLOR};
            color: {TEXT_COLOR};
            border: none;
            padding: 10px;
            border-radius: 5px;
            font-size: 14px;
            """)
        button.clicked.connect(callback)
        return button

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_point = event.position()

    def mouseMoveEvent(self, event):
        if self.last_point is not None:
            painter = QPainter(self.pixmap)
            painter.setPen(QColor(self.current_color))
            if self.current_tool == 'pen':
                painter.drawLine(self.last_point, event.position())
            painter.end()
            self.last_point = event.position()
            self.update()

    def contextMenuEvent(self, event: QContextMenuEvent):
        context_menu = QMenu(self)

        clear_action = QAction("Clear", self)
        clear_action.triggered.connect(self.clear)
        context_menu.addAction(clear_action)

        context_menu.exec(event.globalPosition().toPoint())

    def clear(self):
        self.pixmap.fill(Qt.GlobalColor.black)
        self.update()

    def set_tool(self, tool):
        self.current_tool = tool

class NotesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setStyleSheet(f"background-color: {BACKGROUND_COLOR};")
        self.layout = QVBoxLayout(self)
        self.notes_list = QTreeWidget()
        self.notes_list.setHeaderLabels(["Notes"])
        self.notes_list.setStyleSheet(f"background-color: #000000; color: {TEXT_COLOR}; border: 1px solid #ddd;")
        self.layout.addWidget(self.notes_list)

        self.note_content = QTextEdit()
        self.note_content.setStyleSheet(f"background-color: #000000; color: {TEXT_COLOR}; border: 1px solid #ddd;")
        self.layout.addWidget(self.note_content)

        self.create_button_layout()
        self.notes = {}
        self.load_notes()

    def create_button_layout(self):
        button_layout = QVBoxLayout()

        self.new_button = self.create_button("New Note", self.new_note)
        button_layout.addWidget(self.new_button)

        self.save_button = self.create_button("Save Note", self.save_note)
        button_layout.addWidget(self.save_button)

        self.load_button = self.create_button("Load Note", self.load_note_from_file)
        button_layout.addWidget(self.load_button)

        self.layout.addLayout(button_layout)

    def create_button(self, label, callback):
        button = QPushButton(label, self)
        button.setStyleSheet(f"""
            background-color: {PRIMARY_COLOR};
            color: {TEXT_COLOR};
            border: none;
            padding: 10px;
            border-radius: 5px;
            font-size: 14px;
            """)
        button.clicked.connect(callback)
        return button

    def load_notes(self):
        self.notes_list.clear()
        for note_title in self.notes.keys():
            item = QTreeWidgetItem([note_title])
            self.notes_list.addTopLevelItem(item)

    def new_note(self):
        note_title, ok = QInputDialog.getText(self, 'New Note', 'Enter note title:')
        if ok and note_title:
            self.notes[note_title] = ""
            self.load_notes()
            self.notes_list.setCurrentItem(self.notes_list.findItems(note_title, Qt.MatchFlag.MatchExactly)[0])

    def save_note(self):
        note_title = self.notes_list.currentItem().text(0) if self.notes_list.currentItem() else None
        current_note_content = self.note_content.toPlainText()

        if note_title:
            file_name, _ = QFileDialog.getSaveFileName(self, "Save Note", f"{note_title}.txt", "Text Files (*.txt)")
            if file_name:
                with open(file_name, 'w') as file:
                    file.write(current_note_content)
                QMessageBox.information(self, "Note Saved", "Note has been saved successfully.")
        else:
            new_title, ok = QInputDialog.getText(self, 'New Note Title', 'Enter note title:')
            if ok and new_title:
                file_name, _ = QFileDialog.getSaveFileName(self, "Save Note", f"{new_title}.txt", "Text Files (*.txt)")
                if file_name:
                    with open(file_name, 'w') as file:
                        file.write(current_note_content)
                    self.notes[new_title] = current_note_content
                    self.load_notes()
                    QMessageBox.information(self, "Note Saved", "New note has been saved successfully.")
            else:
                QMessageBox.warning(self, "No Title Entered", "Please enter a title for the note.")

    def load_note_from_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Note", "", "Text Files (*.txt)")
        if file_name:
            with open(file_name, 'r') as file:
                content = file.read()
                note_title = file_name.split("/")[-1].replace(".txt", "")
                self.notes[note_title] = content
                self.load_notes()
                self.note_content.setPlainText(content)
                self.notes_list.setCurrentItem(self.notes_list.findItems(note_title, Qt.MatchFlag.MatchExactly)[0])

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Alpha Suite")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon('background/icon.png'))

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"background-color: {BACKGROUND_COLOR}; border: 1px solid #ddd;")
        self.setCentralWidget(self.tabs)

        self.whiteboard = Whiteboard()
        self.notes_tab = NotesTab()

        self.tabs.addTab(self.whiteboard, "Whiteboard")
        self.tabs.addTab(self.notes_tab, "Notes")

        self.create_status_bar()

    def create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status("Ready")

    def update_status(self, message):
        self.status_bar.showMessage(message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
