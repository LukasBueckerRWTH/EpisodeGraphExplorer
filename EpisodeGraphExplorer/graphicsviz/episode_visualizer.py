from PyQt6.QtWidgets import QWidget,QVBoxLayout,QGraphicsView,QGraphicsScene,QHBoxLayout,QLabel,QPushButton,QSlider,QCheckBox,QGraphicsItem,QApplication,QScrollArea,QFrame
from PyQt6.QtCore import QPointF, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QPainterPath, QFont, QFontMetricsF
import math
import copy

from layout_engine import LayoutEngine
from episode_item import EpisodeItem, EpisodeItemSignals
from graphics_view import ZoomableGraphicsView
from collapsible_section import CollapsibleSection
from episode_relation_arrow import EpisodeRelationArrow
from layouts.force_layout import ForceLayout
from theme import detect_theme, build_stylesheet
from wrapping_button import WrappingButton



class _OutlinedTextItem(QGraphicsItem):

    def __init__(self, text, fill_color, outline_color=None,
                 outline_width=1.5, font=None, parent=None):
        super().__init__(parent)
        self._fill_color = fill_color
        self._outline_pen = QPen(
            outline_color if outline_color is not None else QColor("black"),
            outline_width
        )
        self._outline_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

        self._font = font if font is not None else QFont()

        metrics = QFontMetricsF(self._font)
        raw_path = QPainterPath()
        raw_path.addText(0, metrics.ascent(), self._font, text)

        center = raw_path.boundingRect().center()
        self._path = QPainterPath()
        self._path.addPath(raw_path.translated(-center.x(), -center.y()))

        self._rect = self._path.boundingRect()

    def boundingRect(self):
        pad = self._outline_pen.widthF()
        return self._rect.adjusted(-pad, -pad, pad, pad)

    def paint(self, painter, option, widget=None):
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            painter.setPen(self._outline_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(self._path)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(self._fill_color))
            painter.drawPath(self._path)
        except Exception:
            import traceback
            print("[_OutlinedTextItem] paint() failed - skipping this frame. Traceback:")
            traceback.print_exc()


