from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtCore import Qt


class ZoomableGraphicsView(QGraphicsView):

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(self.renderHints())
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._zoom = 0
        self._zoom_step = 0.15
        self._zoom_range = (-10, 20)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                zoom_factor = 1 + self._zoom_step
                self._zoom += 1
            else:
                zoom_factor = 1 - self._zoom_step
                self._zoom -= 1

            if self._zoom_range[0] <= self._zoom <= self._zoom_range[1]:
                self.scale(zoom_factor, zoom_factor)
            else:
                self._zoom -= 1 if delta > 0 else -1
        else:
            super().wheelEvent(event)