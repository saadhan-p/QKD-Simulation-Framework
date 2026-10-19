# client/theme.py
# KeyForge - Modern Dark Theme with Orange Accents (matching HTML design)

class Colors:
    # Background - Deep neutral blacks
    BG_PRIMARY = "#0d0d0d"
    BG_SECONDARY = "#161616"
    BG_TERTIARY = "#1f1f1f"
    BG_CARD = "#1a1a1a"
    BG_HOVER = "#242424"
    
    # Text
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#b3b3b3"
    TEXT_TERTIARY = "#808080"
    
    # Border
    BORDER = "#2a2a2a"
    BORDER_LIGHT = "#333333"
    
    # Brand Colors - Orange/Coral Accents
    ACCENT_PRIMARY = "#ff6b35"
    ACCENT_SECONDARY = "#ff8c42"
    
    # Status Colors
    ACCENT_SUCCESS = "#00d9a3"
    ACCENT_WARNING = "#ffa500"
    ACCENT_DANGER = "#ff4757"
    ACCENT_INFO = "#4a90e2"
    
    # Gradients
    GRADIENT_PRIMARY = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff6b35, stop:1 #ff8c42)"
    GRADIENT_CARD = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(255, 107, 53, 0.1), stop:1 rgba(255, 140, 66, 0.1))"

