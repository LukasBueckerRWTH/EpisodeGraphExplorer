from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal

class WrappingButton(QFrame):
    clicked = pyqtSignal(bool)
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setObjectName("wrappingButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checkable = False
        self._checked = False
        self._label = QLabel(text)
        self._label.setWordWrap(True)
        self._label.setObjectName("wrappingButtonLabel")
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.addWidget(self._label)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def setText(self, text):
        self._label.setText(text)

    def text(self):
        return self._label.text()

    def setCheckable(self, value):
        self._checkable = bool(value)

    def isCheckable(self):
        return self._checkable

    def setChecked(self, value):
        self._checked = bool(value) if self._checkable else False
        self._refresh_state()

    def isChecked(self):
        return self._checked

    def setMinimumHeight(self, h):
        super().setMinimumHeight(h)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._checkable:
                self.setChecked(not self._checked)
            self.clicked.emit(self._checked)
        super().mousePressEvent(event)

    def _refresh_state(self):
        self.setProperty("checked", self._checked)
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self.update()