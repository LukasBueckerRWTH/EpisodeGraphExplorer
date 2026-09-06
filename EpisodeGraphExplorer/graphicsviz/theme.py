from dataclasses import dataclass
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

@dataclass(frozen=True)
class Theme:
    name: str

    # Surfaces
    bg_canvas: str          
    bg_panel: str           
    bg_panel_alt: str       
    bg_elevated: str        
    bg_input: str        

    # Borders & separators
    border: str
    border_strong: str

    # Text
    text_primary: str
    text_secondary: str
    text_muted: str
    text_on_accent: str

    # Accent (primary interactive color)
    accent: str
    accent_hover: str
    accent_pressed: str
    accent_soft: str 

    # Status
    danger: str
    danger_soft: str

    # Canvas: episode boxes
    episode_fill: str
    episode_border: str
    episode_border_selected: str

    # Canvas: activity nodes
    node_fill: str
    node_border: str
    node_border_structured: str
    node_text: str

    # Canvas: arrows / transitions
    arrow: str

    # Canvas: relation overlay (tau label backdrop, halo around lines)
    relation_label_bg: tuple  
    relation_halo: tuple 

    # Relation-type colors (Dependency / Co-occurrence / Exclusion)
    rel_dependency: str
    rel_cooccurrence: str
    rel_exclusion: str

    # Misc structural marks
    structured_mark: str

    def qcolor(self, role: str) -> QColor:
        return QColor(getattr(self, role))


LIGHT = Theme(
    name="light",

    bg_canvas="#ffffff",
    bg_panel="#f2f2f2",
    bg_panel_alt="#e6e6e6",
    bg_elevated="#ffffff",
    bg_input="#ffffff",

    border="#333333",
    border_strong="#000000",

    text_primary="#000000",
    text_secondary="#404040",
    text_muted="#737373",
    text_on_accent="#000000",

    accent="#5eead4",
    accent_hover="#2dd4bf",
    accent_pressed="#14b8a6",
    accent_soft="#f0fdfa",

    danger="#dc2626",
    danger_soft="#fee2e2",

    episode_fill="#ffffff",
    episode_border="#4f6df5",
    episode_border_selected="#f59e0b",

    node_fill="#ffffff",
    node_border="#d0d5dd",
    node_border_structured="#1aa15e",
    node_text="#1b1f24",

    arrow="#5b6472",

    relation_label_bg=(255, 255, 255, 225),
    relation_halo=(255, 255, 255, 220),

    rel_dependency="#e0524c",
    rel_cooccurrence="#4f6df5",
    rel_exclusion="#9b59b6",

    structured_mark="#1aa15e",
)


DARK = Theme(
    name="dark",

    bg_canvas="#181818",
    bg_panel="#0e0e0e",
    bg_panel_alt="#1c1c1c",
    bg_elevated="#222222",
    bg_input="#222222",

    border="#595959",
    border_strong="#f2f2f2",

    text_primary="#f2f2f2",
    text_secondary="#b3b3b3",
    text_muted="#808080",
    text_on_accent="#ffffff",

    accent="#0f766e",
    accent_hover="#14b8a6",
    accent_pressed="#115e59",
    accent_soft="#0f2e2b",

    danger="#f87171",
    danger_soft="#450a0a",

    episode_fill="#262b33",
    episode_border="#6c87ff",
    episode_border_selected="#f5a524",

    node_fill="#2f3540",
    node_border="#454c59",
    node_border_structured="#3ecf8e",
    node_text="#e7eaf0",

    arrow="#a7afbd",

    relation_label_bg=(24, 24, 24, 230),
    relation_halo=(24, 24, 24, 220),

    rel_dependency="#ec6a64",
    rel_cooccurrence="#7d96ff",
    rel_exclusion="#c084e8",

    structured_mark="#3ecf8e",
)


def _qt_reports_dark_scheme() -> bool:
    app = QApplication.instance()

    if app is not None:
        try:
            style_hints = app.styleHints()
            scheme = style_hints.colorScheme()
            if scheme is not None and int(scheme.value) == 2:
                return True
            if scheme is not None and int(scheme.value) == 1:
                return False
        except Exception:
            pass

    try:
        palette = app.palette() if app is not None else QPalette()
        bg = palette.color(QPalette.ColorRole.Window)
        fg = palette.color(QPalette.ColorRole.WindowText)
        return bg.lightness() < fg.lightness()
    except Exception:
        return False


def detect_theme() -> Theme:
    return DARK if _qt_reports_dark_scheme() else LIGHT


