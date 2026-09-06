from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsPolygonItem
from PyQt6.QtGui import QPainterPath, QPen, QBrush, QPolygonF, QColor, QPainterPathStroker
from PyQt6.QtCore import QPointF
import math

from theme import detect_theme


class EpisodeRelationArrow(QGraphicsPathItem):
    ARROW_SIZE = 12

    def __init__(self, path, color, pen=None, theme=None):
        super().__init__(path)
        self.theme = theme if theme is not None else detect_theme()
        self.color = color
        if pen is None:
            pen = QPen(color, 2)

        self.setPen(pen)
        halo_color = QColor(*self.theme.relation_halo)
        self.outline_pen = QPen(halo_color, pen.width() + 3)
        self.setZValue(-10)
        self.arrow_head = QGraphicsPolygonItem(self)
        self.arrow_head.setBrush(QBrush(color))
        self.arrow_head.setPen(QPen(self.theme.qcolor("border_strong"), 1))
        self._update_arrowhead()

    def set_path(self, path):
        self.setPath(path)
        self._update_arrowhead()

    def update_position(self):
        start = self.start
        end = self.end
        path = QPainterPath()
        path.moveTo(start)
        dx = abs(end.x() - start.x())
        if dx > 200:
            mid_x = (start.x() + end.x()) / 2
            control = QPointF(mid_x, min(start.y(), end.y()) - self.CURVE_HEIGHT)
            path.quadTo(control, end)
        else:
            path.lineTo(end)
        self.setPath(path)
        self._update_arrowhead(path)

    def _update_arrowhead(self):
        path = self.path()
        end = path.pointAtPercent(1.0)
        prev = path.pointAtPercent(0.97)
        dx = end.x() - prev.x()
        dy = end.y() - prev.y()
        angle = math.atan2(dy, dx)
        p1 = QPointF(end.x() - 2 * math.cos(angle),end.y() - 2 * math.sin(angle))
        p2 = QPointF(end.x() - self.ARROW_SIZE * math.cos(angle - math.pi / 6),end.y() - self.ARROW_SIZE * math.sin(angle - math.pi / 6),)
        p3 = QPointF(end.x() - self.ARROW_SIZE * math.cos(angle + math.pi / 6),end.y() - self.ARROW_SIZE * math.sin(angle + math.pi / 6),)
        self.arrow_head.setPolygon(QPolygonF([p1, p2, p3]))

    def shape(self):
        stroker = QPainterPathStroker()
        stroker.setWidth(self.pen().widthF() + 4)
        path = stroker.createStroke(self.path())
        path.addPolygon(self.arrow_head.polygon())
        return path

    def paint(self, painter, option, widget):
        try:
            halo_color = QColor(*self.theme.relation_halo)
            outline_pen = QPen(halo_color, self.pen().width() + 2)
            outline_pen.setStyle(self.pen().style())
            outline_pen.setDashPattern(self.pen().dashPattern())
            painter.setPen(outline_pen)
            painter.drawPath(self.path())
            painter.setPen(self.pen())
            painter.drawPath(self.path())
        except Exception:
            import traceback
            print("EpisodeRelationArrow paint() failed. Traceback:")
            traceback.print_exc()