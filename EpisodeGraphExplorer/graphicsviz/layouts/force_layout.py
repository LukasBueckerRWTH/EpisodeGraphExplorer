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
        
        self.w_cooccurrence = 3.0
        self.w_dependency = 1.0
        self.w_exclusion = 4.0

        self.k_exclusion = 0.02
        self.exclusion_range_factor = 3.0

    def layout(self, visualizer, episode_items, fixed_items=None):
        if not episode_items:
            return

        fixed = set(fixed_items or ())
        movable = [ep for ep in episode_items if ep not in fixed]
        if not movable:
            return

        pos = {}
        geo = {}
        for ep in episode_items:
            rect = ep.sceneBoundingRect()
            c = rect.center()
            pos[ep] = [ep.x(), ep.y()]
            geo[ep] = (rect.width() / 2, rect.height() / 2, c.x() - ep.x(), c.y() - ep.y())

        def center(ep):
            p = pos[ep]
            g = geo[ep]
            return p[0] + g[2], p[1] + g[3]

        base_x, base_y = 0.0, 0.0
        if fixed:
            base_x = max(center(f)[0] + geo[f][0] for f in fixed) + 100
            base_y = min(center(f)[1] - geo[f][1] for f in fixed)
        for i, ep in enumerate(movable):
            pos[ep] = [base_x + (i % 5) * 220, base_y + (i // 5) * 160]

        if fixed:
            fcs = [center(f) for f in fixed]
            grav_x = sum(c[0] for c in fcs) / len(fcs)
            grav_y = sum(c[1] for c in fcs) / len(fcs)
        else:
            grav_x = self.width / 2
            grav_y = self.height / 2

        ep_map = {visualizer._episode_key(ep.raw_data_org): ep for ep in episode_items}
        pair_relations = {}
        for label, ep1, ep2, tau in visualizer.directRelations:
            k1 = visualizer._episode_key(ep1)
            k2 = visualizer._episode_key(ep2)
            if k1 not in ep_map or k2 not in ep_map:
                continue
            pair_key = tuple(sorted((k1, k2)))
            if pair_key not in pair_relations:
                pair_relations[pair_key] = {"attract": 0.0, "repel": 0.0}

            if label == "Co-occurrence":
                pair_relations[pair_key]["attract"] += self.w_cooccurrence * tau

            elif label == "Dependency":
                pair_relations[pair_key]["attract"] += self.w_dependency * tau

            elif label == "Exclusion":
                pair_relations[pair_key]["repel"] += self.w_exclusion * tau

        velocities = {ep: [0.0, 0.0] for ep in movable}
        for _ in range(self.iterations):
            forces = {ep: [0.0, 0.0] for ep in episode_items}
            centers = {ep: center(ep) for ep in episode_items}
            for i, a in enumerate(episode_items):
                ax, ay = centers[a]
                for b in episode_items[i + 1:]:
                    if a in fixed and b in fixed:
                        continue
                    bx, by = centers[b]
                    dx = ax - bx
                    dy = ay - by
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
                if a in fixed and b in fixed:
                    continue
                ax, ay = centers[a]
                bx, by = centers[b]
                dx = bx - ax
                dy = by - ay
                dist = math.hypot(dx, dy) + 0.1
                size_a = max(geo[a][0], geo[a][1]) * 2
                size_b = max(geo[b][0], geo[b][1]) * 2                                     
                ideal_dist = (size_a + size_b) * 0.6 + self.padding
                f_attr = self.k_relation * rel["attract"] * (dist - ideal_dist)
                f_rep = self.k_repulsion * rel["repel"] / (dist * dist)
                if rel["repel"] > 0:
                    exclusion_range = ideal_dist * self.exclusion_range_factor
                    if dist < exclusion_range:
                        f_rep += self.k_exclusion * rel["repel"] * (exclusion_range - dist)
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

                ax, ay = centers[a]
                bx, by = centers[b]
                cluster_centers[a][0] += bx * weight
                cluster_centers[a][1] += by * weight
                cluster_centers[a][2] += weight
                cluster_centers[b][0] += ax * weight
                cluster_centers[b][1] += ay * weight
                cluster_centers[b][2] += weight

            for ep, (sx, sy, w) in cluster_centers.items():
                if w == 0:
                    continue
                ex, ey = centers[ep]
                scale = max(getattr(ep, "episode_scale", 1.0), 0.6)
                strength = 0.01 / scale
                forces[ep][0] += (sx / w - ex) * strength
                forces[ep][1] += (sy / w - ey) * strength

            for i, a in enumerate(episode_items):
                ax, ay = centers[a]
                for b in episode_items[i + 1:]:
                    if a in fixed and b in fixed:                         
                        continue
                    bx, by = centers[b]                      
                    dx = ax - bx
                    dy = ay - by
                    ovx = geo[a][0] + geo[b][0] - abs(dx)                                                            
                    ovy = geo[a][1] + geo[b][1] - abs(dy)
                    if ovx <= 0 or ovy <= 0:                            
                        continue                                     
                    scale_a = max(getattr(a, "episode_scale", 1.0), 0.6)
                    scale_b = max(getattr(b, "episode_scale", 1.0), 0.6)
                    size_factor = max(scale_a, scale_b)
                    gain = 1.2 + size_factor * 0.8
                    if ovx <= ovy:
                        force = (ovx + self.padding) * gain
                        fx = force if dx >= 0 else -force
                        fy = 0.0
                    else:
                        force = (ovy + self.padding) * gain
                        fx = 0.0
                        fy = force if dy >= 0 else -force
                    forces[a][0] += fx
                    forces[a][1] += fy
                    forces[b][0] -= fx
                    forces[b][1] -= fy
            for ep in movable:
                scale = max(getattr(ep, "episode_scale", 1.0), 0.6)
                mass = 1.0 + scale * 3.5
                center_bias = 1.0 + (scale - 1.0) * 2.5
                gravity = self.center_gravity * (1.0 + center_bias)
                ex, ey = centers[ep]                                          
                fx = forces[ep][0] + (grav_x - ex) * gravity
                fy = forces[ep][1] + (grav_y - ey) * gravity
                vx = (velocities[ep][0] + fx / mass) * self.damping
                vy = (velocities[ep][1] + fy / mass) * self.damping
                speed = math.hypot(vx, vy)
                if speed > self.max_speed:
                    vx = vx / speed * self.max_speed
                    vy = vy / speed * self.max_speed
                velocities[ep] = [vx, vy]
                pos[ep][0] += vx
                pos[ep][1] += vy                     
        self._resolve_collisions(episode_items, pos, geo, fixed)

        for ep in movable:
            ep.setPos(pos[ep][0], pos[ep][1])

        visualizer.scene.setSceneRect(visualizer.scene.itemsBoundingRect())

    def _resolve_collisions(self, episode_items, pos, geo, fixed, max_passes=50):
        for _ in range(max_passes):
            moved = False
            for i, a in enumerate(episode_items):
                a_fixed = a in fixed
                hwa, hha, oxa, oya = geo[a]
                for b in episode_items[i + 1:]:
                    b_fixed = b in fixed
                    if a_fixed and b_fixed:                                            
                        continue
                    hwb, hhb, oxb, oyb = geo[b]
                    dx = (pos[a][0] + oxa) - (pos[b][0] + oxb)
                    dy = (pos[a][1] + oya) - (pos[b][1] + oyb)            
                    ovx = hwa + hwb - abs(dx)
                    ovy = hha + hhb - abs(dy)
                    if ovx <= 0 or ovy <= 0:
                                    
                        continue

                    if ovx <= ovy:
                        shift = ovx + self.padding
                        sx = shift if dx >= 0 else -shift
                        sy = 0.0
                    else:
                        shift = ovy + self.padding
                        sx = 0.0
                        sy = shift if dy >= 0 else -shift
                    if a_fixed:
                        pos[b][0] -= sx
                        pos[b][1] -= sy
                    elif b_fixed:
                        pos[a][0] += sx
                        pos[a][1] += sy
                    else:
                        pos[a][0] += sx / 2
                        pos[a][1] += sy / 2
                        pos[b][0] -= sx / 2
                        pos[b][1] -= sy / 2
                    moved = True
            if not moved:
                break