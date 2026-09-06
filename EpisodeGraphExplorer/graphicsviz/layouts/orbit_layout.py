from .base_layout import BaseLayout
import math

class OrbitLayout(BaseLayout):

    def layout(self, visualizer, episode_items):
        center_x = 400
        center_y = 300
        radius = 200

        for i, ep in enumerate(episode_items):
            angle = (i / len(episode_items)) * 2 * math.pi
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            ep.setPos(x, y)