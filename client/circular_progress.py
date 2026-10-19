# client/circular_progress.py
"""
Custom circular progress widget with modern styling
"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRect, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QConicalGradient, QFont


class CircularProgress(QWidget):
    """Modern circular progress ring widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.max_value = 100
        self.setMinimumSize(120, 120)
        
    def setValue(self, value):
        """Set the current progress value"""
        self.value = max(0, min(value, self.max_value))
        self.update()
        
    def setMaximum(self, maximum):
        """Set the maximum value"""
        self.max_value = maximum
        self.update()
        
    def paintEvent(self, event):
        """Custom paint event for circular progress"""
        width = self.width()
        height = self.height()
        size = min(width, height)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Center the circle
        rect = QRect(
            (width - size) // 2 + 10,
            (height - size) // 2 + 10,
            size - 20,
            size - 20
        )
        
        # Background circle (track)
        painter.setPen(QPen(QColor(255, 255, 255, 20), 8, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, 0, 360 * 16)
        
        # Progress arc with gradient
        if self.value > 0:
            gradient = QConicalGradient(rect.center(), -90)
            gradient.setColorAt(0.0, QColor(0, 229, 255))     # Cyan
            gradient.setColorAt(1.0, QColor(0, 184, 212))     # Darker Cyan
            
            pen = QPen(gradient, 8, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen)
            
            # Draw arc (angle in 16ths of a degree)
            span_angle = int((self.value / self.max_value) * 360 * 16)
            painter.drawArc(rect, 90 * 16, -span_angle)
        
        # Draw percentage text in center
        painter.setPen(QColor(248, 249, 250))
        font = QFont('JetBrains Mono', 24, QFont.Bold)
        painter.setFont(font)
        text = f"{int((self.value / self.max_value) * 100)}%"
        painter.drawText(rect, Qt.AlignCenter, text)
