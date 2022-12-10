import veusz.plugins as plugins
import copy
from itertools import cycle
import random


class SankeyNode:
    def __init__(self, name, nodes_in, nodes_out, amount_in, amount_out):
        self.name = name
        self.nodes_in = nodes_in
        self.nodes_out = nodes_out
        self.amount_in = amount_in
        self.amount_out = amount_out


node_space = 0.85
sigmoid_width_constant = 300.59
themes = {
    "Ocean": ["#164773", "#0B2B40", "#1E5959", "#3B8C6E", "#3B8C6E", "#89D99D"],
    "Pastel": ["#F5B7B1", "#D2B4DE", "#AED6F1", "#A2D9CE", "#F9E79F", "#F5CBA7", "#D7BDE2", "#A9CCE3", "#A3E4D7"],
    "Forest": ["#f1ddbf", "#525e75", "#78938a", "#92ba92"],
    "Sunset": ["#003f5c", "#58508d", "#bc5090", "#ff6361", "#ffa600"],
    "Desert": ["#d6ccc2", "#d6ccc2", "#f5ebe0", "#e3d5ca", "#d5bdaf"]
          }


def find_node(name):
    for node in nodes:
        if node.name == name:
            return node
    return None


def generate_nodes():
    for i in range(len(source)):
        found_source = False
        for node in nodes:
            if source[i] == node.name:
                node.nodes_out.append(target[i])
                node.amount_out += value[i]
                found_source = True
                break
        if not found_source:
            nodes.append(SankeyNode(source[i], [], [target[i]], 0, value[i]))

        found_target = False
        for node in nodes:
            if target[i] == node.name:
                node.nodes_in.append(source[i])
                node.amount_in += value[i]
                found_target = True
                break
        if not found_target:
            nodes.append(SankeyNode(target[i], [source[i]], [], value[i], 0))


def get_first_layer():
    first_layer = []
    for node in nodes:
        if len(node.nodes_in) == 0:
            first_layer.append(node)
    return first_layer


def get_next_layer(layer):
    next_layer = []
    for x in layer:
        for node_out in x.nodes_out:
            node = find_node(node_out)
            if node not in next_layer:
                next_layer.append(node)

    return next_layer


def get_layer_info(layer):
    total_value = 0
    for node in layer:
        total_value += max(node.amount_in, node.amount_out)
    node_count = len(layer)
    return node_count, total_value


def draw_nodes(interface, layer, layer_number, global_layer_max):
    node_count = layer_info[layer_number]['node_count']
    layer_max = layer_info[layer_number]['total_value']
    layer_ratio = layer_max / global_layer_max
    layer_spacing = 1 - layer_ratio + (1 - node_space)
    per_spacing = layer_spacing / (node_count + 1)

    next_yPos = 1
    for i in range(node_count):
        height = max(layer[i].amount_in, layer[i].amount_out) / global_layer_max * node_space
        next_yPos -= (height / 2) + per_spacing
        layer_info[layer_number]["nodes"][layer[i].name] = next_yPos + (height / 2)
        if not layer_number == len(layers) - 1:
            interface.Root.page1.grid1["graph" + str(layer_number + 1)].Add('rect', xPos=-0.025, yPos=next_yPos, width=0.05,
                                                              height=height, Fill__color=node_color)
        else:
            interface.Root.page1.grid1["graph" + str(layer_number)].Add('rect', xPos=1.025, yPos=next_yPos, width=0.05,
                                                                  height=height, Fill__color=node_color)
        next_yPos -= height / 2


def draw_flows(interface, global_layer_max):
    print(layer_info)
    for i in range(len(layer_info)):
        current_layers = copy.deepcopy(layer_info[i:i + 2])
        print(current_layers)
        for node in current_layers[0]["nodes"]:
            node = find_node(node)
            for flow_count in range(len(source)):
                if node.name == source[flow_count]:
                    height = value[flow_count] / global_layer_max * node_space
                    flow_source = current_layers[0]["nodes"][node.name]
                    source_adjusted = flow_source - height / 2
                    flow_target = current_layers[1]["nodes"][target[flow_count]]
                    target_adjusted = flow_target - height / 2
                    draw_sigmoid(interface, "graph" + str(i + 1), source_adjusted, target_adjusted, height * sigmoid_width_constant)
                    current_layers[0]["nodes"][node.name] -= height
                    current_layers[1]["nodes"][target[flow_count]] -= height


def draw_sigmoid(interface, graph, source, target, height):
    if target < source:
        y = source - target
        if y == 0:
            y = 0.000001
        interface.Root.page1.grid1[graph].Add('function', function="-(1/((1/" + str(y) + ")+(e**-x)))+" + str(source),
                                    Line__width=str(height) + "pt", Line__color=next(colors_cycle))
    else:
        y = target - source
        if y == 0:
            y = 0.000001
        interface.Root.page1.grid1[graph].Add('function', function="(1/((1/" + str(y) + ")+(e**-x)))+" + str(source),
                                    Line__width=str(height) + "pt", Line__color=next(colors_cycle))


class SankeyPlugin(plugins.ToolsPlugin):
    menu = ('Generate Sankey',)
    name = 'Sankey'

    description_short = 'Generate Sankey Plot'
    description_full = 'Before generating, ensure that your data is imported (columns: source, target, value), and the custom Sankey stylesheet is applied.'

    def __init__(self):
        self.fields = [
            plugins.FieldColor('node_color', descr='Node Color', default='theme11'),
            plugins.FieldCombo('theme', descr='Flow Color', default=list(themes.keys())[0], items=(themes.keys())),
        ]

    def apply(self, interface, fields):
        global source, target, value, nodes, layers, layer_info, node_color, colors_cycle
        source = interface.GetData('source')
        target = interface.GetData('target')
        value = interface.GetData('value')[0]
        nodes = []
        layer_info = []

        node_color = fields['node_color']

        if fields['theme'] in themes:
            colors_cycle = cycle(random.sample(themes[fields['theme']], len(themes[fields['theme']])))
        else:
            colors_cycle = cycle([fields['theme']])

        for node in interface.GetChildren():
            interface.Remove(node)

        generate_nodes()
        layers = [get_first_layer()]
        while True:
            next_layer = get_next_layer(layers[-1])
            if len(next_layer) != 0:
                layers.append(next_layer)
            else:
                break

        layer_count = len(layers)

        global_layer_max = 0
        for layer in layers:
            node_count, total_value = get_layer_info(layer)
            layer_info.append({"total_value": total_value, "node_count": node_count, "nodes": {}})
            if total_value > global_layer_max:
                global_layer_max = total_value

        page = interface.Root.Add('page', width=str(14.45 + 10.55 * (layer_count - 2)) + "cm")
        grid = page.Add('grid', rows=1, columns=layer_count)

        for i in range(layer_count - 1):
            graph = grid.Add('graph', autoadd=False)
            graph.Add('axis', min=-7, max=7)
            graph.Add('axis', min=0, max=1)

        for layer_number in range(layer_count):
            draw_nodes(interface, layers[layer_number], layer_number, global_layer_max)

        draw_flows(interface, global_layer_max)


plugins.toolspluginregistry.append(SankeyPlugin)
