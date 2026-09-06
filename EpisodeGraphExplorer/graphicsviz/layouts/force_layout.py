import math
from .base_layout import BaseLayout

class ForceLayout(BaseLayout):
    def __init__(self, iterations=60, width=1200, height=800):
        self.iterations = iterations
        self.width = width
        self.height = height

        #default parameters
        self.k_repulsion = 7500
        self.k_relation = 0.04
        self.center_gravity = 0.002
        self.damping = 0.85
        self.max_speed = 40.0
        self.padding = 15               

    def layout(self, visualizer, episode_items):
        if not episode_items:
            return

        for i, ep in enumerate(episode_items):
            if ep.pos().x() == 0 and ep.pos().y() == 0:
                ep.setPos((i % 5) * 220,(i // 5) * 160)

        ep_map = {visualizer._episode_key(ep.raw_data_org): ep for ep in episode_items}
        pair_relations = {}
        for label, ep1, ep2, tau in visualizer.directRelations:
            k1 = visualizer._episode_key(ep1)
            k2 = visualizer._episode_key(ep2)
            if k1 not in ep_map or k2 not in ep_map:
                continue
            pair_key = tuple(sorted((k1, k2)))
            if pair_key not in pair_relations:
                pair_relations[pair_key] = {"attract": 0.0,"repel": 0.0}

            if label == "Co-occurrence":
                pair_relations[pair_key]["attract"] += 1.5 * tau

            elif label == "Dependency":
                pair_relations[pair_key]["attract"] += 1.0 * tau

            elif label == "Exclusion":
                pair_relations[pair_key]["repel"] += 4 * tau
 
        velocities = {ep: [0.0, 0.0] for ep in episode_items}
        for _ in range(self.iterations):
            forces = {ep: [0.0, 0.0] for ep in episode_items}
            
            for i, a in enumerate(episode_items):
                rect_a = a.sceneBoundingRect()
                center_a = rect_a.center()

                for b in episode_items[i + 1:]:
                    rect_b = b.sceneBoundingRect()
                    center_b = rect_b.center()
                    dx = center_a.x() - center_b.x()
                    dy = center_a.y() - center_b.y()
                    dist = math.hypot(dx, dy) + 0.1
                    force = self.k_repulsion / (dist * dist)
                    fx = force * dx / dist
                    fy = force * dy / dist
                    forces[a][0] += fx
                    forces[a][1] += fy
                    forces[b][0] -= fx
                    forces[b][1] -= fy
          
            for (k1, k2), rel in pair_relations.items():
                a = ep_map[k1]
                b = ep_map[k2]
                dx = b.x() - a.x()
                dy = b.y() - a.y()
                dist = math.hypot(dx, dy) + 0.1
                rect_a = a.sceneBoundingRect()
                rect_b = b.sceneBoundingRect()
                size_a = max(rect_a.width(), rect_a.height())
                size_b = max(rect_b.width(), rect_b.height())
                ideal_dist = (size_a + size_b) * 0.6 + self.padding
                attract = rel["attract"]
                repel = rel["repel"]
                rect_a = a.sceneBoundingRect()
                rect_b = b.sceneBoundingRect()
                size_a = max(rect_a.width(), rect_a.height())
                size_b = max(rect_b.width(), rect_b.height())
                ideal_dist = (size_a + size_b) * 0.6 + self.padding
                f_attr = self.k_relation * attract * (dist - ideal_dist)
                f_rep = self.k_repulsion * repel / (dist * dist)
                scale_a = max(getattr(a, "episode_scale", 1.0), 0.6)
                scale_b = max(getattr(b, "episode_scale", 1.0), 0.6)
                size_factor = (scale_a + scale_b) * 0.5
                force = (f_attr * size_factor) - f_rep
                fx = force * dx / dist
                fy = force * dy / dist
                forces[a][0] += fx
                forces[a][1] += fy
                forces[b][0] -= fx
                forces[b][1] -= fy

            cluster_centers = {}
            for (k1, k2), rel in pair_relations.items():
                a = ep_map[k1]
                b = ep_map[k2]
                weight = rel["attract"]
                if weight <= 0:
                    continue

                if a not in cluster_centers:
                    cluster_centers[a] = [0.0, 0.0, 0.0]  # x_sum, y_sum, total_w

                if b not in cluster_centers:
                    cluster_centers[b] = [0.0, 0.0, 0.0]

                cluster_centers[a][0] += b.x() * weight
                cluster_centers[a][1] += b.y() * weight
                cluster_centers[a][2] += weight
                cluster_centers[b][0] += a.x() * weight
                cluster_centers[b][1] += a.y() * weight
                cluster_centers[b][2] += weight

            for ep, (sx, sy, w) in cluster_centers.items():
                if w == 0:
                    continue
                cx = sx / w
                cy = sy / w
                dx = cx - ep.x()
                dy = cy - ep.y()
                scale = max(getattr(ep, "episode_scale", 1.0), 0.6)
                strength = 0.01 / scale
                forces[ep][0] += dx * strength
                forces[ep][1] += dy * strength

            for i, a in enumerate(episode_items):
                for b in episode_items[i + 1:]:
                    rect_a = a.sceneBoundingRect()
                    rect_b = b.sceneBoundingRect()
                    if not rect_a.intersects(rect_b):
                        continue
                    center_a = rect_a.center()
                    center_b = rect_b.center()
                    dx = center_a.x() - center_b.x()
                    dy = center_a.y() - center_b.y()
                    dist = math.hypot(dx, dy)
                    if dist < 0.01:
                        dx = 1.0
                        dy = 0.0
                        dist = 1.0

                    overlap_x = (rect_a.width() + rect_b.width()) / 2 - abs(dx)
                    overlap_y = (rect_a.height() + rect_b.height()) / 2 - abs(dy)
                    overlap = max(overlap_x, overlap_y)

                    if overlap <= 0:
                        continue

                    overlap += self.padding
                    scale_a = max(getattr(a, "episode_scale", 1.0), 0.6)
                    scale_b = max(getattr(b, "episode_scale", 1.0), 0.6)
                    size_factor = max(scale_a, scale_b)
                    force = overlap * (1.2 + size_factor * 0.8)
                    fx = force * dx / dist
                    fy = force * dy / dist
                    forces[a][0] += fx
                    forces[a][1] += fy
                    forces[b][0] -= fx
                    forces[b][1] -= fy

            cx = self.width / 2
            cy = self.height / 2
            for ep in episode_items:
                dx = cx - ep.x()
                dy = cy - ep.y()
                forces[ep][0] += dx * self.center_gravity
                forces[ep][1] += dy * self.center_gravity
            
            for ep in episode_items:

                scale = max(getattr(ep, "episode_scale", 1.0), 0.6)
                mass = 1.0 + scale * 3.5
                center_bias = 1.0 + (scale - 1.0) * 2.5
                cx = self.width / 2
                cy = self.height / 2
                dx_c = cx - ep.x()
                dy_c = cy - ep.y()
                forces[ep][0] += dx_c * self.center_gravity * center_bias
                forces[ep][1] += dy_c * self.center_gravity * center_bias
                vx = (velocities[ep][0] + forces[ep][0] / mass) * self.damping
                vy = (velocities[ep][1] + forces[ep][1] / mass) * self.damping
                speed = math.hypot(vx, vy)
                if speed > self.max_speed:
                    vx = vx / speed * self.max_speed
                    vy = vy / speed * self.max_speed

                velocities[ep] = [vx, vy]
                ep.setPos(ep.x() + vx, ep.y() + vy)

        for _ in range(2):
            self._resolve_collisions(episode_items)
        
        visualizer.scene.setSceneRect(visualizer.scene.itemsBoundingRect())
    
    def _resolve_collisions(self, episode_items):
        for _ in range(3):
            for i, a in enumerate(episode_items):
                for b in episode_items[i + 1:]:

                    rect_a = a.sceneBoundingRect()
                    rect_b = b.sceneBoundingRect()
                    if not rect_a.intersects(rect_b):
                        continue
                    center_a = rect_a.center()
                    center_b = rect_b.center()
                    dx = center_a.x() - center_b.x()
                    dy = center_a.y() - center_b.y()
                    dist = math.hypot(dx, dy)
                    if dist < 0.01:
                        dx = 1.0
                        dy = 0.0
                        dist = 1.0
                    overlap_x = (rect_a.width() + rect_b.width()) / 2 - abs(dx)
                    overlap_y = (rect_a.height() + rect_b.height()) / 2 - abs(dy)
                    overlap = max(overlap_x, overlap_y)
                    if overlap <= 0:
                        continue
                    overlap += self.padding
                    shift = overlap / 2
                    ux = dx / dist
                    uy = dy / dist
                    a.setPos(a.x() + ux * shift, a.y() + uy * shift)
                    b.setPos(b.x() - ux * shift, b.y() - uy * shift)