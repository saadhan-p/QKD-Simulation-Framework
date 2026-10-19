# client/toast_notification.py
"""
Modern toast notification system
"""
from PyQt5.QtWidgets import QLabel, QGraphicsOpacityEffect
from PyQt5.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont


class ToastNotification(QLabel):
    """Modern toast notification widget"""
    
    def __init__(self, message, toast_type="info", parent=None):
        super().__init__(message, parent)
        self.toast_type = toast_type
        
        # Styling based on type
        self._apply_style()
        
        # Setup fade effect
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        # Setup animations
        self._setup_animations()
        
        # Auto-dismiss timer
        self.dismiss_timer = QTimer(self)
        self.dismiss_timer.setSingleShot(True)
        self.dismiss_timer.timeout.connect(self.hide_toast)
        
    def _apply_style(self):
        """Apply styling based on toast type"""
        font = QFont('Inter', 13, QFont.Medium)
        self.setFont(font)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setMinimumWidth(280)
        self.setMaximumWidth(400)
        
        if self.toast_type == "success":
            self.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                stop:0 #06FFA5, stop:1 #059669);
                    color: white;
                    border-radius: 12px;
                    padding: 16px 24px;
                    border: 2px solid rgba(6, 255, 165, 0.3);
                }
            """)
            icon = "✅ "
        elif self.toast_type == "error":
            self.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                stop:0 #E71D36, stop:1 #DC2626);
                    color: white;
                    border-radius: 12px;
                    padding: 16px 24px;
                    border: 2px solid rgba(231, 29, 54, 0.3);
                }
            """)
            icon = "❌ "
        elif self.toast_type == "warning":
            self.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                stop:0 #FCA311, stop:1 #F59E0B);
                    color: white;
                    border-radius: 12px;
                    padding: 16px 24px;
                    border: 2px solid rgba(252, 163, 17, 0.3);
                }
            """)
            icon = "⚠️ "
        else:  # info
            self.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                stop:0 #4CC9F0, stop:1 #3A86FF);
                    color: white;
                    border-radius: 12px;
                    padding: 16px 24px;
                    border: 2px solid rgba(76, 201, 240, 0.3);
                }
            """)
            icon = "ℹ️ "
        
        # Prepend icon to text
        current_text = self.text()
        if not current_text.startswith(icon):
            self.setText(icon + current_text)
    
    def _setup_animations(self):
        """Setup slide and fade animations"""
        # Slide in animation
        self.slide_in = QPropertyAnimation(self, b"geometry")
        self.slide_in.setDuration(400)
        self.slide_in.setEasingCurve(QEasingCurve.OutCubic)
        
        # Fade in animation
        self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in.setDuration(300)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        
        # Fade out animation
        self.fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out.setDuration(300)
        self.fade_out.setStartValue(1.0)
        self.fade_out.setEndValue(0.0)
        self.fade_out.finished.connect(self.deleteLater)
    
    def show_toast(self, duration=3000):
        """Show toast with animations"""
        parent = self.parent()
        if not parent:
            return
        
        # Position at top-right
        self.adjustSize()
        parent_width = parent.width()
        parent_height = parent.height()
        
        x_end = parent_width - self.width() - 20
        y_end = 20
        
        # Start position (off-screen top)
        x_start = x_end
        y_start = -self.height() - 20
        
        # Setup slide animation
        from PyQt5.QtCore import QRect
        self.slide_in.setStartValue(QRect(x_start, y_start, self.width(), self.height()))
        self.slide_in.setEndValue(QRect(x_end, y_end, self.width(), self.height()))
        
        # Show and animate
        self.show()
        self.raise_()
        self.slide_in.start()
        self.fade_in.start()
        
        # Auto-dismiss
        self.dismiss_timer.start(duration)
    
    def hide_toast(self):
        """Hide toast with fade out"""
        self.fade_out.start()


def show_toast(parent, message, toast_type="info", duration=3000):
    """Convenience function to show a toast"""
    toast = ToastNotification(message, toast_type, parent)
    toast.show_toast(duration)
    return toast
