from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt

class CollapsibleSection(QWidget):

    COLLAPSED_GLYPH = "\u203a"   # ›
    EXPANDED_GLYPH = "\u2304"    # ⌄

    def __init__(self, title):
        super().__init__()

        self._title = title

        self.toggle = QPushButton()
        self.toggle.setObjectName("sectionToggle")
        self.toggle.setCheckable(True)
        self.toggle.setChecked(True)
        self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle.setMinimumHeight(32)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(12, 8, 4, 10)
        self.content_layout.setSpacing(8)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toggle)
        layout.addWidget(self.content)

        self.toggle.clicked.connect(self.toggle_content)
        self._update_label()

    def _update_label(self):
        glyph = self.EXPANDED_GLYPH if self.toggle.isChecked() else self.COLLAPSED_GLYPH
        self.toggle.setText(f"{glyph}  {self._title}")

    def toggle_content(self):
        self.content.setVisible(self.toggle.isChecked())
        self._update_label()