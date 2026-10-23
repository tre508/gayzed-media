def get_stylesheet() -> str:
    return r'''
QWidget {
    color: #f6f7ff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(12, 8, 30, 245),
        stop:0.25 rgba(18, 12, 44, 245),
        stop:0.5 rgba(10, 24, 42, 245),
        stop:0.75 rgba(36, 12, 48, 245),
        stop:1 rgba(8, 10, 30, 245));
    font-size: 13px;
}

QMainWindow, QTabWidget::pane, QGroupBox, QPlainTextEdit, QTextEdit,
QLineEdit, QTableWidget, QComboBox, QSpinBox {
    background: rgba(255, 255, 255, 18);
    border: 1px solid rgba(255, 255, 255, 55);
    border-radius: 18px;
}

QGroupBox {
    margin-top: 10px;
    padding: 16px;
    font-weight: 700;
    border: 1px solid rgba(255, 255, 255, 70);
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #9ffcff;
}

QPushButton {
    color: white;
    font-weight: 700;
    padding: 10px 16px;
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,80);
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(255, 0, 128, 125),
        stop:0.2 rgba(255, 136, 0, 125),
        stop:0.4 rgba(255, 255, 0, 125),
        stop:0.6 rgba(0, 255, 153, 125),
        stop:0.8 rgba(0, 200, 255, 125),
        stop:1 rgba(166, 0, 255, 125));
}

QPushButton:hover {
    border: 1px solid rgba(255,255,255,150);
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(255, 0, 128, 180),
        stop:0.2 rgba(255, 136, 0, 180),
        stop:0.4 rgba(255, 255, 0, 180),
        stop:0.6 rgba(0, 255, 153, 180),
        stop:0.8 rgba(0, 200, 255, 180),
        stop:1 rgba(166, 0, 255, 180));
}

QPushButton:pressed {
    background: rgba(255,255,255,55);
}

QHeaderView::section {
    background: rgba(255,255,255,30);
    color: #ffffff;
    border: none;
    padding: 8px;
    font-weight: 700;
}

QTableWidget {
    gridline-color: rgba(255,255,255,35);
    selection-background-color: rgba(0, 255, 255, 55);
    alternate-background-color: rgba(255,255,255,8);
}

QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox {
    padding: 10px;
    selection-background-color: rgba(255, 0, 204, 80);
}

QProgressBar {
    border: 1px solid rgba(255,255,255,60);
    border-radius: 10px;
    background: rgba(255,255,255,15);
    text-align: center;
    min-height: 16px;
}

QProgressBar::chunk {
    border-radius: 9px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff0080,
        stop:0.2 #ff7b00,
        stop:0.4 #ffee00,
        stop:0.6 #00ff99,
        stop:0.8 #00d4ff,
        stop:1 #8a2eff);
}

QTabBar::tab {
    background: rgba(255,255,255,20);
    border: 1px solid rgba(255,255,255,45);
    border-radius: 14px;
    padding: 10px 16px;
    margin-right: 8px;
}

QTabBar::tab:selected {
    background: rgba(0,255,255,45);
    color: white;
}
'''