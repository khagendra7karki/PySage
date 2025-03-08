import ujson
import os
from collections import OrderedDict

EDGE_TYPES_TO_SQEEZE = ["file_docstring", "value", "func_signature", "class_signature"]

def process_edges(retrieved_edges):
    proc_edges = []
    for head, edges in retrieved_edges.items():
        for e in edges:
            proc_edges.append([head, e[0][0], e[0][1], e[1]])
    return proc_edges

def post_squeeze_nodes(nodes, edges):
    squeezed_nodes_map = {}
    squeezed_nodes = []
    squeezed_edges = []
    redundant_nodes = set()

    edges = list(OrderedDict.fromkeys([tuple(e) for e in edges]))  # Remove duplicates
    concrete_edges = [[nodes[int(e[0])], e[1], e[2], nodes[int(e[3])]] for e in edges]

    for e in edges:
        head, tail = nodes[int(e[0])], nodes[int(e[3])]
        if e[1] in EDGE_TYPES_TO_SQEEZE:
            new_node = f"#{head}\n{tail}"
            squeezed_nodes_map.setdefault(head, []).append(new_node)
            squeezed_nodes_map.setdefault(tail, []).append(new_node)
            redundant_nodes.add(tail)

    for e in concrete_edges:
        head, tail = e[0], e[3]
        heads = squeezed_nodes_map.get(head, [head])
        tails = squeezed_nodes_map.get(tail, [tail])

        for h in heads:
            for t in tails:
                if t not in heads:  # Avoid self-loops
                    squeezed_edges.append([h, e[1], e[2], t])

    for n in nodes:
        if n not in redundant_nodes:
            squeezed_nodes.extend(squeezed_nodes_map.get(n, [n]))

    squeezed_nodes2idx = {n: i for i, n in enumerate(squeezed_nodes)}
    squeezed_edges = [[str(squeezed_nodes2idx[e[0]]), e[1], e[2], str(squeezed_nodes2idx[e[3]])] for e in squeezed_edges]

    return squeezed_nodes, squeezed_edges

def create_test_samples(retrieved_entity_file, prompts=None):
    if prompts is None:
        prompts = [
            {
                "prompt": "...<IN-FILE CONTEXT>...",
                "groundtruth": "...",
                "metadata": {"file": "/path/to/file"}  # Replace with appropriate file path
            }
        ]

    with open(retrieved_entity_file, 'r') as f:
        retrieved_info = ujson.load(f)

    proj_loc = retrieved_info["project_location"]
    retrieved_nodes = retrieved_info["retrived_nodes"]
    retrieved_edges = retrieved_info["retrieved_edges"]

    samples = []  # Initialize samples list to collect valid test samples

    for p in prompts:  # Loop through all prompts
        file_path = p["metadata"]["file"].replace(proj_loc, "")
        # Ensure file_path is in the retrieved_nodes, then proceed
        if file_path not in retrieved_nodes:
            continue

        s = {
            "prompt": p["prompt"],
            "groundtruth": p["groundtruth"],
            "retrieved_nodes": retrieved_nodes[file_path],
            "retrieved_edges": process_edges(retrieved_edges[file_path]),
            "metadata": p["metadata"]
        }

        s["retrieved_nodes"], s["retrieved_edges"] = post_squeeze_nodes(s["retrieved_nodes"], s["retrieved_edges"])

        # If no edges exist, skip this sample (if needed)
        if len(s["retrieved_edges"]) == 0:
            continue

        samples.append(s)

    return samples  # Return the list of valid test samples


def generate_cross_file_context(retrieved_entity_file, prompt_file, output_file):
    # print(prompt_file)
    # print(retrieved_entity_file,"rrrrrrrrrrrrrrrrrrrr")
    samples = create_test_samples(retrieved_entity_file, prompt_file)
    with open(output_file, 'w') as f:
        for samp in samples:
            f.write(ujson.dumps(samp) + "\n")
    # print(samples,"here")
    return samples
