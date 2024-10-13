import sys
from PyQt6.QtCore import QUrl, Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPainter, QRegion
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QPushButton, QInputDialog, QHBoxLayout, QSpacerItem, QSizePolicy, QTabBar
)
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView

class WebViewerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setStyleSheet("background-color: #F8F9FA;")  # Use the same background color
        
        self.layout = QVBoxLayout(self)
        
        # Create a custom profile for this tab
        self.profile = QWebEngineProfile()
        
        # Create browser instance with the custom profile
        self.browser = QWebEngineView()
        self.browser.setPage(QWebEnginePage(self.profile, self.browser))
        self.layout.addWidget(self.browser)
        
        # Create button panel
        self.button_panel = QHBoxLayout()
        self.layout.addLayout(self.button_panel)
        
        # Back button
        self.back_button = QPushButton("←")
        self.back_button.setStyleSheet("""
            background-color: #FF0000; 
            color: #FFFFFF; 
            border: none; 
            padding: 10px; 
            border-radius: 5px; 
            font-size: 14px;
            font-weight: bold;
        """)
        self.back_button.clicked.connect(self.browser.back)
        self.button_panel.addWidget(self.back_button)
        
        # Forward button
        self.forward_button = QPushButton("→")
        self.forward_button.setStyleSheet("""
            background-color: #FF0000; 
            color: #FFFFFF; 
            border: none; 
            padding: 10px; 
            border-radius: 5px; 
            font-size: 14px;
            font-weight: bold;
        """)
        self.forward_button.clicked.connect(self.browser.forward)
        self.button_panel.addWidget(self.forward_button)
        
        # Reload button
        self.reload_button = QPushButton("⟳")
        self.reload_button.setStyleSheet("""
            background-color: #FF0000; 
            color: #FFFFFF; 
            border: none; 
            padding: 10px; 
            border-radius: 5px; 
            font-size: 14px;
            font-weight: bold;
        """)
        self.reload_button.clicked.connect(self.browser.reload)
        self.button_panel.addWidget(self.reload_button)
        
        # Load URL button
        self.load_button = QPushButton("Load URL")
        self.load_button.setStyleSheet("""
            background-color: #FF0000; 
            color: #FFFFFF; 
            border: none; 
            padding: 10px; 
            border-radius: 5px; 
            font-size: 14px;
            font-weight: bold;
        """)
        self.load_button.clicked.connect(self.load_url)
        self.button_panel.addWidget(self.load_button)

        # Connect signals
        self.browser.urlChanged.connect(self.update_buttons)
        self.browser.loadFinished.connect(self.update_buttons)
        self.browser.page().linkHovered.connect(self.update_buttons)

        self.update_buttons()  # Initial update

    def load_url(self):
        url, ok = QInputDialog.getText(self, 'Load URL', 'Enter URL:')
        if ok and url:
            self.browser.setUrl(QUrl(url))

    def update_buttons(self):
        history = self.browser.history()
        self.back_button.setEnabled(history.canGoBack())
        self.forward_button.setEnabled(history.canGoForward())

class HalfButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 60)  # Adjust size for better visibility

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self.palette().button())
        painter.setPen(Qt.PenStyle.NoPen)

        # Draw the full button area
        painter.drawRect(self.rect())

        # Create a mask that only keeps the right half of the button
        region = QRegion(self.rect().adjusted(0, 0, -self.width() // 2, 0))
        painter.setClipRegion(region)

        # Draw the button's contents in the visible region
        super().paintEvent(event)

class CustomTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)  # Allow tabs to be closable
        self.tabCloseRequested.connect(self.close_tab)  # Connect close request signal

    def close_tab(self, index):
        self.parent().removeTab(index)

    def tabButton(self, index, position):
        if position == QTabBar.ButtonPosition.RightSide:
            button = QPushButton()  # Create a new QPushButton for the close tab button
            button.setIcon(QIcon('background/close_icon.png'))  # Set the icon
            button.setIconSize(QSize(16, 16))  # Adjust the icon size as needed
            button.setStyleSheet("""
                QPushButton {
                    background-color: transparent; 
                    border: none; 
                    width: 20px; 
                    height: 20px;
                }
                QPushButton:hover {
                    background-color: #CC0000;
                }
                QPushButton:pressed {
                    background-color: #990000;
                }
            """)
            button.clicked.connect(lambda: self.close_tab(index))  # Connect button click to close tab
            return button
        return None  # Ensure no default button is returned

class Sidebar(QWidget):
    themeChangeRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setStyleSheet("background-color: #333333;")  # Dark background for sidebar
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Create a button to change the theme
        self.theme_button = QPushButton("Theme")
        self.theme_button.setStyleSheet("""
            background-color: #FF0000; 
            color: #FFFFFF; 
            border: none; 
            padding: 10px; 
            border-radius: 5px; 
            font-size: 14px;
            font-weight: bold;
        """)
        self.theme_button.clicked.connect(self.toggle_theme)
        self.layout.addWidget(self.theme_button)
        
        # Create a spacer to push content to the top
        self.spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.layout.addItem(self.spacer)

    def toggle_theme(self):
        self.themeChangeRequested.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.is_light_theme = True  # Track the current theme

    def initUI(self):
        self.setWindowTitle('Alpha Hub')
        self.setGeometry(100, 100, 800, 600)

        self.setWindowIcon(QIcon('background/icon.png'))

        # Create central widget and layout
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        
        # Create tab widget with custom tab bar
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabBar(CustomTabBar(self.tab_widget))  # Set custom tab bar
        central_layout.addWidget(self.tab_widget)
        
        # Change New Tab button color to black
        self.add_tab_button = QPushButton("New Tab")
        self.add_tab_button.setStyleSheet("""
            background-color: #000000; 
            color: #FFFFFF; 
            border: none; 
            padding: 10px; 
            border-radius: 5px; 
            font-size: 14px;
            font-weight: bold;
        """)
        self.add_tab_button.clicked.connect(self.add_new_tab)
        central_layout.addWidget(self.add_tab_button)

        # Create the sidebar and add it to the layout
        self.sidebar = Sidebar(self)
        self.sidebar.themeChangeRequested.connect(self.toggle_theme)  # Connect the signal to the slot

        # Create a button to toggle the sidebar visibility
        self.sidebar_toggle_button = HalfButton()
        self.sidebar_toggle_button.setStyleSheet("""
            background-color: #FF0000;
            border: none;
            border-radius: 15px;
        """)
        self.sidebar_toggle_button.clicked.connect(self.toggle_sidebar)

        # Create layout for the main window
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(central_widget)
        
        # Create a wrapper widget to hold the layout
        wrapper_widget = QWidget()
        wrapper_widget.setLayout(main_layout)

        # Create a container layout for the sidebar button and the main content
        container_layout = QHBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.sidebar_toggle_button, alignment=Qt.AlignmentFlag.AlignLeft)
        container_layout.addWidget(wrapper_widget)

        # Set the final layout
        final_widget = QWidget()
        final_widget.setLayout(container_layout)
        self.setCentralWidget(final_widget)

        # Adjust the position of the sidebar toggle button to be partially hidden
        self.sidebar_toggle_button.move(-15, 0)  # Adjust position to partially hide it
        
        # Ensure the main content area does not get affected
        self.sidebar.setFixedWidth(100)  # Adjust the width of the sidebar as needed

        # Add an initial tab
        self.add_new_tab()

        # Initially hide the sidebar
        self.sidebar.setVisible(False)
        self.sidebar_toggle_button.setText(">")

        # Set the tab bar style
        self.set_tab_bar_style()

    def add_new_tab(self):
        new_tab = WebViewerTab()
        tab_index = self.tab_widget.addTab(new_tab, f"Tab {self.tab_widget.count() + 1}")
        self.tab_widget.setCurrentIndex(tab_index)
        # Set the URL to Google
        new_tab.browser.setUrl(QUrl("https://www.google.com"))

    def toggle_theme(self):
        if self.is_light_theme:
            self.setStyleSheet("""
                QWidget {
                    background-color: #2E2E2E;
                    color: #FFFFFF;
                }
                QPushButton {
                    background-color: #FF0000;
                    color: #FFFFFF;
                }
                QTabWidget::pane {
                    border: 1px solid #444;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background-color: #F8F9FA;
                    color: #000000;
                }
                QPushButton {
                    background-color: #FF0000;
                    color: #FFFFFF;
                }
                QTabWidget::pane {
                    border: 1px solid #CCC;
                }
            """)
        self.is_light_theme = not self.is_light_theme
        self.set_tab_bar_style()

    def set_tab_bar_style(self):
        # Set the tab bar color to red
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #FF0000;
            }
            QTabBar::tab {
                background-color: #FF0000;
                color: #FFFFFF;
                padding: 5px;
                border: 1px solid #FF0000;
                border-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #CC0000;
            }
        """)

    def toggle_sidebar(self):
        if self.sidebar.isVisible():
            self.sidebar.setVisible(False)
            self.sidebar_toggle_button.setText(">")
        else:
            self.sidebar.setVisible(True)
            self.sidebar_toggle_button.setText("<")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec())
