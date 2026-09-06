from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
from PyQt6.QtGui import QPen, QBrush, QPainter
from PyQt6.QtCore import QRectF, QPointF

from theme import detect_theme


class ActivityNode(QGraphicsRectItem):
    PADDING = 14
    RADIUS = 8

    def __init__(self, label, theme=None):
        super().__init__()
        self.theme = theme if theme is not None else detect_theme()
        self.label = label
        self.text = QGraphicsTextItem(label, self)
        self.text.setDefaultTextColor(self.theme.qcolor("node_text"))
        self._update_size()
        self.setPen(QPen(self.theme.qcolor("node_border"), 1.2))
        self.setBrush(QBrush(self.theme.qcolor("node_fill")))
        self.setZValue(2)

    def _update_size(self):
        rect = self.text.boundingRect()
        w = rect.width() + self.PADDING * 2
        h = rect.height() + self.PADDING * 2
        self.setRect(QRectF(0, 0, w, h))
        self.text.setPos(self.PADDING, self.PADDING)

    def paint(self, painter: QPainter, option, widget=None):
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(self.pen())
            painter.setBrush(self.brush())
            painter.drawRoundedRect(self.rect(), self.RADIUS, self.RADIUS)
        except Exception:
            import traceback
            print("[ActivityNode] paint() failed - skipping this frame. Traceback:")
            traceback.print_exc()

    def scene_center(self):
        r = self.rect()
        return self.mapToScene(QPointF(r.width() / 2, r.height() / 2))

    def edge_point_towards(self, target_point):
        center = self.scene_center()
        rect = self.sceneBoundingRect()
        dx = target_point.x() - center.x()
        dy = target_point.y() - center.y()
        if dx == 0 and dy == 0:
            return center
        hw = rect.width() / 2
        hh = rect.height() / 2
        scale_x = hw / abs(dx) if dx != 0 else float("inf")
        scale_y = hh / abs(dy) if dy != 0 else float("inf")
        scale = min(scale_x, scale_y)
        return QPointF(center.x() + dx * scale,center.y() + dy * scale,)