def build_stylesheet(theme: Theme) -> str:
    return f"""
    QWidget {{
        background-color: {theme.bg_panel};
        color: {theme.text_primary};
        font-size: 12.5px;
    }}

    QWidget#leftPanel {{
        background-color: {theme.bg_panel};
        border: none;
        border-right: 1px solid {theme.border};
    }}

    QWidget#rightPanel {{
        background-color: {theme.bg_panel};
        border: none;
        border-left: 1px solid {theme.border};
    }}

    QLabel {{
        color: {theme.text_secondary};
        background: transparent;
    }}

    QLabel#panelTitle {{
        color: {theme.text_primary};
        font-size: 13.5px;
        font-weight: 600;
        padding: 4px 2px 8px 2px;
    }}

    QPushButton {{
        background-color: {theme.bg_elevated};
        color: {theme.text_primary};
        border: 1px solid {theme.border};
        border-radius: 0px;
        padding: 7px 12px;
        text-align: left;
    }}

    QPushButton:hover {{
        background-color: {theme.accent_soft};
        border-color: {theme.accent};
    }}

    QPushButton:pressed {{
        background-color: {theme.accent_soft};
        border-color: {theme.accent_pressed};
    }}

    QPushButton:checkable:checked {{
        background-color: {theme.accent};
        color: {theme.text_on_accent};
        border-color: {theme.accent};
        font-weight: 600;
    }}

    QPushButton:checkable:checked:hover {{
        background-color: {theme.accent_hover};
        color: {theme.text_on_accent};
    }}

    QPushButton#primaryButton {{
        background-color: {theme.accent};
        color: {theme.text_on_accent};
        border: 1px solid {theme.accent};
        font-weight: 600;
    }}

    QPushButton#primaryButton:hover {{
        background-color: {theme.accent_hover};
        color: {theme.text_on_accent};
    }}

    QPushButton#primaryButton:pressed {{
        background-color: {theme.accent_pressed};
        color: {theme.text_on_accent};
    }}

    QPushButton#dangerButton {{
        background-color: {theme.bg_elevated};
        color: {theme.danger};
        border: 1px solid {theme.danger};
    }}

    QPushButton#dangerButton:hover {{
        background-color: {theme.danger_soft};
    }}

    /* Word-wrapping relation buttons (see wrapping_button.py) */
    QFrame#wrappingButton {{
        background-color: {theme.bg_elevated};
        border: 1px solid {theme.border};
        border-radius: 0px;
    }}

    QFrame#wrappingButton:hover {{
        background-color: {theme.accent_soft};
        border-color: {theme.accent};
    }}

    QFrame#wrappingButton[checked="true"] {{
        background-color: {theme.accent};
        border-color: {theme.accent};
    }}

    QFrame#wrappingButton[checked="true"]:hover {{
        background-color: {theme.accent_hover};
    }}

    QLabel#wrappingButtonLabel {{
        background: transparent;
        color: {theme.text_primary};
        font-weight: 500;
    }}

    QFrame#wrappingButton[checked="true"] QLabel#wrappingButtonLabel {{
        color: {theme.text_on_accent};
        font-weight: 600;
    }}

    QPushButton#sectionToggle {{
        background-color: {theme.bg_panel_alt};
        border: 1px solid {theme.border};
        border-radius: 0px;
        padding: 9px 12px;
        font-weight: 600;
        color: {theme.text_primary};
        text-align: left;
    }}

    QPushButton#sectionToggle:hover {{
        border-color: {theme.border_strong};
    }}

    QPushButton#sectionToggle:checked {{
        background-color: {theme.bg_panel_alt};
        color: {theme.text_primary};
        border-color: {theme.border};
    }}

    QCheckBox {{
        color: {theme.text_secondary};
        spacing: 8px;
        padding: 2px 0;
    }}

    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 0px;
        border: 1.5px solid {theme.border_strong};
        background-color: {theme.bg_input};
    }}

    QCheckBox::indicator:hover {{
        border-color: {theme.accent};
    }}

    QCheckBox::indicator:checked {{
        background-color: {theme.accent};
        border-color: {theme.accent};
    }}

    QSlider::groove:horizontal {{
        height: 4px;
        background: {theme.border};
        border-radius: 0px;
    }}

    QSlider::sub-page:horizontal {{
        background: {theme.accent};
        border-radius: 0px;
    }}

    QSlider::handle:horizontal {{
        width: 14px;
        height: 14px;
        margin: -6px 0;
        border-radius: 0px;
        background: {theme.accent};
        border: 2px solid {theme.bg_panel};
    }}

    QSlider::handle:horizontal:hover {{
        background: {theme.accent_hover};
    }}

    QSlider::groove:vertical {{
        width: 4px;
        background: {theme.border};
        border-radius: 0px;
    }}

    QSlider::sub-page:vertical {{
        background: {theme.border};
        border-radius: 0px;
    }}

    QSlider::add-page:vertical {{
        background: {theme.accent};
        border-radius: 0px;
    }}

    QSlider::handle:vertical {{
        width: 14px;
        height: 14px;
        margin: 0 -6px;
        border-radius: 0px;
        background: {theme.accent};
        border: 2px solid {theme.bg_panel};
    }}

    QProgressBar {{
        background-color: {theme.bg_input};
        border: 1px solid {theme.border};
        border-radius: 0px;
        height: 14px;
        text-align: center;
        color: {theme.text_secondary};
    }}

    QProgressBar::chunk {{
        background-color: {theme.accent};
        border-radius: 0px;
    }}

    QToolTip {{
        background-color: {theme.bg_elevated};
        color: {theme.text_primary};
        border: 1px solid {theme.border};
        padding: 4px 6px;
        border-radius: 0px;
    }}

    QMessageBox {{
        background-color: {theme.bg_panel};
    }}

    QMessageBox QLabel {{
        color: {theme.text_primary};
    }}

    QDialog {{
        background-color: {theme.bg_panel};
    }}

    QScrollBar:vertical, QScrollBar:horizontal {{
        background: transparent;
        border: none;
    }}

    QScrollBar::handle {{
        background: {theme.border_strong};
        border-radius: 0px;
    }}

    QScrollBar::handle:hover {{
        background: {theme.text_muted};
    }}
    """