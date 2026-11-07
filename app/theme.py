"""Shared bone-white application theme."""

BONE_WHITE_QSS = r"""
/* PICTURE TO 3D STUDIO - BONE WHITE THEME */

QMainWindow, QDialog, QWidget {
    background-color: #F4F0E7;
    color: #292820;
    font-family: "Segoe UI";
    font-size: 10pt;
}

QLabel {
    color: #292820;
}

QLabel#mainTitle, QLabel#title, QLabel#viewerTitle {
    color: #292820;
    font-size: 22pt;
    font-weight: 700;
}

QLabel#subtitle, QLabel#viewerSubtitle {
    color: #777164;
    font-size: 9pt;
}

QLabel#engineBadge, QLabel#statusBadge {
    background-color: #E9E0D2;
    color: #805438;
    border: 1px solid #CDBBA3;
    border-radius: 6px;
    padding: 8px 12px;
    font-weight: 700;
}

QGroupBox {
    background-color: #FAF7F0;
    border: 1px solid #D8CEBE;
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px;
    color: #51483D;
    font-weight: 700;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 5px;
    color: #8A5A3C;
}

QLabel#imagePreview, QLabel#preview {
    background-color: #EEE9DF;
    border: 1px dashed #C8BBA8;
    border-radius: 6px;
    color: #81796C;
    padding: 10px;
}

QLabel#infoText {
    color: #514B41;
}

QLabel#mutedText, QLabel#Muted {
    color: #777164;
}

QLabel#status {
    color: #805438;
}

QLabel#viewerMessage {
    color: #777164;
    font-size: 11pt;
    padding: 25px;
}

QPushButton {
    background-color: #E9E2D7;
    color: #292820;
    border: 1px solid #CFC3B2;
    border-radius: 5px;
    padding: 7px 10px;
    min-height: 18px;
    font-family: "Segoe UI";
    font-size: 9pt;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #DED3C3;
    border-color: #A98A6B;
}

QPushButton:pressed {
    background-color: #D4C6B3;
}

QPushButton:disabled {
    background-color: #EAE6DE;
    color: #756D61;
    border-color: #DDD6CA;
}

QPushButton#primaryButton, QPushButton#Primary {
    background-color: #8A5A3C;
    color: #FFFDF8;
    border: 1px solid #75472F;
    font-weight: 700;
}

QPushButton#primaryButton:hover, QPushButton#Primary:hover {
    background-color: #70452E;
}

QPushButton#secondaryButton {
    background-color: #E5DED2;
    color: #62594D;
}

QLineEdit, QTextEdit, QPlainTextEdit,
QListWidget, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #FFFCF6;
    color: #292820;
    border: 1px solid #D2C7B7;
    border-radius: 5px;
    padding: 7px;
    selection-background-color: #B88A68;
    selection-color: #FFFFFF;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #A87957;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #FFFCF6;
    color: #292820;
    border: 1px solid #D2C7B7;
    selection-background-color: #E9D9C8;
    selection-color: #292820;
}

QCheckBox, QRadioButton {
    color: #403A31;
    spacing: 7px;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 15px;
    height: 15px;
}

QProgressBar {
    background-color: #E8E1D6;
    color: #51483D;
    border: 1px solid #D2C7B7;
    border-radius: 5px;
    text-align: center;
    min-height: 10px;
}

QProgressBar::chunk {
    background-color: #A87957;
    border-radius: 4px;
}

QFrame#viewerFrame {
    background-color: #EEE9DF;
    border: 1px solid #D8CEBE;
    border-radius: 8px;
}

QTextEdit {
    font-family: Consolas;
}

QStatusBar {
    background-color: #EAE4D9;
    color: #777164;
    border-top: 1px solid #D8CEBE;
}

QSplitter::handle {
    background-color: #D6CBBB;
    width: 3px;
}

QScrollBar:vertical {
    background-color: #EEE9DF;
    width: 12px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background-color: #C9BBA8;
    border-radius: 5px;
    min-height: 25px;
}

QScrollBar::handle:vertical:hover {
    background-color: #A98A6B;
}

QScrollBar:horizontal {
    background-color: #EEE9DF;
    height: 12px;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    background-color: #C9BBA8;
    border-radius: 5px;
    min-width: 25px;
}

QToolTip {
    background-color: #FFFCF6;
    color: #292820;
    border: 1px solid #CFC3B2;
    padding: 5px;
}

QMenu {
    background-color: #FFFCF6;
    color: #292820;
    border: 1px solid #D2C7B7;
}

QMenu::item:selected {
    background-color: #E9D9C8;
}
"""

def apply_bone_white_theme(widget):
    widget.setStyleSheet(BONE_WHITE_QSS)

