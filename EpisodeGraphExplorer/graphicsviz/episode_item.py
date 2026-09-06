from PyQt6.QtWidgets import QGraphicsRectItem, QDialog, QVBoxLayout, QGraphicsScene, QGraphicsView, QGraphicsTextItem, QGraphicsItem
from PyQt6.QtGui import QPen, QBrush, QPainter
from PyQt6.QtCore import Qt, QObject, QRectF, pyqtSignal

from activity_node import ActivityNode
from transition_arrow import TransitionArrow
from theme import detect_theme
import math

class EpisodeItemSignals(QObject):
    focusClicked = pyqtSignal(object)

class EpisodeItem(QGraphicsRectItem):

    PADDING = 22
    RADIUS = 12
    BUTTON_SIZE = 16
    BUTTON_GAP = 4
    BUTTON_MARGIN = 10          
    TOP_BAR_HEIGHT = 34         

    def __init__(self, raw_data, layout_engine, signals, visualizer=None, parent=None, theme=None):
        super().__init__(parent)

        if theme is not None:
            self.theme = theme
        elif visualizer is not None and getattr(visualizer, "theme", None) is not None:
            self.theme = visualizer.theme
        else:
            self.theme = detect_theme()

        self.setPen(QPen(self.theme.qcolor("episode_border"), 1.8))
        self.setBrush(QBrush(self.theme.qcolor("episode_fill")))
        self.setZValue(0)

        self.signals = signals
        self.layout_engine = layout_engine
        self.visualizer = visualizer
        self.raw_data_org = raw_data
        self.raw_data_current = raw_data

        #Self-references
        self.nodes = {}
        self.arrows = []

        #Hiding
        self.hiddenEPs = []
        self.raw_data_org = raw_data

        #Structuredness
        self.structured_activities = set()
        self.original_structured_activities = set()
        self.show_struct_activity_mark = False
        self.show_struct_episode_mark = False

        self._build_chrome()

        #Selection
        self.selected_state = False

    def _build_chrome(self):
        b = self.BUTTON_SIZE
        #Selector-Box
        self.select_button = QGraphicsRectItem(0, 0, b, b, self)
        self.select_button.setBrush(QBrush(self.theme.qcolor("bg_elevated")))
        self.select_button.setPen(QPen(self.theme.qcolor("border_strong")))
        self.select_mark = QGraphicsTextItem("", self.select_button)
        self.select_mark.setDefaultTextColor(self.theme.qcolor("accent"))
        self.select_mark.setScale(0.8)
        self.select_mark.setPos(3, -2)
        self.select_button.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.select_button.mousePressEvent = lambda event: self.toggle_selected()

        #Show-Hide Menu
        self.hidden_button = QGraphicsRectItem(0, 0, b, b, self)
        self.hidden_button.setBrush(QBrush(self.theme.qcolor("bg_panel_alt")))
        self.hidden_button.setPen(QPen(self.theme.qcolor("border_strong")))
        hidden_label = QGraphicsTextItem("H", self.hidden_button)
        hidden_label.setDefaultTextColor(self.theme.qcolor("text_secondary"))
        hidden_label.setScale(0.8)
        hidden_label.setPos(1, -2)
        self.hidden_button.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

        def hidden_click(event):
            if self.hiddenEPs:
                self._open_hidden_window()

        self.hidden_button.mousePressEvent = hidden_click

        #Focus button
        self.focus_button = QGraphicsRectItem(0, 0, b, b, self)
        self.focus_button.setBrush(QBrush(self.theme.qcolor("bg_panel_alt")))
        self.focus_button.setPen(QPen(self.theme.qcolor("border_strong")))
        focus_label = QGraphicsTextItem("F", self.focus_button)
        focus_label.setDefaultTextColor(self.theme.qcolor("text_secondary"))
        focus_label.setScale(0.8)
        focus_label.setPos(1, -2)

        self.focus_button.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

        def focus_click(event):
            self.signals.focusClicked.emit(self)

        self.focus_button.mousePressEvent = focus_click

        #Raw-data button - Only used for debugging
        #self.raw_button = QGraphicsRectItem(0, 0, b, b, self)
        #self.raw_button.setBrush(QBrush(self.theme.qcolor("bg_panel_alt")))
        #self.raw_button.setPen(QPen(self.theme.qcolor("border_strong")))
        #raw_label = QGraphicsTextItem("R", self.raw_button)
        #raw_label.setDefaultTextColor(self.theme.qcolor("text_secondary"))
        #raw_label.setScale(0.8)
        #raw_label.setPos(1, -2)
        #self.raw_button.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

        def raw_click(event):
            print(self.raw_data_org)

        #self.raw_button.mousePressEvent = raw_click

        #Frequency
        self.frequency_value = None
        self.freq_text = QGraphicsTextItem(self)
        self.freq_text.setDefaultTextColor(self.theme.qcolor("text_muted"))
        self.freq_text.setScale(0.85)
        self.freq_text.setZValue(5)

        self._chrome_items = [self.select_button, self.hidden_button,self.focus_button, self.freq_text] #self.raw_button
        
        self._structured_mark = None

    def _layout_chrome(self):
        rect = self.rect()
        m = self.BUTTON_MARGIN
        b = self.BUTTON_SIZE
        gap = self.BUTTON_GAP

        x = rect.right() - m - b
        y = rect.top() + m

        #self.raw_button.setPos(x, y)
        #x -= (b + gap)
        self.focus_button.setPos(x, y)
        x -= (b + gap)
        self.hidden_button.setPos(x, y)
        x -= (b + gap)
        self.select_button.setPos(x, y)

        left_x = rect.left() + m
        top_y = rect.top() + m - 2

        if self._structured_mark is not None and self._structured_mark.isVisible():
            self._structured_mark.setPos(left_x, top_y)
            left_x += self._structured_mark.boundingRect().width() + 6

        if self.frequency_value is not None:
            self.freq_text.setPos(left_x, top_y)
        
    def toggle_selected(self):

        self.set_selected_state(not self.selected_state)

        if self.visualizer is not None:
            self.visualizer.toggle_episode_selection(self)
        else:
            return

    def set_selected_state(self, state):

        self.selected_state = state

        if state:
            self.select_mark.setPlainText("✓")
        else:
            self.select_mark.setPlainText("")

        self.update()
    
    def set_frequency(self, freq):
        self.frequency_value = freq

        if freq is None:
            self.freq_text.setPlainText("")
        else:
            self.freq_text.setPlainText(f"{freq:.3f}")

        self._layout_chrome()

    def set_episode_scale(self, scale: float):
        self.episode_scale = scale
        self.setScale(scale)

    def compute_scale_from_frequency(self, freq, min_freq, max_freq):
        if max_freq == min_freq:
            return 1.0
        norm = (freq - min_freq) / (max_freq - min_freq)
        scaled = math.log1p(norm * 9) / math.log1p(9)
        return 0.8 + scaled * 0.4   # → range: 0.7 to 1.4

    def _content_bounds(self):
        items = list(self.nodes.values()) + self.arrows
        if not items:
            return None
        bounds = None
        for item in items:
            item_rect = item.mapRectToParent(item.boundingRect())
            bounds = item_rect if bounds is None else bounds.united(item_rect)

        return bounds

    def update_border(self):
        content_rect = self._content_bounds()
        if content_rect is None:
            content_rect = self._zero_rect()
        rect = content_rect.adjusted(-self.PADDING,-self.PADDING,self.PADDING,self.PADDING,)
        rect.setTop(rect.top() - self.TOP_BAR_HEIGHT)
        self.setRect(rect)
        self.setTransformOriginPoint(self.rect().center())

        if getattr(self, "show_struct_episode_mark", False) and getattr(self, "structured_ratio", 0) >= 0.66:
            if self._structured_mark is None:
                self._structured_mark = QGraphicsTextItem("S", self)
                self._structured_mark.setDefaultTextColor(self.theme.qcolor("structured_mark"))
            self._structured_mark.show()
        elif self._structured_mark is not None:
            self._structured_mark.hide()

        self._layout_chrome()

    def _zero_rect(self):
        return QRectF(0, 0, 0, 0)

    def paint(self, painter: QPainter, option, widget=None):
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            if self.selected_state:
                painter.setPen(QPen(self.theme.qcolor("episode_border_selected"), 4))
            else:
                painter.setPen(self.pen())
            painter.setBrush(self.brush())
            painter.drawRoundedRect(self.rect(), self.RADIUS, self.RADIUS)
        except Exception:
            import traceback
            print("EpisodeItem paint() failed, skipping this frame. Traceback:")
            traceback.print_exc()
    
    def rebuild_from_current(self):
        self.prepareGeometryChange()

        for arrow in self.arrows:
            arrow.setParentItem(None)
            arrow.scene().removeItem(arrow)

        for node in self.nodes.values():
            node.setParentItem(None)
            node.scene().removeItem(node)

        self.nodes.clear()
        self.arrows.clear()
        activities, transitions = self.raw_data_current
        positions, layers = self.layout_engine.compute_layout(activities,transitions,getattr(self, "episode_scale", 1.0))

        for name, (x, y) in positions.items():
            node = ActivityNode(name, theme=self.theme)
            node.label = name
            node.setParentItem(self)
            node.setPos(x, y)
            self.nodes[name] = node
        
        for node in self.nodes.values():
            node.setPen(QPen(self.theme.qcolor("node_border"), 1.5))

        if self.show_struct_activity_mark and self.structured_activities:
            for node in self.nodes.values():
                if node.label in self.structured_activities:
                    node.setPen(QPen(self.theme.qcolor("node_border_structured"), 3))

        for src, dst in transitions:
            arrow = TransitionArrow(self.nodes[src],self.nodes[dst],layers[src],layers[dst],theme=self.theme)
            arrow.setParentItem(self)
            self.arrows.append(arrow)
            arrow.update_position()

        self.update_border()
        self.update()
        scale = getattr(self, "episode_scale", 1.0)
        self.set_episode_scale(scale)

    def apply_relation(self, relation):
        activities, transitions = self.raw_data_org
        label = relation[0]
        label_lower = label.lower()
        rename_map = {}

        if label_lower == "update":
            _, act1, act2, tau = relation
            merged_name = f"UP({act1},{act2})"
            for act in activities:
                if act == act1 or act == act2:
                    rename_map[act] = merged_name
                else:
                    rename_map[act] = act
        elif label_lower == "choice":
            _, acts, tau = relation
            merged_name = f"×{{{','.join(sorted(acts))}}}"
            for act in activities:
                if act in acts:
                    rename_map[act] = merged_name
                else:
                    rename_map[act] = act
        else:
            return

        new_activities = []
        for act in activities:
            new_name = rename_map[act]
            if new_name not in new_activities:
                new_activities.append(new_name)

        new_transitions = []

        for src, dst in transitions:
            new_src = rename_map[src]
            new_dst = rename_map[dst]
            if new_src != new_dst:
                new_transitions.append((new_src, new_dst))

        self.raw_data_current = (new_activities, new_transitions)
        self._recompute_structured_activities(rename_map)
        self.rebuild_from_current()

    def _episode_key(self, ep):
        activities, transitions = ep
        canon_acts = tuple(sorted(set(activities)))
        canon_trans = tuple(sorted(set((str(a), str(b)) for a, b in transitions)))
        return (canon_acts, canon_trans)

    def _recompute_structured_activities(self, rename_map):
        base = self.original_structured_activities
        new_structured = set()
        for act in base:
            mapped = rename_map.get(act, act)
            new_structured.add(mapped)
        self.structured_activities = new_structured

    def reset_relation(self):
        self.current_relation = None
        self.raw_data_current = self.raw_data_org
        activities, _ = self.raw_data_current
        rename_map = {a: a for a in activities}
        self._recompute_structured_activities(rename_map)
        self.rebuild_from_current()

    def mousePressEvent(self, event):
        if (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            if self.visualizer is not None:
                self.visualizer.toggle_episode_selection(self)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.toggle_selected()
        super().mouseDoubleClickEvent(event)

    def _open_hidden_window(self):
        dialog = QDialog()
        dialog.setStyleSheet(f"QDialog{{background-color: {self.theme.bg_canvas};}}")
        layout = QVBoxLayout(dialog)
        scene = QGraphicsScene()
        view = QGraphicsView(scene)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        view.setStyleSheet(f"QGraphicsView {{background-color: {self.theme.bg_canvas}; border: none; }}")
        layout.addWidget(view)
        y = 0
        seen_eps = []
        for hidden_data in self.hiddenEPs:
            if hidden_data["episode"] in seen_eps:
                continue
            seen_eps.append(hidden_data["episode"])
            label = hidden_data["label"]
            tau = hidden_data["tau"]
            ep = hidden_data["episode"]
            title = QGraphicsTextItem(f"{label}  (τ = {tau:.2f})")
            title.setDefaultTextColor(self.theme.qcolor("text_primary"))
            title.setPos(0, y)
            title.setZValue(10)
            scene.addItem(title)
            y += 25
            if hidden_data.get("conflict"):
                note_text = hidden_data.get("note", "Kept visible: conflicting relations point both ways")
                note = QGraphicsTextItem(f"⚠ {note_text}")
                note.setDefaultTextColor(self.theme.qcolor("text_secondary"))
                note.setPos(0, y)
                note.setZValue(10)
                scene.addItem(note)
                y += 22
            signals = EpisodeItemSignals()
            item = EpisodeItem(ep, self.layout_engine, signals, theme=self.theme)
            scene.addItem(item)
            item.rebuild_from_current()
            item.setPos(0, y)
            y += item.boundingRect().height() + 50

        dialog.setWindowTitle(f"Hidden Episodes ({len(seen_eps)})")
        scene.setSceneRect(scene.itemsBoundingRect())
        dialog.resize(600, 400)
        dialog.exec()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            old_pos = self.pos()
            new_pos = value
            delta = new_pos - old_pos
            if self.visualizer is not None:
                self.visualizer.move_selected_group(self, delta)
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if self.visualizer is not None:
                self.visualizer._store_episode_position(self)
        return super().itemChange(change, value)