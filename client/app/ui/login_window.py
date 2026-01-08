"""
Login Window

Authentication screen for the application.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame, QCheckBox, QSpacerItem,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QPixmap

from app.config import settings
from app.api import api_client, APIError


class LoginThread(QThread):
    """Background thread for login operation."""
    
    success = Signal(dict)
    error = Signal(str)
    
    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.password = password
    
    def run(self):
        try:
            result = api_client.login(self.username, self.password)
            user = api_client.get_current_user()
            self.success.emit(user)
        except APIError as e:
            self.error.emit(e.message)
        except Exception as e:
            self.error.emit(str(e))


class LoginWindow(QWidget):
    """Login window for user authentication."""
    
    login_successful = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self._login_thread: LoginThread = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the login UI."""
        self.setWindowTitle(f"{settings.APP_NAME} - Login")
        self.setFixedSize(400, 500)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Logo/Title area
        title_label = QLabel(settings.APP_NAME)
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        layout.addWidget(title_label)
        
        subtitle_label = QLabel("Point of Sale System")
        subtitle_label.setObjectName("subtitle")
        subtitle_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle_label)
        
        layout.addSpacing(20)
        
        # Login Form Card
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)
        
        # Server URL
        server_label = QLabel("Server")
        self.server_input = QLineEdit()
        self.server_input.setText(settings.SERVER_URL)
        self.server_input.setPlaceholderText("http://localhost:8000")
        card_layout.addWidget(server_label)
        card_layout.addWidget(self.server_input)
        
        # Username
        username_label = QLabel("Username")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        card_layout.addWidget(username_label)
        card_layout.addWidget(self.username_input)
        
        # Password
        password_label = QLabel("Password")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        card_layout.addWidget(password_label)
        card_layout.addWidget(self.password_input)
        
        # Remember me
        self.remember_checkbox = QCheckBox("Remember me")
        card_layout.addWidget(self.remember_checkbox)
        
        # Login button
        self.login_button = QPushButton("Login")
        self.login_button.setObjectName("primary")
        self.login_button.setMinimumHeight(44)
        self.login_button.clicked.connect(self._on_login)
        card_layout.addWidget(self.login_button)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #ff6b6b;")
        card_layout.addWidget(self.status_label)
        
        layout.addWidget(card)
        
        # Spacer
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Version
        version_label = QLabel(f"v{settings.APP_VERSION}")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #666666;")
        layout.addWidget(version_label)
        
        # Connect enter key
        self.password_input.returnPressed.connect(self._on_login)
        
        # Load saved credentials
        self._load_saved_credentials()
    
    def _load_saved_credentials(self):
        """Load saved credentials if any."""
        # TODO: Load from secure storage
        pass
    
    def _on_login(self):
        """Handle login button click."""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        server_url = self.server_input.text().strip()
        
        # Validation
        if not username:
            self._show_error("Please enter your username")
            self.username_input.setFocus()
            return
        
        if not password:
            self._show_error("Please enter your password")
            self.password_input.setFocus()
            return
        
        # Update server URL
        settings.SERVER_URL = server_url
        api_client.base_url = f"{server_url}/api/v1"
        
        # Disable inputs
        self._set_loading(True)
        self.status_label.setText("Connecting...")
        self.status_label.setStyleSheet("color: #888888;")
        
        # Start login thread
        self._login_thread = LoginThread(username, password)
        self._login_thread.success.connect(self._on_login_success)
        self._login_thread.error.connect(self._on_login_error)
        self._login_thread.start()
    
    def _on_login_success(self, user: dict):
        """Handle successful login."""
        self._set_loading(False)
        self.status_label.setText("")
        
        # Save credentials if remember me
        if self.remember_checkbox.isChecked():
            # TODO: Save to secure storage
            pass
        
        # Open main window
        from app.ui.main_window import MainWindow
        self.main_window = MainWindow(user)
        self.main_window.show()
        self.close()
    
    def _on_login_error(self, error: str):
        """Handle login error."""
        self._set_loading(False)
        self._show_error(error)
    
    def _show_error(self, message: str):
        """Show error message."""
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #ff6b6b;")
    
    def _set_loading(self, loading: bool):
        """Set loading state."""
        self.login_button.setEnabled(not loading)
        self.username_input.setEnabled(not loading)
        self.password_input.setEnabled(not loading)
        self.server_input.setEnabled(not loading)
        
        if loading:
            self.login_button.setText("Logging in...")
        else:
            self.login_button.setText("Login")
