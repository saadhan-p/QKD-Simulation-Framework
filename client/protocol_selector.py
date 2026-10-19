# client/protocol_selector.py
"""
Visual protocol selector with cards
"""
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class ProtocolCard(QPushButton):
    """Single protocol card button"""
    
    def __init__(self, protocol_name, efficiency, description, parent=None):
        super().__init__(parent)
        self.protocol_name = protocol_name
        self.efficiency = efficiency
        self.is_active = False
        
        self.setCheckable(True)
        self.setFixedSize(180, 140)
        self.setCursor(Qt.PointingHandCursor)
        
        # Set text
        display_name = protocol_name.upper()
        self.setText(f"{display_name}\n\n{efficiency}\nEfficiency\n\n{description}")
        
        self.update_style()
        
    def update_style(self):
        """Update styling based on active state"""
        if self.is_active:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                stop:0 #4CC9F0, stop:1 #7209B7);
                    color: white;
                    border: 2px solid #06FFA5;
                    border-radius: 16px;
                    font-weight: 600;
                    font-size: 12px;
                    padding: 16px;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.08);
                    color: #4CC9F0;
                    border: 2px solid rgba(76, 201, 240, 0.3);
                    border-radius: 16px;
                    font-weight: 500;
                    font-size: 12px;
                    padding: 16px;
                }
                QPushButton:hover {
                    background: rgba(76, 201, 240, 0.15);
                    border: 2px solid #4CC9F0;
                }
            """)
    
    def setActive(self, active):
        """Set active state"""
        self.is_active = active
        self.setChecked(active)
        self.update_style()


class ProtocolSelector(QWidget):
    """Visual protocol selector with cards"""
    
    protocol_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards = {}
        self.current_protocol = "bb84"
        self._build_ui()
        
    def _build_ui(self):
        layout = QHBoxLayout()
        layout.setSpacing(16)
        
        # Protocol configurations
        protocols = [
            ("bb84", "~50%", "Classic"),
            ("sarg04", "~60%", "Enhanced"),
            ("aurora", "~45%", "Adaptive"),
            ("b92", "~25%", "Minimal"),
            ("e91", "~50%", "Entangled"),
        ]
        
        for protocol, efficiency, description in protocols:
            card = ProtocolCard(protocol, efficiency, description)
            card.clicked.connect(lambda checked, p=protocol: self._on_protocol_selected(p))
            self.cards[protocol] = card
            layout.addWidget(card)
        
        # Set initial selection
        self.cards[self.current_protocol].setActive(True)
        
        self.setLayout(layout)
    
    def _on_protocol_selected(self, protocol):
        """Handle protocol selection"""
        if protocol != self.current_protocol:
            # Deactivate previous
            self.cards[self.current_protocol].setActive(False)
            
            # Activate new
            self.current_protocol = protocol
            self.cards[protocol].setActive(True)
            
            # Emit signal
            self.protocol_changed.emit(protocol)
    
    def get_current_protocol(self):
        """Get currently selected protocol"""
        return self.current_protocol
    
    def set_protocol(self, protocol):
        """Programmatically set protocol"""
        if protocol in self.cards and protocol != self.current_protocol:
            self._on_protocol_selected(protocol)