class EpisodeVisualizer(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.theme = detect_theme()
        self.setStyleSheet(build_stylesheet(self.theme))
        self.setWindowTitle("Episode Graph Explorer")

        self.active_relation = None
        self.episode_items = []
        self.relation_buttons = {}
        self.focused_episode_keys = None

        self.LEFT_RESERVED = 180
        self.LEFT_EPISODE_GAP = 60
        self.RIGHT_RESERVED = 180
        self.RIGHT_EPISODE_GAP = 60
        self.EPISODE_SPACING_X = 40
        self.EPISODE_SPACING_Y = 60

        self.episodes = []
        self.actUPChoice = []
        self._episode_lookup = {}
        self._initial_view_fit_done = False
        
        #Merging
        self.original_episodes = None
        self.original_direct_relations = None
        self.original_show_hide_relations = None
        self.original_episode_lookup = None
        self.original_episode_occurrences = None
        self.original_occurrence_sets = None
        self.enable_connection_merge = False

        #Hiding
        self.tagRelations = []
        self.showHideRelations = []

        #Resizing
        self.episode_occurrences = {}
        self.occurrence_sets = {}
        self.min_episode_scale = 0.75
        self.max_episode_scale = 1.5

        #Application of activity relations
        self.active_episodes = None
        self.active_relations = None

        #Direct Relations
        self.directRelations = []
        self.direct_relation_types = {
            "Dependency": {"color": self.theme.qcolor("rel_dependency"), "enabled": True, "tau": 0.5},
            "Co-occurrence": {"color": self.theme.qcolor("rel_cooccurrence"), "enabled": True, "tau": 0.5},
            "Exclusion": {"color": self.theme.qcolor("rel_exclusion"), "enabled": False, "tau": 1.0},
        }
        self.direct_relation_items = []

        #Thresholds Show/Hide-Relations
        self.T_SUBEP = 0.8
        self.T_SUBSUME = 0.8
        self.T_REORDER = 0.8

        #Thresholds and Settings Tag-Relations
        self.activity_struct_tau = 0.9
        self.episode_struct_ratio = 0.66
        self.show_struct_episode_mark = False
        self.show_struct_activity_mark = False
        self.only_show_structured_episodes = False
        self.enable_episode_hiding = True

        #Saved Filters
        self.saved_filter_state = {}

        #Episode Positions
        self.manual_episode_positions = {}

        self._group_moving = False
        self.relation_update_timer = QTimer()
        self.relation_update_timer.setSingleShot(True)
        self.relation_update_timer.timeout.connect(self._deferred_scene_update)

        self.scene = QGraphicsScene(self)
        self.view = ZoomableGraphicsView(self.scene)

        self.view.setRenderHints(QPainter.RenderHint.Antialiasing |QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setStyleSheet(f"""QGraphicsView {{background-color: {self.theme.bg_canvas}; border: none;}}""")
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        self.view.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing,True)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # left panel
        self.left_panel = QWidget()
        self.left_panel.setObjectName("leftPanel")
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.left_layout.setContentsMargins(12, 12, 12, 12)
        self.left_layout.setSpacing(8)

        self.left_scroll_area = QScrollArea()
        self.left_scroll_area.setObjectName("leftScrollArea")
        self.left_scroll_area.setWidget(self.left_panel)
        self.left_scroll_area.setWidgetResizable(True)
        self.left_scroll_area.setFixedWidth(self.LEFT_RESERVED)
        self.left_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.left_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.left_scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        main_layout.addWidget(self.left_scroll_area)

        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0,0,0,0)

        self.LARGE_EPISODE_COUNT_THRESHOLD = 100
        self.performance_warning_label = QLabel("")
        self.performance_warning_label.setStyleSheet(
            f"QLabel {{ background-color: {self.theme.bg_panel_alt}; "
            f"color: {self.theme.text_primary}; padding: 6px 10px; }}"
        )
        self.performance_warning_label.hide()
        center_layout.addWidget(self.performance_warning_label)

        center_layout.addWidget(self.view)

        main_layout.addWidget(center_widget)

        self.right_panel = QWidget()
        self.right_panel.setObjectName("rightPanel")
        self.right_panel.setFixedWidth(self.RIGHT_RESERVED)
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.right_layout.setContentsMargins(12, 12, 12, 12)
        self.right_layout.setSpacing(10)

        main_layout.addWidget(self.right_panel)

        self.layout_engine = LayoutEngine()
        self.episode_layout = ForceLayout()

        #Episode Selection
        self.selected_episode_keys = set()
        self.selection_toolbar = None
        self.selection_toolbar = QWidget()
        toolbar_layout = QVBoxLayout(self.selection_toolbar)
        toolbar_layout.setContentsMargins(8,8,8,8)
        toolbar_layout.setSpacing(6)

        self.selection_toolbar.setStyleSheet(f"""
        QWidget {{
            background-color: {self.theme.bg_panel_alt};
            border: 1px solid {self.theme.border};
            border-radius: 0px;
        }}
        """)

        self.selection_toolbar.hide()

        focus_btn = QPushButton("Focus")
        merge_btn = QPushButton("Merge")
        print_btn = QPushButton("Print Relations")
        clear_btn = QPushButton("Clear")
        focus_btn.setObjectName("primaryButton")
        merge_btn.setObjectName("primaryButton")
        print_btn.setObjectName("primaryButton")
        clear_btn.setObjectName("dangerButton")
        focus_btn.setMinimumHeight(32)
        merge_btn.setMinimumHeight(32)
        print_btn.setMinimumHeight(32)
        clear_btn.setMinimumHeight(32)
        focus_btn.setSizePolicy(focus_btn.sizePolicy().horizontalPolicy(),focus_btn.sizePolicy().verticalPolicy())
        self.selection_toolbar.setSizePolicy(self.selection_toolbar.sizePolicy().horizontalPolicy(),self.selection_toolbar.sizePolicy().verticalPolicy())
        focus_btn.clicked.connect(self.focus_selected_episodes)
        merge_btn.clicked.connect(self.merge_selected_episodes)
        print_btn.clicked.connect(self.print_selected_relations)
        clear_btn.clicked.connect(self.clear_episode_selection)

        toolbar_layout.addWidget(focus_btn)
        toolbar_layout.addWidget(merge_btn)
        toolbar_layout.addWidget(print_btn)
        toolbar_layout.addWidget(clear_btn)

        self.left_layout.addWidget(self.selection_toolbar)

    def _deferred_scene_update(self):

        self._update_scene_rect()
        self._draw_direct_relations()

    def set_episode_occurrences(self, freq_set):
        self.episode_occurrences = freq_set
    
    def set_occurrence_sets(self, occ_sets):
        self.occurrence_sets = occ_sets
    
    def set_total_traces(self,total_traces):
        self.total_traces = total_traces
    
    def get_episode_occurrences(self):
        return self.episode_occurrences
    
    def get_occurrence_sets(self):
        return self.occurrence_sets
    
    def get_total_traces(self):
        return self.total_traces

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_scene_rect()

    def _update_scene_rect(self):

        rect = self.scene.itemsBoundingRect().adjusted(-150, -150, 150, 150)

        self.scene.setSceneRect(rect)

    def _get_episode_scale(self, key):

        if not self.episode_occurrences:
            return 1.0

        freq = self.episode_occurrences.get(key, 0)

        if freq is None:
            return 1.0

        if freq == 0:
            return 1.0

        values = list(self.episode_occurrences.values())

        min_f = min(values)
        max_f = max(values)

        if min_f == max_f:
            return 1.0

        norm = (freq - min_f) / (max_f - min_f)

        return self.min_episode_scale + norm * (self.max_episode_scale - self.min_episode_scale)

    def build_visualization(self):
        self.scene.clear()
        self.direct_relation_items = []

        try:
            self._compute_structured_activities()
        except Exception:
            import traceback
            traceback.print_exc()
            self.structured_activities = set()

        self.episode_items = []

        try:
            self._process_show_hide_relations()
        except Exception:
            import traceback
            traceback.print_exc()
            self.visibleEpisodes = list(self.episodes)

        try:
            self._compute_structuredness()
        except Exception:
            import traceback
            traceback.print_exc()
            self.structured_episodes = {}
            self.activity_struct_tau_map = {}

        for raw_data in self.visibleEpisodes:
            try:
                key = self._episode_key(raw_data)
                if any(self._episode_key(obj.raw_data_org) == key for obj in self.episode_items):
                    continue

                episode_signals = EpisodeItemSignals()

                episode_item = EpisodeItem(
                    raw_data,
                    self.layout_engine,
                    episode_signals,
                    visualizer=self
                )

                key = self._episode_key(raw_data)
                activities, _ = raw_data

                episode_item.structured_activities = {act for act in activities if act in self.structured_activities}
                episode_item.original_structured_activities = set(episode_item.structured_activities)
                episode_item.structured_ratio = self.structured_episodes.get(key, 0)
                episode_item.show_struct_activity_mark = self.show_struct_activity_mark
                episode_item.show_struct_episode_mark = self.show_struct_episode_mark
                episode_item.activity_struct_tau_map = self.activity_struct_tau_map

                if key in self._episode_lookup:
                    episode_item.hiddenEPs = self._episode_lookup[key]["hidden"]

                if self.only_show_structured_episodes and episode_item.structured_ratio < self.episode_struct_ratio:
                    continue

                self.scene.addItem(episode_item)
                episode_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable,True)
                episode_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,True)
                episode_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,True)
                episode_item.signals.focusClicked.connect(self._focus_episode)
                episode_item.setZValue(10)
                episode_item.rebuild_from_current()
                episode_item.set_episode_scale(self._get_episode_scale(key))
                freq = self.episode_occurrences.get(key, 0)
                episode_item.set_frequency(freq)
                self.episode_items.append(episode_item)
                if key in self.selected_episode_keys:
                    episode_item.set_selected_state(True)
                else:
                    episode_item.set_selected_state(False)
            except Exception:
                import traceback
                traceback.print_exc()
                continue

        self.build_left_panel()
        self.build_right_panel()
        self._layout_episodes(self.episode_items)

        QTimer.singleShot(0, self._draw_direct_relations_safe)
        if not self._initial_view_fit_done and self.episode_items:
            QTimer.singleShot(0, self._fit_view_to_content)
            self._initial_view_fit_done = True

    def _fit_view_to_content(self):
        rect = self.scene.itemsBoundingRect()
        if rect.isEmpty():
            return
        rect = rect.adjusted(-40, -40, 40, 40)
        self.view.resetTransform()
        self.view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def _layout_episodes(self, episode_items):
        if not episode_items:
            return
        new_items = []
        for item in episode_items:
            key = self._episode_key(item.raw_data_org)
            if key in self.manual_episode_positions:
                item.setPos(self.manual_episode_positions[key])
            else:
                new_items.append(item)
        if new_items:
            if len(new_items) >= self.LARGE_EPISODE_COUNT_THRESHOLD:
                self.performance_warning_label.setText(f"Laying out {len(new_items)} episodes. This can take a while and the window may look unresponsive until it finishes.")
                self.performance_warning_label.show()
                QApplication.processEvents()
                print(f"{len(new_items)} episodes to lay out (>= {self.LARGE_EPISODE_COUNT_THRESHOLD}) - the force layout is O(iterations * n^2) and runs on the UI thread, so this will block the window for a while.")
            else:
                self.performance_warning_label.hide()
            self.episode_layout.layout(self, new_items)
            self.performance_warning_label.hide()
        self._update_scene_rect()

    def _on_relation_clicked(self, relation):
        for i in range(self.left_layout.count()):
            widget = self.left_layout.itemAt(i).widget()
            if isinstance(widget, (QPushButton, WrappingButton)):
                widget.setChecked(False)

        if self.active_relation == relation:
            self.active_relation = None
            self.reset_episode_merges()
            return

        else:
            self.active_relation = relation
            sender = self.sender()
            if isinstance(sender, (QPushButton, WrappingButton)):
                sender.setChecked(True)

        if self.original_episodes is None:
            self.original_episodes = list(self.episodes)
            self.original_direct_relations = list(self.directRelations)
            self.original_show_hide_relations = list(self.showHideRelations)
            self.original_episode_lookup = copy.deepcopy(self._episode_lookup)
            self.original_episode_occurrences = dict(self.episode_occurrences)
            self.original_occurrence_sets = dict(self.occurrence_sets)

        self._restore_original_merge_state()

        self._process_show_hide_relations()
        self.episodes, self.directRelations = self._apply_activity_relation(relation)
        self.build_visualization()
        self._ensure_lookup_integrity()

    def build_left_panel(self):

        while self.left_layout.count():
            child = self.left_layout.takeAt(0)
            widget = child.widget()
            if widget is None:
                continue
            if widget == self.selection_toolbar:
                continue
            widget.deleteLater()

        title = QLabel("Activity Relations")
        title.setObjectName("panelTitle")
        title.setWordWrap(True)
        self.left_layout.addWidget(title)

        visible_activities = set()
        for ep in self.visibleEpisodes:
            activities, _ = ep
            visible_activities.update(activities)

        for relation in self.actUPChoice:

            label = relation[0].lower()
            if label == "update":
                _, act1, act2, tau = relation
                rel_acts = {act1, act2}
                text = f"UPDATE: {act1} → {act2} (τ={tau:.2f})"
            elif label == "choice":
                _, acts, tau = relation
                rel_acts = set(acts)
                text = f"CHOICE: {', '.join(acts)} (τ={tau:.2f})"
            else:
                text = f"{label}: {act1} → {act2} (τ={tau:.2f})"
                rel_acts = set()

            is_active = (relation == self.active_relation)

            if not is_active and not rel_acts.issubset(visible_activities):
                continue

            btn = WrappingButton(text)
            btn.setCheckable(True)
            btn.setMinimumHeight(34)
            if self.active_relation == relation:
                btn.setChecked(True)
            else:
                btn.setChecked(False)

            btn.clicked.connect(lambda checked, rel=relation: self._on_relation_clicked(rel))
            self.left_layout.addWidget(btn)
        
        self.left_layout.addWidget(self.selection_toolbar)

    def _episode_key(self, ep):
        activities, transitions = ep
        canon_activities = tuple(sorted(set(activities)))
        canon_transitions = tuple(sorted((str(a), str(b))for a, b in transitions))

        return (canon_activities,canon_transitions)

    def _format_episode(self, ep):
        activities, transitions = ep
        acts_str = ", ".join(str(a) for a in activities)
        if transitions:
            trans_str = ", ".join(f"{a}->{b}" for a, b in transitions)
            return f"[{acts_str}] ({trans_str})"
        return f"[{acts_str}]"

    def _process_show_hide_relations(self):

        self.visibleEpisodes = list(self.episodes)
        if not self.enable_episode_hiding:
            self._episode_lookup = {}
            for ep in self.episodes:
                key = self._episode_key(ep)
                self._episode_lookup[key] = {
                    "data": ep,
                    "hidden": []
                }
            return

        if not hasattr(self, "_episode_lookup") or self._episode_lookup is None:
            self._episode_lookup = {}

        for ep in self.episodes:
            key = self._episode_key(ep)

            if key not in self._episode_lookup:
                self._episode_lookup[key] = {
                    "data": ep,
                    "hidden": []
                }

        for entry in self._episode_lookup.values():
            entry["hidden"] = [
                h for h in entry.get("hidden", [])
                if h.get("label") not in ("SUBEP", "SUBSUME", "REORDER") or h.get("source")
            ]

        hide_pairs = set()
        for label, ep1, ep2, tau in self.showHideRelations:

            if ((label == "SUBEP" and tau >= self.T_SUBEP) or
                (label == "SUBSUME" and tau >= self.T_SUBSUME) or
                (label == "REORDER" and tau >= self.T_REORDER)):
                key1 = self._episode_key(ep1)
                key2 = self._episode_key(ep2)
                hide_pairs.add((key1, key2))
                if key1 in self._episode_lookup:
                    if "hidden" not in self._episode_lookup[key1]:
                        self._episode_lookup[key1]["hidden"] = []

                    self._episode_lookup[key1]["hidden"].append({
                        "label": label,
                        "tau": tau,
                        "episode": ep2
                    })

        for key1, key2 in hide_pairs:
            if (key2, key1) in hide_pairs:
                for entry in self._episode_lookup.get(key1, {}).get("hidden", []):
                    if self._episode_key(entry["episode"]) == key2:
                        entry["conflict"] = True
                        entry["note"] = "Kept visible: conflicting relations point both ways"
                continue

            ep2 = self._episode_lookup[key2]["data"]
            if ep2 in self.visibleEpisodes:
                self.visibleEpisodes.remove(ep2)

        immediate_hider = {}
        for key1, key2 in hide_pairs:
            if (key2, key1) in hide_pairs:
                continue
            immediate_hider.setdefault(key2, key1)

        def _resolve_visible_root(hider_key):
            visited = set()
            while hider_key in immediate_hider and hider_key not in visited:
                visited.add(hider_key)
                hider_key = immediate_hider[hider_key]
            return hider_key

        for hidden_key, hider_key in immediate_hider.items():
            root_key = _resolve_visible_root(hider_key)
            if root_key == hider_key:
                continue
            if root_key not in self._episode_lookup:
                continue

            for entry in self._episode_lookup.get(hider_key, {}).get("hidden", []):
                if self._episode_key(entry["episode"]) == hidden_key:
                    self._episode_lookup[root_key].setdefault("hidden", []).append(entry)
                    break

    def _compute_structuredness(self):
        self.activity_struct_tau_map = {}
        for label, act, actset in self.tagRelations:
            if label == "STRUCT":
                tau = actset.get("tau_avg", 0)
                self.activity_struct_tau_map[act] = tau

        self.structured_activities = {
            act
            for act, tau in self.activity_struct_tau_map.items()
            if tau >= self.activity_struct_tau
        }

        self.structured_episodes = {}
        for ep in self.episodes:
            activities, _ = ep
            if not activities:
                continue

            structured_count = sum(1 for a in activities if a in self.structured_activities)
            ratio = structured_count / len(activities)
            self.structured_episodes[self._episode_key(ep)] = ratio

    def _make_wrapping_checkbox(self, text, checked=False):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        checkbox = QCheckBox()
        checkbox.setChecked(checked)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setCursor(Qt.CursorShape.PointingHandCursor)
        label.mousePressEvent = lambda event: checkbox.toggle()

        row_layout.addWidget(checkbox, 0)
        row_layout.addWidget(label, 1)

        return row, checkbox

    def build_right_panel(self):

        while self.right_layout.count():
            child = self.right_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        tag_section = CollapsibleSection("Structural Filters")
        self.right_layout.addWidget(tag_section)
        tag_layout = tag_section.content_layout
        act_label = QLabel(f"Activity STRUCT τ ≥ {self.activity_struct_tau:.2f}")
        act_label.setWordWrap(True)
        tag_layout.addWidget(act_label)
        act_slider = QSlider(Qt.Orientation.Horizontal)
        act_slider.setMinimum(0)
        act_slider.setMaximum(100)
        act_slider.setValue(int(self.activity_struct_tau * 100))

        def act_changed(v):
            self.activity_struct_tau = v / 100
            act_label.setText(f"Activity STRUCT τ ≥ {self.activity_struct_tau:.2f}")

        act_slider.valueChanged.connect(act_changed)
        tag_layout.addWidget(act_slider)
        ep_label = QLabel(f"Episode STRUCT ≥ {self.episode_struct_ratio:.2f}")
        ep_label.setWordWrap(True)
        tag_layout.addWidget(ep_label)
        ep_slider = QSlider(Qt.Orientation.Horizontal)
        ep_slider.setMinimum(0)
        ep_slider.setMaximum(100)
        ep_slider.setValue(int(self.episode_struct_ratio * 100))

        def ep_changed(v):
            self.episode_struct_ratio = v / 100
            ep_label.setText(f"Episode STRUCT ≥ {self.episode_struct_ratio:.2f}")

        ep_slider.valueChanged.connect(ep_changed)
        tag_layout.addWidget(ep_slider)
        ep_mark_row, self.show_ep_mark = self._make_wrapping_checkbox("Show Episode STRUCT Mark", self.show_struct_episode_mark)

        def toggle_ep(v):
            self.show_struct_episode_mark = bool(v)

        self.show_ep_mark.stateChanged.connect(toggle_ep)
        tag_layout.addWidget(ep_mark_row)
        act_mark_row, self.show_act_mark = self._make_wrapping_checkbox("Show Activity STRUCT Mark", self.show_struct_activity_mark)

        def toggle_act(v):
            self.show_struct_activity_mark = bool(v)

        self.show_act_mark.stateChanged.connect(toggle_act)
        tag_layout.addWidget(act_mark_row)
        only_struct_row, only_struct = self._make_wrapping_checkbox("Only Show Structured Episodes", self.only_show_structured_episodes)

        def toggle_only(v):
            self.only_show_structured_episodes = bool(v)

        only_struct.stateChanged.connect(toggle_only)
        tag_layout.addWidget(only_struct_row)
        rel_section = CollapsibleSection("Associative Filters")
        self.right_layout.addWidget(rel_section)

        for label, settings in self.direct_relation_types.items():

            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0,0,0,0)
            color_box = QLabel()
            color_box.setFixedSize(14,14)
            color_box.setStyleSheet(f"background-color: {settings['color'].name()}; border: 1px solid {self.theme.border_strong}; border-radius: 0px;")
            box = QCheckBox(label)
            box.setChecked(settings["enabled"])

            def toggle(v, lab=label):
                self.direct_relation_types[lab]["enabled"] = bool(v)

            box.stateChanged.connect(toggle)
            row_layout.addWidget(color_box)
            row_layout.addWidget(box)
            rel_section.content_layout.addWidget(row)
            tau_label = QLabel(f"{label} τ ≥ {settings['tau']:.2f}")
            tau_label.setWordWrap(True)
            rel_section.content_layout.addWidget(tau_label)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(100)
            slider.setValue(int(settings["tau"] * 100))

            def change(v, lab=label, lbl=tau_label):
                tau = v / 100
                if tau > 1:
                    tau = 1
                self.direct_relation_types[lab]["tau"] = tau
                lbl.setText(f"{lab} τ ≥ {tau:.2f}")

            slider.valueChanged.connect(change)
            rel_section.content_layout.addWidget(slider)

        merge_row, merge_checkbox = self._make_wrapping_checkbox("Merge Co-occurrence Episodes", self.enable_connection_merge)

        def toggle_merge(v):
            self.enable_connection_merge = bool(v)

        merge_checkbox.stateChanged.connect(toggle_merge)
        rel_section.content_layout.addWidget(merge_row)
        sh_section = CollapsibleSection("Relevance Filters")
        self.right_layout.addWidget(sh_section)
        sh_layout = sh_section.content_layout
        hide_row, hide_checkbox = self._make_wrapping_checkbox("Enable Episode Hiding (SUBEPISODE / SUBSUME / REORDER)", self.enable_episode_hiding)

        def toggle_hide(v):
            self.enable_episode_hiding = bool(v)

        hide_checkbox.stateChanged.connect(toggle_hide)
        sh_layout.addWidget(hide_row)
        subep_label = QLabel(f"SUBEP ≥ {self.T_SUBEP:.2f}")
        subep_label.setWordWrap(True)
        sh_layout.addWidget(subep_label)
        subep_slider = QSlider(Qt.Orientation.Horizontal)
        subep_slider.setMinimum(0)
        subep_slider.setMaximum(100)
        subep_slider.setValue(int(self.T_SUBEP * 100))

        def subep_changed(v):
            self.T_SUBEP = v / 100
            subep_label.setText(f"SUBEP ≥ {self.T_SUBEP:.2f}")

        subep_slider.valueChanged.connect(subep_changed)
        sh_layout.addWidget(subep_slider)
        subsume_label = QLabel(f"SUBSUME ≥ {self.T_SUBSUME:.2f}")
        subsume_label.setWordWrap(True)
        sh_layout.addWidget(subsume_label)
        subsume_slider = QSlider(Qt.Orientation.Horizontal)
        subsume_slider.setMinimum(0)
        subsume_slider.setMaximum(100)
        subsume_slider.setValue(int(self.T_SUBSUME * 100))

        def subsume_changed(v):
            self.T_SUBSUME = v / 100
            subsume_label.setText(f"SUBSUME ≥ {self.T_SUBSUME:.2f}")

        subsume_slider.valueChanged.connect(subsume_changed)
        sh_layout.addWidget(subsume_slider)
        reorder_label = QLabel(f"REORDER ≥ {self.T_REORDER:.2f}")
        reorder_label.setWordWrap(True)
        sh_layout.addWidget(reorder_label)
        reorder_slider = QSlider(Qt.Orientation.Horizontal)
        reorder_slider.setMinimum(0)
        reorder_slider.setMaximum(100)
        reorder_slider.setValue(int(self.T_REORDER * 100))

        def reorder_changed(v):
            self.T_REORDER = v / 100
            reorder_label.setText(f"REORDER ≥ {self.T_REORDER:.2f}")

        reorder_slider.valueChanged.connect(reorder_changed)
        sh_layout.addWidget(reorder_slider)
        apply_button = QPushButton("Apply Filters")
        apply_button.setObjectName("primaryButton")
        apply_button.setMinimumHeight(34)
        apply_button.clicked.connect(self.apply_filters)
        refresh_button = QPushButton("Refresh View")
        refresh_button.setMinimumHeight(34)
        refresh_button.clicked.connect(self.refresh_view)
        reset_button = QPushButton("Reset View")
        reset_button.setObjectName("dangerButton")
        reset_button.setMinimumHeight(34)
        reset_button.clicked.connect(self.reset_view)
        self.right_layout.addSpacing(10)
        self.right_layout.addWidget(apply_button)
        self.right_layout.addWidget(refresh_button)
        self.right_layout.addWidget(reset_button)
        self.right_layout.addStretch()

    def apply_filters(self):

        self.show_struct_activity_mark = self.show_act_mark.isChecked()

        self.show_struct_episode_mark = self.show_ep_mark.isChecked()

        self._save_current_filter_state()
        self._restore_original_merge_state()
        self._reapply_active_relation()

        if self.enable_connection_merge:
            self.merge_connection_episodes()

        self.build_visualization()
        self._ensure_lookup_integrity()

    def _compute_structured_activities(self):

        self.activity_struct_tau_map = {}
        for relation in self.tagRelations:

            label, activity, data = relation
            if label == "STRUCT":
                tau = data.get("tau_avg", 0.0)
                self.activity_struct_tau_map[activity] = tau

        self.structured_activities = {
            act
            for act, tau in self.activity_struct_tau_map.items()
            if tau >= self.activity_struct_tau
        }
    
    def _relation_tooltip_html(self, label, value):
        try:
            value_str = f"{float(value):.2f}"
        except (TypeError, ValueError):
            value_str = str(value)
        return (
            f"<b>{label}</b>: {value_str}"
            "</div>"
        )

    def _draw_direct_relations_safe(self):
        try:
            self._draw_direct_relations()
        except Exception:
            import traceback
            traceback.print_exc()

    def _draw_direct_relations(self):

        for item in self.direct_relation_items:
            try:
                self.scene.removeItem(item)
            except:
                pass

        self.direct_relation_items.clear()

        ep_map = {
            self._episode_key(item.raw_data_org): item
            for item in self.episode_items
        }

        self.direct_relation_items = []

        pairs = {}

        for label, ep1, ep2, tau in self.directRelations:

            settings = self.direct_relation_types.get(label)
            EPSILON = 1e-6

            if not settings or not settings["enabled"]:
                continue

            if tau + EPSILON < settings["tau"]:
                continue

            key1 = self._episode_key(ep1)
            key2 = self._episode_key(ep2)

            if key1 not in ep_map or key2 not in ep_map:
                continue

            pair_key = tuple(sorted((key1, key2)))
            pairs.setdefault(pair_key, []).append((label, ep1, ep2, tau))

        for pair_key, relations in pairs.items():

            key1, key2 = pair_key
            item1 = ep_map[key1]
            item2 = ep_map[key2]
            item1.prepareGeometryChange()
            item2.prepareGeometryChange()
            p1, p2 = self._episode_connection_points(item1, item2)
            lane_map = {}
            side_index = 1
            relations.sort(key=lambda r: r[0])

            for (label, ep1, ep2, tau) in relations:
                if label == "Co-occurrence":
                    lane_map[(label, id(ep1), id(ep2))] = 0
                else:
                    lane = side_index
                    if side_index % 2 == 0:
                        lane = -(side_index // 2)
                    else:
                        lane = (side_index + 1) // 2

                    lane_map[(label, id(ep1), id(ep2))] = lane
                    side_index += 1

            n_relations = len(relations)

            for idx, (label, ep1, ep2, tau) in enumerate(relations):

                settings = self.direct_relation_types[label]
                color = settings["color"]
                actual_k1 = self._episode_key(ep1)
                actual_k2 = self._episode_key(ep2)

                if label == "Dependency":
                    start_item = ep_map[actual_k1]
                    end_item = ep_map[actual_k2]
                    start, end = self._episode_connection_points(start_item, end_item)
                else:
                    if (actual_k1, actual_k2) == (key1, key2):
                        start, end = p1, p2
                    else:
                        start, end = p2, p1

                lane = lane_map[(label, id(ep1), id(ep2))]

                if n_relations <= 1:
                    label_t = 0.5
                else:
                    span_start, span_end = 0.3, 0.7
                    label_t = span_start + (span_end - span_start) * idx / (n_relations - 1)

                path, label_pos, angle = self._build_relation_curve(
                    p1, p2, lane, draw_start=start, draw_end=end, label_t=label_t
                )

                if label == "Co-occurrence":
                    pen = QPen(color, 2.5)

                    item = self.scene.addPath(path, pen)
                    item.setZValue(-10)
                    item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                    item.relation_keys = (actual_k1, actual_k2)
                    item.setToolTip(self._relation_tooltip_html(label, tau))

                    self.direct_relation_items.append(item)

                elif label == "Dependency":
                    pen = QPen(color, 2.5)
                    pen.setStyle(Qt.PenStyle.DashLine)
                    pen.setDashPattern([10, 4])

                    arrow = EpisodeRelationArrow(path, color, theme=self.theme)
                    arrow.setPen(pen)
                    arrow.set_path(path)
                    arrow.setZValue(-9)
                    arrow.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                    arrow.relation_keys = (actual_k1, actual_k2)
                    arrow.setToolTip(self._relation_tooltip_html(label, tau))

                    self.scene.addItem(arrow)
                    self.direct_relation_items.append(arrow)

                elif label == "Exclusion":
                    pen = QPen(color, 2)
                    pen.setStyle(Qt.PenStyle.DotLine)
                    pen.setDashPattern([2, 8])

                    item = self.scene.addPath(path, pen)
                    item.setZValue(-10)
                    item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                    item.relation_keys = (actual_k1, actual_k2)
                    item.setToolTip(self._relation_tooltip_html(label, tau))

                    self.direct_relation_items.append(item)

                display_tau = 1.0 if abs(tau - 1.0) < 1e-6 else min(tau, 0.99)

                text = _OutlinedTextItem(f"{display_tau:.2f}", color)
                text.setRotation(angle)
                text.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                text.setToolTip(self._relation_tooltip_html(label, tau))
                text.setPos(label_pos)
                text.setZValue(-5)
                text.relation_keys = (actual_k1, actual_k2)
                self.scene.addItem(text)
                self.direct_relation_items.append(text)


    def _build_relation_curve(self, p1, p2, lane, draw_start=None, draw_end=None, label_t=0.5):
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()

        length = math.hypot(dx, dy)
        if length == 0:
            length = 1

        ux = dx / length
        uy = dy / length
        nx = -uy
        ny = ux
        lane_width = 18
        offset = lane * lane_width
        mid = QPointF((p1.x() + p2.x()) / 2,(p1.y() + p2.y()) / 2)
        curvature_strength = 1.2
        control = QPointF(mid.x() + nx * offset * curvature_strength,mid.y() + ny * offset * curvature_strength)
        start = draw_start if draw_start is not None else p1
        end = draw_end if draw_end is not None else p2
        path = QPainterPath(start)
        path.quadTo(control, end)
        t = label_t
        label_pos = path.pointAtPercent(t)

        angle_rad = math.atan2(
            path.pointAtPercent(min(t + 0.01, 1.0)).y() - label_pos.y(),
            path.pointAtPercent(min(t + 0.01, 1.0)).x() - label_pos.x()
        )

        angle_deg = math.degrees(angle_rad)
        return path, label_pos, angle_deg

    def _episode_connection_points(self, item1, item2):
        r1 = item1.sceneBoundingRect()
        r2 = item2.sceneBoundingRect()

        c1 = r1.center()
        c2 = r2.center()

        dx = c2.x() - c1.x()
        dy = c2.y() - c1.y()

        def anchor(rect, dx, dy, is_source=True):
            if abs(dx) > abs(dy):
                if dx > 0:
                    return QPointF(rect.right(), rect.center().y()) if is_source else QPointF(rect.left(), rect.center().y())
                else:
                    return QPointF(rect.left(), rect.center().y()) if is_source else QPointF(rect.right(), rect.center().y())
            else:
                if dy > 0:
                    return QPointF(rect.center().x(), rect.bottom()) if is_source else QPointF(rect.center().x(), rect.top())
                else:
                    return QPointF(rect.center().x(), rect.top()) if is_source else QPointF(rect.center().x(), rect.bottom())

        p1 = anchor(r1, dx, dy, True)
        p2 = anchor(r2, dx, dy, False)

        margin = 6
        length = math.hypot(dx, dy)
        if length > 0:
            ux = dx / length
            uy = dy / length
            p1 = QPointF(p1.x() + ux * margin, p1.y() + uy * margin)
            p2 = QPointF(p2.x() - ux * margin, p2.y() - uy * margin)

        return p1, p2

    def _focus_episode(self, episode_item_or_items):
        if isinstance(episode_item_or_items, (list, set, tuple, frozenset)):
            focus_items = list(episode_item_or_items)
        else:
            focus_items = [episode_item_or_items]

        if not focus_items:
            return None

        focus_keys = frozenset(
            self._episode_key(ep.raw_data_org) for ep in focus_items
        )

        if self.focused_episode_keys == focus_keys:
            self.focused_episode_keys = None
            self.apply_filters()
            return None

        self.focused_episode_keys = focus_keys

        for ep in self.episode_items:
            ep.setOpacity(0.25)

        for rel in self.direct_relation_items:
            rel.setOpacity(0.15)

        for ep in focus_items:
            ep.setOpacity(1.0)

        connected = set()

        for label, ep1, ep2, tau in self.directRelations:

            settings = self.direct_relation_types.get(label)

            if not settings or not settings["enabled"]:
                continue

            rounded_tau = round(tau, 2)
            threshold = round(settings["tau"], 2)

            if rounded_tau < threshold:
                continue

            k1 = self._episode_key(ep1)
            k2 = self._episode_key(ep2)

            if k1 in focus_keys:
                connected.add(k2)

            if k2 in focus_keys:
                connected.add(k1)

        connected -= focus_keys

        for ep in self.episode_items:

            k = self._episode_key(ep.raw_data_org)

            if k in connected:
                ep.setOpacity(1.0)

        for item in self.direct_relation_items:
            if not hasattr(item,"relation_keys"):
                continue

            k1,k2 = item.relation_keys

            if ((k1 in focus_keys and k2 in connected) or
                (k2 in focus_keys and k1 in connected) or
                (k1 in focus_keys and k2 in focus_keys)):
                item.setOpacity(1.0)

    def _restore_original_merge_state(self):

        if self.original_episodes is None:
            return False

        self.episodes = list(self.original_episodes)
        self.directRelations = list(self.original_direct_relations)

        if self.original_show_hide_relations is not None:
            self.showHideRelations = list(self.original_show_hide_relations)

        if self.original_episode_lookup is not None:
            self._episode_lookup = copy.deepcopy(self.original_episode_lookup)

        if self.original_episode_occurrences is not None:
            self.episode_occurrences = dict(self.original_episode_occurrences)

        if self.original_occurrence_sets is not None:
            self.occurrence_sets = dict(self.original_occurrence_sets)

        return True

    def reset_episode_merges(self):

        if not self._restore_original_merge_state():
            return

        self.build_visualization()

    def merge_connection_episodes(self, restrict_keys=None):

        if self.original_episodes is None:
            self.original_episodes = list(self.episodes)
            self.original_direct_relations = list(self.directRelations)
            self.original_show_hide_relations = list(self.showHideRelations)
            self.original_episode_lookup = copy.deepcopy(self._episode_lookup)
            self.original_episode_occurrences = dict(self.episode_occurrences)
            self.original_occurrence_sets = dict(self.occurrence_sets)

        self._restore_original_merge_state()

        if restrict_keys is not None:
            graph = {
                self._episode_key(ep): set()
                for ep in self.episodes
                if self._episode_key(ep) in restrict_keys
            }
        else:
            graph = {self._episode_key(ep): set() for ep in self.episodes}

        threshold = self.direct_relation_types["Co-occurrence"]["tau"]

        for label, ep1, ep2, tau in self.directRelations:
            if label != "Co-occurrence" or tau < threshold:
                continue

            k1 = self._episode_key(ep1)
            k2 = self._episode_key(ep2)

            if k1 not in graph or k2 not in graph:
                continue

            graph[k1].add(k2)
            graph[k2].add(k1)

        visited = set()
        components = []

        for node in graph:
            if node in visited:
                continue

            stack = [node]
            comp = []

            while stack:
                cur = stack.pop()
                if cur in visited:
                    continue

                visited.add(cur)
                comp.append(cur)
                stack.extend(graph[cur])

            if len(comp) > 1:
                components.append(comp)

        if not components:
            return

        key_to_episode = {self._episode_key(ep): ep for ep in self.episodes}

        new_episodes = []
        removed_keys = set()
        merged_hidden_map = {}
        for comp in components:

            nodes = set()
            edges = []

            for key in comp:
                ep = key_to_episode.get(key)
                if not ep:
                    continue

                acts, trans = ep
                nodes.update(acts)
                edges.extend(trans)

            if len(nodes) < 2:
                continue

            graph_act = {n: set() for n in nodes}
            indeg = {n: 0 for n in nodes}

            for a, b in edges:
                if b not in graph_act[a]:
                    graph_act[a].add(b)
                    indeg[b] += 1

            queue = [n for n in indeg if indeg[n] == 0]
            ordered = []

            while queue:
                queue.sort()
                n = queue.pop(0)
                ordered.append(n)

                for nxt in graph_act[n]:
                    indeg[nxt] -= 1
                    if indeg[nxt] == 0:
                        queue.append(nxt)

            if len(ordered) != len(nodes):
                continue

            merged_trans = [(ordered[i], ordered[i+1]) for i in range(len(ordered)-1)]
            merged_ep = (ordered, merged_trans)
            merged_key = self._episode_key(merged_ep)
            merged_occurrences = self._compute_merged_occurrence_set(comp)
            self.occurrence_sets[merged_key] = merged_occurrences
            merged_frequency = 0.0
            if self.total_traces > 0:
                merged_frequency = (len(merged_occurrences) / self.total_traces)
            self.episode_occurrences[merged_key] = merged_frequency

            new_episodes.append(merged_ep)
            merged_hidden = []
            seen_keys = set()

            for old_key in comp:

                old_ep = key_to_episode.get(old_key)

                if not old_ep:
                    continue

                if old_key not in seen_keys:

                    merged_hidden.append({"label": "SUBSUME","tau": 1.0,"episode": old_ep,"source": "merge connection"})

                    seen_keys.add(old_key)

                old_hidden = self._episode_lookup.get(old_key, {}).get("hidden", [])

                for h in old_hidden:

                    ep = h.get("episode")

                    if not ep:
                        continue

                    ep_key = self._episode_key(ep)

                    if ep_key in seen_keys:
                        continue

                    seen_keys.add(ep_key)
                    merged_hidden.append({**h, "source": h.get("source", "merge connection")})
            merged_hidden_map[self._episode_key(merged_ep)] = merged_hidden

            for key in comp:
                removed_keys.add(key)

        self.episodes = [
            ep for ep in self.episodes
            if self._episode_key(ep) not in removed_keys
        ]

        self.episodes.extend(new_episodes)
        self._cleanup_episode_occurrences()

        for ep in new_episodes:
            key = self._episode_key(ep)
            self._episode_lookup[key] = {"data": ep,"hidden": merged_hidden_map.get(key, [])}

    def _merge_relations_activity(self, mapping):

        def resolve(key):
            return mapping.get(key, key)

        relation_acc = {}

        for label, ep1, ep2, tau in self.directRelations:

            k1 = resolve(self._episode_key(ep1))
            k2 = resolve(self._episode_key(ep2))

            if k1 == k2:
                continue

            key = (label, k1, k2)

            if key not in relation_acc:
                relation_acc[key] = []

            relation_acc[key].append(tau)

        key_to_episode = {
            self._episode_key(ep): ep
            for ep in self.episodes
        }

        new_direct = []

        for (label, k1, k2), taus in relation_acc.items():
            avg_tau = sum(taus) / len(taus)

            if k1 in key_to_episode and k2 in key_to_episode:
                new_direct.append((
                    label,
                    key_to_episode[k1],
                    key_to_episode[k2],
                    avg_tau
                ))

        self.directRelations = new_direct

    def _apply_activity_relation(self, relation):

        label = relation[0].lower()
        self._process_show_hide_relations()

        if label == "choice":
            _, acts, tau = relation
            acts = set(acts)
            merged_name = f"×{{{','.join(sorted(acts))}}}"
            require_all_variants = True

        elif label == "update":
            _, act1, act2, tau = relation
            acts = {act1, act2}
            merged_name = f"UP({act1},{act2})"
            require_all_variants = True

        else:
            return self.episodes, self.directRelations

        structure_groups = {}

        placeholder = "__CHOICE__" if label == "choice" else "__UPDATE__"

        visible_keys = {
            self._episode_key(ep)
            for ep in self.visibleEpisodes
        }

        for ep in self.visibleEpisodes:

            old_key = self._episode_key(ep)

            if old_key not in visible_keys:
                continue

            activities, transitions = ep

            if not any(a in acts for a in activities):
                continue

            mapped_trans = []

            for s, t in transitions:

                ns = placeholder if s in acts else s
                nt = placeholder if t in acts else t

                if ns != nt:
                    mapped_trans.append((ns, nt))

            mapped_trans = tuple(sorted(set(mapped_trans)))

            mapped_nodes = {
                placeholder if a in acts else a
                for a in activities
            }

            skeleton_key = (
                tuple(sorted(mapped_nodes)),
                mapped_trans
            )

            if skeleton_key not in structure_groups:
                structure_groups[skeleton_key] = []

            structure_groups[skeleton_key].append(ep)

        valid_groups = []

        for skeleton_key, eps in structure_groups.items():

            observed_variants = set()

            for ep in eps:
                activities, _ = ep
                present = acts.intersection(set(activities))
                if len(present) == 1:
                    observed_variants.update(present)

            if require_all_variants:
                if observed_variants == acts:
                    valid_groups.append((skeleton_key, eps))
            else:
                if observed_variants:
                    valid_groups.append((skeleton_key, eps))

        mapping = {}
        derived_groups = {}
        final_new_episodes = []

        for skeleton_key, originals in valid_groups:
            rep_ep = originals[0]
            activities, transitions = rep_ep

            new_acts = []
            for a in activities:
                if a in acts:
                    if merged_name not in new_acts:
                        new_acts.append(merged_name)
                else:
                    new_acts.append(a)

            new_trans = []
            for s, t in transitions:
                ns = merged_name if s in acts else s
                nt = merged_name if t in acts else t
                if ns != nt and (ns, nt) not in new_trans:
                    new_trans.append((ns, nt))

            merged_ep = (new_acts, new_trans)
            final_new_episodes.append(merged_ep)
            new_key = self._episode_key(merged_ep)
            derived_groups[new_key] = originals

            for old_ep in originals:
                old_key = self._episode_key(old_ep)
                mapping[old_key] = new_key

        for new_key, originals in derived_groups.items():
            union_occurrences = set()
            has_any_occurrence_data = False

            for ep in originals:
                old_key = self._episode_key(ep)
                occ_set = self.occurrence_sets.get(old_key)
                if occ_set:
                    has_any_occurrence_data = True
                    union_occurrences |= set(occ_set)

            if has_any_occurrence_data:
                self.occurrence_sets[new_key] = union_occurrences

                if self.total_traces:
                    self.episode_occurrences[new_key] = (
                        len(union_occurrences) / self.total_traces
                    )
                else:
                    self.episode_occurrences[new_key] = len(union_occurrences)
            else:
                max_freq = 0

                for ep in originals:
                    old_key = self._episode_key(ep)
                    freq = self.episode_occurrences.get(old_key, 0)
                    max_freq = max(max_freq, freq)

                self.episode_occurrences[new_key] = max_freq

        replaced_keys = set(mapping.keys())

        self.episodes = [
            ep for ep in self.episodes
            if self._episode_key(ep) not in replaced_keys
        ]

        for new_ep in final_new_episodes:
            new_key = self._episode_key(new_ep)
            merged_hidden = []
            seen_keys = set()

            for old_ep in derived_groups[new_key]:
                old_key = self._episode_key(old_ep)
                if old_key not in seen_keys:
                    merged_hidden.append({
                        "label": "SUBSUME",
                        "tau": 1.0,
                        "episode": old_ep,
                        "source": "merge act_relation"
                    })
                    seen_keys.add(old_key)

                old_hidden = self._episode_lookup.get(old_key, {}).get("hidden", [])

                for h in old_hidden:
                    ep = h.get("episode")

                    if not ep:
                        continue
                    ep_key = self._episode_key(ep)
                    if ep_key in seen_keys:
                        continue

                    seen_keys.add(ep_key)
                    merged_hidden.append({**h, "source": h.get("source", "merge act_relation")})

            self._episode_lookup[new_key] = {
                "data": new_ep,
                "hidden": merged_hidden
            }

        self.episodes.extend(final_new_episodes)
        self._cleanup_episode_occurrences()
        self._merge_relations_activity(mapping)

        return self.episodes, self.directRelations
    
    def _ensure_lookup_integrity(self):

        if not hasattr(self, "_episode_lookup") or self._episode_lookup is None:
            self._episode_lookup = {}
        for ep in self.episodes:
            key = self._episode_key(ep)
            if key not in self._episode_lookup:
                self._episode_lookup[key] = {
                    "data": ep,
                    "hidden": []
                }
            else:
                self._episode_lookup[key].setdefault("hidden", [])


    def _save_current_filter_state(self):

        self.saved_filter_state = {
            "activity_struct_tau": self.activity_struct_tau,
            "episode_struct_ratio": self.episode_struct_ratio,
            "show_struct_episode_mark": self.show_ep_mark.isChecked(),
            "show_struct_activity_mark": self.show_act_mark.isChecked(),
            "only_show_structured_episodes":
                self.only_show_structured_episodes,

            "enable_connection_merge":
                self.enable_connection_merge,

            "enable_episode_hiding":
                self.enable_episode_hiding,

            "T_SUBEP": self.T_SUBEP,
            "T_SUBSUME": self.T_SUBSUME,
            "T_REORDER": self.T_REORDER,

            "direct_relation_types": {
                k: {
                    "enabled": v["enabled"],
                    "tau": v["tau"]
                }
                for k, v in self.direct_relation_types.items()
            }
        }
        
    def _restore_saved_filter_state(self):

        if not self.saved_filter_state:
            return
        s = self.saved_filter_state
        self.activity_struct_tau = s["activity_struct_tau"]
        self.episode_struct_ratio = s["episode_struct_ratio"]
        self.show_struct_episode_mark = s["show_struct_episode_mark"]
        self.show_struct_activity_mark = s["show_struct_activity_mark"]
        self.only_show_structured_episodes = s["only_show_structured_episodes"]
        self.enable_connection_merge = s["enable_connection_merge"]
        self.enable_episode_hiding = s["enable_episode_hiding"]

        self.T_SUBEP = s["T_SUBEP"]
        self.T_SUBSUME = s["T_SUBSUME"]
        self.T_REORDER = s.get("T_REORDER", 0.8)

        for label, vals in s["direct_relation_types"].items():

            if label not in self.direct_relation_types:
                continue

            self.direct_relation_types[label]["enabled"] = vals["enabled"]
            self.direct_relation_types[label]["tau"] = vals["tau"]
            
    
    def refresh_view(self):
        self._restore_saved_filter_state()
        self._restore_original_merge_state()
        self._reapply_active_relation()
        if self.enable_connection_merge:
            self.merge_connection_episodes()
        self.build_visualization()
        self._ensure_lookup_integrity()

    def reset_view(self):
        self.manual_episode_positions.clear()
        self.selected_episode_keys.clear()
        self.refresh_view()
        self._fit_view_to_content()
        
    def _store_episode_position(self, episode_item):
        key = self._episode_key(episode_item.raw_data_org)
        self.manual_episode_positions[key] = episode_item.pos()
        self.relation_update_timer.start(16)
    
    def _reapply_active_relation(self):
        if not self.active_relation:
            return
        self.episodes, self.directRelations = self._apply_activity_relation(self.active_relation)
    
    def toggle_episode_selection(self, episode_item):
        key = self._episode_key(episode_item.raw_data_org)
        if key in self.selected_episode_keys:
            self.selected_episode_keys.remove(key)
        else:
            self.selected_episode_keys.add(key)

        episode_item.set_selected_state(key in self.selected_episode_keys)

        self._update_selection_toolbar()

    def clear_episode_selection(self):
        self.selected_episode_keys.clear()
        for item in self.episode_items:
            item.set_selected_state(False)

        if self.focused_episode_keys is not None:
            self.focused_episode_keys = None
            for ep in self.episode_items:
                ep.setOpacity(1.0)
            for rel in self.direct_relation_items:
                rel.setOpacity(1.0)

        self._update_selection_toolbar()

    def get_selected_episode_items(self):
        result = []
        for item in self.episode_items:
            key = self._episode_key(item.raw_data_org)
            if key in self.selected_episode_keys:
                result.append(item)
        return result
    
    def _update_selection_toolbar(self):
        if self.selected_episode_keys:
            self.selection_toolbar.show()
        else:
            self.selection_toolbar.hide()
    
    def focus_selected_episodes(self):
        selected = self.get_selected_episode_items()
        if not selected:
            return
        self._focus_episode(selected)

    def print_selected_relations(self):
        selected_keys = set(self.selected_episode_keys)

        if not selected_keys:
            print("No episodes selected - nothing to print.")
            return

        selected_items = self.get_selected_episode_items()

        print("=" * 70)
        print(f"Selected episodes ({len(selected_items)}):")
        for item in selected_items:
            print(f"  - {self._format_episode(item.raw_data_org)}")
        print("-" * 70)
        print("Relations where all endpoints are within the selection:")

        found = False
        for relation_list in (self.directRelations, self.showHideRelations):
            for label, ep1, ep2, value in relation_list:
                key1 = self._episode_key(ep1)
                key2 = self._episode_key(ep2)
                if key1 in selected_keys and key2 in selected_keys:
                    found = True
                    try:
                        value_str = f"{float(value):.4f}"
                    except (TypeError, ValueError):
                        value_str = str(value)
                    if label == "Dependency":
                        print(f"  [{label}] {self._format_episode(ep1)}  ->  "
                            f"{self._format_episode(ep2)}   value={value_str}")
                    else:
                        print(f"  [{label}] {self._format_episode(ep1)}  <->  "
                            f"{self._format_episode(ep2)}   value={value_str}")

        if not found:
            print("  (none found - no relation exists where every endpoint "
                  "is part of the current selection)")
        print("=" * 70)

    def move_selected_group(self, moved_item, delta):
        if self._group_moving:
            return

        moved_key = self._episode_key(moved_item.raw_data_org)
        if moved_key not in self.selected_episode_keys:
            return

        self._group_moving = True
        try:
            for item in self.get_selected_episode_items():
                if item is moved_item:
                    continue
                item.setPos(item.pos() + delta)
        finally:
            self._group_moving = False
    
    def merge_selected_episodes(self):
        selected = self.get_selected_episode_items()
        if not selected:
            return

        selected_keys = {
            self._episode_key(ep.raw_data_org) for ep in selected
        }

        self.merge_connection_episodes(restrict_keys=selected_keys)
        self.selected_episode_keys.clear()
        self._update_selection_toolbar()

        self.build_visualization()
        self._ensure_lookup_integrity()
    
    def _cleanup_episode_occurrences(self):
        valid_keys = {self._episode_key(ep) for ep in self.episodes}
        self.episode_occurrences = {k: v for k, v in self.episode_occurrences.items() if k in valid_keys}
        self.occurrence_sets = {k: v for k, v in self.occurrence_sets.items() if k in valid_keys}
    
    def _compute_merged_occurrence_set(self, component_keys):
        occurrence_sets = []
        for key in component_keys:
            occ = self.occurrence_sets.get(key)
            if not occ:
                return set()
            occurrence_sets.append(set(occ))

        if not occurrence_sets:
            return set()

        merged_occurrences = set.intersection(*occurrence_sets)

        return merged_occurrences