from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsRectItem
from PyQt6.QtCore import QRectF, QPointF, Qt
from PyQt6.QtGui import QPen, QFont, QFontMetrics, QPolygonF, QBrush, QPainter, QColor
import math
from collections import defaultdict, deque
import sys

class EpisodeVisualizer(QApplication):
    def __init__(self, episodes_data=None, inter_episode_transitions=None):
        super().__init__(sys.argv)
        self._episodes_data = episodes_data if episodes_data is not None else []
        self._inter_episode_transitions = inter_episode_transitions if inter_episode_transitions is not None else []
        self.label_colors = {'SUBSUME': QColor(200, 50, 50),'MERGE': QColor(50, 50, 200),}
        self.spacing_x = 80
        self.spacing_y = 120
        self.node_height = 60
        self.arrow_size = 12
        self.font = QFont("Arial", 12)
        self.pen = QPen(Qt.GlobalColor.black)
        self.pen.setWidth(2)
        self.window_width = 1200

    def set_episodes_data(self, data):
        self._episodes_data = data

    def get_episodes_data(self):
        return self._episodes_data

    def set_inter_episode_transitions(self, transitions):
        self._inter_episode_transitions = transitions

    def get_inter_episode_transitions(self):
        return self._inter_episode_transitions

    def point_on_ellipse_edge(self, center, width, height, target):
        dx = target.x() - center.x()
        dy = target.y() - center.y()
        if dx == 0:
            return QPointF(center.x(), center.y() + (height/2 if dy>0 else -height/2))
        angle = math.atan2(dy, dx)
        rx = width / 2
        ry = height / 2
        ex = rx * math.cos(angle)
        ey = ry * math.sin(angle)
        return QPointF(center.x() + ex, center.y() + ey)

    def closest_point_on_rect(self, rect, point):
        x = max(rect.left(), min(point.x(), rect.right()))
        y = max(rect.top(), min(point.y(), rect.bottom()))
        dx_left = abs(x - rect.left())
        dx_right = abs(x - rect.right())
        dy_top = abs(y - rect.top())
        dy_bottom = abs(y - rect.bottom())
        min_dist = min(dx_left, dx_right, dy_top, dy_bottom)
        if min_dist == dx_left:
            return QPointF(rect.left(), y)
        elif min_dist == dx_right:
            return QPointF(rect.right(), y)
        elif min_dist == dy_top:
            return QPointF(x, rect.top())
        else:
            return QPointF(x, rect.bottom())

    def perpendicular_offset(self, start, end, index, reverse=False, step=20):
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = math.hypot(dx, dy)
        if length == 0:
            return QPointF(start.x(), start.y())
        ux = dx / length
        uy = dy / length
        px = -uy
        py = ux
        offset = ((index + 1) // 2) * step * (-1 if index % 2 else 1)
        if reverse:
            offset *= -1
        return QPointF(px * offset, py * offset)

    def _build_scene(self):
        scene = QGraphicsScene()
        scene.setBackgroundBrush(QBrush(Qt.GlobalColor.lightGray))
        episode_boxes = []
        episode_centers = []
        episode_nodes_sizes = []
        episode_widths = []
        for nodes, edges in self._episodes_data:
            node_sizes = {}
            fm = QFontMetrics(self.font)
            total_width = 0
            for node in nodes:
                text_width = fm.horizontalAdvance(node) + 30
                node_width = max(120, text_width)
                node_sizes[node] = node_width
                total_width += node_width + self.spacing_x
            episode_widths.append(total_width)
            episode_nodes_sizes.append(node_sizes)
        x_cursor = 0
        y_cursor = 0
        row_max_height = 0
        for idx, (nodes, edges) in enumerate(self._episodes_data):
            node_sizes = episode_nodes_sizes[idx]
            if x_cursor + episode_widths[idx] > self.window_width:
                x_cursor = 0
                y_cursor += row_max_height + self.spacing_y
                row_max_height = 0
            adj = defaultdict(list)
            incoming = defaultdict(int)
            for a, b in edges:
                adj[a].append(b)
                incoming[b] += 1
                if a not in incoming:
                    incoming[a] = incoming.get(a, 0)
            layers = defaultdict(list)
            queue = deque([n for n in nodes if incoming[n] == 0])
            layer_index = 0
            placed = set()
            while queue:
                next_queue = deque()
                for n in queue:
                    layers[layer_index].append(n)
                    placed.add(n)
                    for m in adj[n]:
                        incoming[m] -= 1
                        if incoming[m] == 0:
                            next_queue.append(m)
                queue = next_queue
                layer_index += 1
            for n in nodes:
                if n not in placed:
                    layers[layer_index].append(n)
            node_positions = {}
            max_layer_width = 0
            min_x, min_y = float('inf'), float('inf')
            max_x, max_y = 0, 0

            for layer_num, layer_nodes in layers.items():
                x = x_cursor
                layer_y = y_cursor + layer_num * (self.node_height + self.spacing_y//2)
                for node in layer_nodes:
                    node_width = node_sizes[node]
                    ellipse = QGraphicsEllipseItem(QRectF(0, 0, node_width, self.node_height))
                    ellipse.setPos(x, layer_y)
                    ellipse.setBrush(QBrush(Qt.GlobalColor.white))
                    scene.addItem(ellipse)
                    fm = QFontMetrics(self.font)
                    display_text = node
                    max_chars = int((node_width - 10) / fm.averageCharWidth())
                    if len(node) > max_chars:
                        display_text = node[:max_chars-3] + "..."
                    text_item = QGraphicsTextItem(display_text, ellipse)
                    text_item.setFont(self.font)
                    text_item.setDefaultTextColor(Qt.GlobalColor.black)
                    text_rect = fm.boundingRect(display_text)
                    text_item.setPos((node_width - text_rect.width())/2, (self.node_height - text_rect.height())/2)
                    node_positions[node] = QPointF(x + node_width/2, layer_y + self.node_height/2)
                    min_x = min(min_x, x)
                    min_y = min(min_y, layer_y)
                    max_x = max(max_x, x + node_width)
                    max_y = max(max_y, layer_y + self.node_height)
                    x += node_width + self.spacing_x
                max_layer_width = max(max_layer_width, x - x_cursor)
                row_max_height = max(row_max_height, (layer_num+1)*(self.node_height + self.spacing_y//2))

            for src, dst in edges:
                src_center = node_positions[src]
                dst_center = node_positions[dst]
                start = self.point_on_ellipse_edge(src_center, node_sizes[src], self.node_height, dst_center)
                end = self.point_on_ellipse_edge(dst_center, node_sizes[dst], self.node_height, src_center)
                scene.addLine(start.x(), start.y(), end.x(), end.y(), self.pen)
                angle = math.atan2(end.y() - start.y(), end.x() - start.x())
                arrow_p1 = QPointF(end.x() - self.arrow_size * math.cos(angle - math.pi/6), end.y() - self.arrow_size * math.sin(angle - math.pi/6))
                arrow_p2 = QPointF(end.x() - self.arrow_size * math.cos(angle + math.pi/6),end.y() - self.arrow_size * math.sin(angle + math.pi/6))
                arrow_head = QPolygonF([end, arrow_p1, arrow_p2])
                scene.addPolygon(arrow_head, self.pen, QBrush(Qt.GlobalColor.black))

            padding = 20
            rect_item = QGraphicsRectItem(min_x-padding, min_y-padding, max_x-min_x+2*padding, max_y-min_y+2*padding)
            rect_item.setPen(QPen(Qt.GlobalColor.black, 2, Qt.PenStyle.DashLine))
            scene.addItem(rect_item)
            episode_boxes.append(rect_item)
            episode_centers.append(QPointF((min_x+max_x)/2, (min_y+max_y)/2))
            x_cursor += max_layer_width + self.spacing_x

        pair_count = defaultdict(int)
        for label, data1, data2, value in self._inter_episode_transitions:
            idx1 = self._episodes_data.index(data1)
            idx2 = self._episodes_data.index(data2)
            box1 = episode_boxes[idx1].rect()
            box2 = episode_boxes[idx2].rect()
            center1 = episode_centers[idx1]
            center2 = episode_centers[idx2]
            reverse = False
            if idx1 > idx2:
                reverse = True
                key = (idx2, idx1)
            else:
                key = (idx1, idx2)

            count = pair_count[key]
            pair_count[key] += 1
            offset = self.perpendicular_offset(center1, center2, count, reverse=reverse)
            start = self.closest_point_on_rect(box1, center2 + offset)
            end = self.closest_point_on_rect(box2, center1 + offset)
            color = self.label_colors.get(label, Qt.GlobalColor.black)
            pen_tr = QPen(color, 2)
            scene.addLine(start.x(), start.y(), end.x(), end.y(), pen_tr)
            angle = math.atan2(end.y() - start.y(), end.x() - start.x())
            arrow_p1 = QPointF(end.x() - self.arrow_size * math.cos(angle - math.pi/6),
                               end.y() - self.arrow_size * math.sin(angle - math.pi/6))
            arrow_p2 = QPointF(end.x() - self.arrow_size * math.cos(angle + math.pi/6),
                               end.y() - self.arrow_size * math.sin(angle + math.pi/6))
            arrow_head = QPolygonF([end, arrow_p1, arrow_p2])
            scene.addPolygon(arrow_head, pen_tr, QBrush(color))
            mid_x = (start.x() + end.x())/2
            mid_y = (start.y() + end.y())/2
            text_offset = self.perpendicular_offset(start, end, count, reverse=reverse)
            text_item = QGraphicsTextItem(f"{label} ({value})")
            text_item.setFont(self.font)
            text_item.setDefaultTextColor(color)
            text_item.setPos(mid_x + text_offset.x(), mid_y + text_offset.y())
            scene.addItem(text_item)
            
        return scene

    def run(self):
        self.scene = self._build_scene()
        view = QGraphicsView(self.scene)
        view.setWindowTitle("Episode Visualizer")
        view.resize(self.window_width, 800)
        view.setRenderHints(view.renderHints() | QPainter.RenderHint.Antialiasing)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        view.show()
        self.exec()