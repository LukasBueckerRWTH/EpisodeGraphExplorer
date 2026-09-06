from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsPolygonItem
from PyQt6.QtGui import QPainterPath, QPen, QPolygonF
from PyQt6.QtCore import QPointF
import math

from theme import detect_theme


class TransitionArrow(QGraphicsPathItem):

    ARROW_SIZE = 12
    CURVE_HEIGHT = 60

    def __init__(self, source, target, source_layer, target_layer, theme=None):
        super().__init__()

        self.theme = theme if theme is not None else detect_theme()

        self.source = source
        self.target = target
        self.source_layer = source_layer
        self.target_layer = target_layer

        self.setPen(QPen(self.theme.qcolor("arrow"), 2))
        self.setZValue(1)

        self.arrow_head = QGraphicsPolygonItem(self)
        self.arrow_head.setBrush(self.theme.qcolor("arrow"))

        self.update_position()

    def update_position(self):
        sc = self.source.scene_center()
        tc = self.target.scene_center()
        start_scene = self.source.edge_point_towards(tc)
        end_scene = self.target.edge_point_towards(sc)
        start = self.mapFromScene(start_scene)
        end = self.mapFromScene(end_scene)
        path = QPainterPath()
        path.moveTo(start)
        layer_distance = self.target_layer - self.source_layer

        if abs(layer_distance) <= 1:
            path.lineTo(end)
        else:
            mid_x = (start.x() + end.x()) / 2
            direction = -1 if start.y() < end.y() else 1
            curve_y = min(start.y(), end.y()) - direction * self.CURVE_HEIGHT
            control = QPointF(mid_x, curve_y)
            path.quadTo(control, end)

        self.setPath(path)
        self._update_arrowhead(path)

    def _update_arrowhead(self, path):
        end = path.pointAtPercent(1.0)
        prev = path.pointAtPercent(0.98)
        angle = math.atan2(-(end.y() - prev.y()),
                           end.x() - prev.x())
        p1 = end
        p2 = QPointF(p1.x() - self.ARROW_SIZE * math.cos(angle - math.pi/6),p1.y() + self.ARROW_SIZE * math.sin(angle - math.pi/6),)
        p3 = QPointF(p1.x() - self.ARROW_SIZE * math.cos(angle + math.pi/6),p1.y() + self.ARROW_SIZE * math.sin(angle + math.pi/6),)
        self.arrow_head.setPolygon(QPolygonF([p1, p2, p3]))