#DO NOT USE THIS LAYOUT FOR ANALYSIS
from .base_layout import BaseLayout

class GridLayout(BaseLayout):

    def layout(self, visualizer, episode_items):
        if not episode_items:
            return
        view_width = visualizer.view.viewport().width()
        usable_width = max(1, view_width)
        avg_width = sum(ep.boundingRect().width() for ep in episode_items) / len(episode_items)
        sample_width = avg_width
        columns = max(1,int(usable_width // (sample_width + visualizer.EPISODE_SPACING_X)))
        x_start = visualizer.LEFT_EPISODE_GAP
        x = x_start
        y = 0
        col = 0
        row_height = 0
        for episode in episode_items:
            rect = episode.sceneBoundingRect()
            episode.setPos(x - rect.left(), y - rect.top())
            row_height = max(row_height, rect.height())
            col += 1
            if col >= columns:
                col = 0
                x = x_start
                y += row_height + visualizer.EPISODE_SPACING_Y
                row_height = 0
            else:
                x += rect.width() + visualizer.EPISODE_SPACING_X

        visualizer.scene.setSceneRect(visualizer.scene.itemsBoundingRect())