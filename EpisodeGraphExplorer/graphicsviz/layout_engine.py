from collections import defaultdict, deque

class LayoutEngine:
    V_SPACING = 80
    H_LAYER_SPACING = 80
    PADDING = 40

    def compute_layout(self, activities, transitions, scale=1.0):
        graph = defaultdict(list)
        indegree = {a: 0 for a in activities}
        for src, dst in transitions:
            graph[src].append(dst)
            indegree[dst] += 1
        layers = {}
        queue = deque()
        for a in activities:
            if indegree[a] == 0:
                queue.append((a, 0))

        while queue:
            node, layer = queue.popleft()
            layers[node] = max(layer, layers.get(node, 0))
            for nxt in graph[node]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append((nxt, layer + 1))

        for a in activities:
            layers.setdefault(a, 0)

        layer_groups = defaultdict(list)
        for node, layer in layers.items():
            layer_groups[layer].append(node)

        node_widths = {}
        for node in activities:
            base_width = max(80, len(node) * 7 + 20)
            node_widths[node] = base_width * scale

        layer_widths = {}
        for layer, nodes in layer_groups.items():
            layer_widths[layer] = max(node_widths[n] for n in nodes)

        sorted_layers = sorted(layer_groups.keys())
        layer_x_positions = {}
        current_x = self.PADDING

        for layer in sorted_layers:
            layer_x_positions[layer] = current_x
            current_x += (layer_widths[layer]+ self.H_LAYER_SPACING)

        positions = {}

        for layer in sorted_layers:
            nodes = layer_groups[layer]
            for i, node in enumerate(nodes):
                x = layer_x_positions[layer]
                y = self.PADDING + i * (self.V_SPACING * scale)
                positions[node] = (x, y)

        return positions, layers