NEW_DARK_THEME = f"""
/* Global */
QWidget {{
    background-color: {Colors.BG_PRIMARY};
    color: {Colors.TEXT_PRIMARY};
    font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
    font-size: 14px;
}}

/* Header */
#header_title {{
    font-size: 28px;
    font-weight: 800;
    color: {Colors.ACCENT_PRIMARY};
}}

#status_badge {{
    color: {Colors.ACCENT_SUCCESS};
    font-size: 13px;
    font-weight: 600;
    padding: 6px 12px;
    background: rgba(0, 217, 163, 0.15);
    border-radius: 20px;
    border: 1px solid {Colors.ACCENT_SUCCESS};
}}

/* Stats */
#stat_label {{
    color: {Colors.TEXT_TERTIARY};
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.2px;
}}

#stat_value {{
    color: {Colors.ACCENT_PRIMARY};
    font-size: 24px;
    font-weight: 800;
}}

/* Control Panel - Glassmorphism */
#control_panel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                stop:0 rgba(26, 26, 26, 0.9), 
                                stop:1 rgba(22, 22, 22, 0.9));
    border: 1px solid {Colors.BORDER};
    border-radius: 16px;
    padding: 24px;
}}

/* Input Fields */
QLineEdit {{
    background: {Colors.BG_SECONDARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
    padding: 12px 16px;
    color: {Colors.TEXT_PRIMARY};
    font-size: 14px;
    font-family: 'JetBrains Mono', 'SF Mono', 'Monaco', monospace;
    min-height: 42px;
}}

QLineEdit:focus {{
    border: 1px solid {Colors.ACCENT_PRIMARY};
    background: rgba(255, 107, 53, 0.05);
}}

QLineEdit:hover {{
    border: 1px solid {Colors.BORDER_LIGHT};
}}

QComboBox {{
    background: {Colors.BG_SECONDARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
    padding: 12px 16px;
    color: {Colors.TEXT_PRIMARY};
    min-height: 42px;
    font-weight: 600;
}}

QComboBox:hover {{
    border: 1px solid {Colors.BORDER_LIGHT};
}}

QComboBox:focus {{
    border: 1px solid {Colors.ACCENT_PRIMARY};
}}

QComboBox::drop-down {{
    border: none;
    width: 35px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 7px solid {Colors.ACCENT_PRIMARY};
    margin-right: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.ACCENT_PRIMARY};
    border-radius: 10px;
    selection-background-color: {Colors.ACCENT_PRIMARY};
    selection-color: #ffffff;
    padding: 6px;
}}

/* Buttons - Orange gradient theme */
QPushButton {{
    border-radius: 10px;
    padding: 14px 28px;
    font-weight: 700;
    font-size: 14px;
    min-height: 48px;
    letter-spacing: 0.5px;
}}

#btn_primary {{
    background: {Colors.GRADIENT_PRIMARY};
    color: #ffffff;
    border: none;
}}

#btn_primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff5a24, stop:0.5 #ff7b31, stop:1 #ff9d52);
}}

#btn_primary:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #e65020, stop:1 #e67a2e);
}}

#btn_primary:disabled {{
    background: {Colors.BG_CARD};
    color: {Colors.TEXT_TERTIARY};
}}

#btn_secondary {{
    background: {Colors.BG_SECONDARY};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
}}

#btn_secondary:hover {{
    background: {Colors.BG_HOVER};
    border: 1px solid {Colors.ACCENT_PRIMARY};
}}

#btn_danger {{
    background: rgba(255, 71, 87, 0.1);
    color: {Colors.ACCENT_DANGER};
    border: 1px solid rgba(255, 71, 87, 0.2);
}}

#btn_danger:hover {{
    background: rgba(255, 71, 87, 0.2);
}}

#btn_danger:disabled {{
    background: {Colors.BG_CARD};
    color: {Colors.TEXT_TERTIARY};
}}

/* Cards - Glassmorphism with orange glow */
#card {{
    background: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 16px;
    padding: 24px;
}}

#card:hover {{
    border: 1px solid {Colors.ACCENT_PRIMARY};
}}

/* Progress Bar - Orange gradient */
QProgressBar {{
    background: {Colors.BG_SECONDARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
    text-align: center;
    height: 10px;
    font-weight: 700;
    color: {Colors.TEXT_PRIMARY};
}}

QProgressBar::chunk {{
    background: {Colors.GRADIENT_PRIMARY};
    border-radius: 8px;
}}

/* List Widget */
QListWidget {{
    background: {Colors.BG_SECONDARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 12px;
    padding: 10px;
}}

QListWidget::item {{
    padding: 14px;
    border-radius: 10px;
    color: {Colors.TEXT_PRIMARY};
    margin: 4px 0;
    background: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
}}

QListWidget::item:selected {{
    background: {Colors.GRADIENT_PRIMARY};
    color: #ffffff;
    font-weight: 600;
    border: 1px solid {Colors.ACCENT_PRIMARY};
}}

QListWidget::item:hover {{
    background: {Colors.BG_HOVER};
    border: 1px solid {Colors.ACCENT_PRIMARY};
}}

/* Tabs - Modern with orange accents */
QTabWidget::pane {{
    border: 1px solid {Colors.BORDER};
    border-radius: 12px;
    background: rgba(26, 26, 26, 0.5);
    padding: 20px;
}}

QTabBar::tab {{
    background: {Colors.BG_SECONDARY};
    color: {Colors.TEXT_SECONDARY};
    padding: 14px 28px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    margin-right: 6px;
    font-weight: 700;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

QTabBar::tab:selected {{
    background: {Colors.GRADIENT_PRIMARY};
    color: #ffffff;
}}

QTabBar::tab:hover {{
    background: rgba(255, 107, 53, 0.1);
    color: {Colors.ACCENT_PRIMARY};
}}

/* Text Edit - Terminal style with orange accents */
QTextEdit {{
    background: rgba(13, 13, 13, 0.95);
    border: 1px solid {Colors.BORDER};
    border-radius: 12px;
    padding: 16px;
    color: {Colors.ACCENT_PRIMARY};
    font-family: 'JetBrains Mono', 'SF Mono', 'Monaco', 'Consolas', monospace;
    font-size: 13px;
    line-height: 1.6;
}}

/* Frame */
QFrame#panel {{
    background: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 12px;
}}

/* Scrollbar - Sleek with orange */
QScrollBar:vertical {{
    background: {Colors.BG_SECONDARY};
    width: 8px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: {Colors.GRADIENT_PRIMARY};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff7b31, stop:1 #ff9d52);
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: {Colors.BG_SECONDARY};
    height: 8px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background: {Colors.GRADIENT_PRIMARY};
    border-radius: 4px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff7b31, stop:1 #ff9d52);
}}

/* Plot Widget (PyQtGraph) */
QGraphicsView {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 16px;
}}
"""
