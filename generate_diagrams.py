from collections import defaultdict
from textx import metamodel_from_file
from textx.scoping.providers import FQN

def get_subsystem_name(node):
    if node.__class__.__name__ == 'Subsystem':
        return node.name
    elif node.__class__.__name__ == 'Component':
        return node.parent.name
    return None

def safe_id(name):
    """Evita problemas con Mermaid (guiones, etc.)"""
    return name.replace("-", "_")

def generate_diagrams():
    # Load metamodel and register FQN resolution
    mm = metamodel_from_file('metamodel.tx')
    mm.register_scope_providers({"*.*": FQN()})
    
    # Load the parsed model
    model = mm.model_from_file('build.arch')

    lines = []
    lines.append("# Architecture Diagrams\n")

    # ==========================================================
    # 1. Global SoS Diagram
    # ==========================================================
    lines.append("## System of Systems (Global)\n")
    lines.append("```mermaid")
    lines.append("graph LR")
    
    subsystems = [e for e in model.elements if e.__class__.__name__ == 'Subsystem']
    
    for sub in subsystems:
        sid = safe_id(sub.name)
        lines.append(f"    {sid}[{sub.name}]")

    lines.append("")
    
    edge_counter = defaultdict(int)

    global_connectors = [e for e in model.elements if e.__class__.__name__ == 'CrossConnector']
    for c in global_connectors:
        src_node = getattr(c, 'from')
        dst_node = getattr(c, 'to')
        
        src_sub = get_subsystem_name(src_node)
        dst_sub = get_subsystem_name(dst_node)
        
        if src_sub and dst_sub:
            label = c.type

            if getattr(c, 'properties', None) and getattr(c.properties, 'protocol', None):
                label += f" ({c.properties.protocol.strip()})"
            
            key = (src_sub, dst_sub, label)
            edge_counter[key] += 1

    processed = set()

    # render
    for (src, dst, label), count in sorted(edge_counter.items()):
        if (src, dst, label) in processed:
            continue

        reverse_key = (dst, src, label)

        # Caso bidireccional (ambos conectores existen con el mismo label)
        if reverse_key in edge_counter and edge_counter[reverse_key] == count:
            if count > 1:
                label_with_count = f"{count}x {label}"
            else:
                label_with_count = label

            lines.append(
                f"    {safe_id(src)} -- \"{label_with_count}\" <--> {safe_id(dst)}"
            )

            processed.add((src, dst, label))
            processed.add(reverse_key)

        else:
            # unidireccional normal
            if count > 1:
                label_with_count = f"{count}x {label}"
            else:
                label_with_count = label

            lines.append(
                f"    {safe_id(src)} -- \"{label_with_count}\" --> {safe_id(dst)}"
            )

            processed.add((src, dst, label))

    lines.append("```\n")

    # ==========================================================
    # 2. Per Subsystem Diagrams
    # ==========================================================
    node_order = ["sensing", "edge", "central", "external", "undefined"]
    tier_order = ["presentation", "communication", "logic", "data", "physical", "edge", "external"]

    for sub in subsystems:
        lines.append(f"## Subsystem: {sub.name}\n")
        lines.append("```mermaid")
        lines.append("graph LR")
        
        sub_id = safe_id(sub.name)
        lines.append(f"    subgraph {sub_id}")

        # ------------------------------------------
        # 1. Agrupar por nodo
        # ------------------------------------------
        components = [e for e in sub.elements if e.__class__.__name__ == 'Component']
        
        nodes = {}
        for comp in components:
            node = getattr(comp, "node", None) or "undefined"
            nodes.setdefault(node, []).append(comp)

        # ------------------------------------------
        # 2. Render: node -> tier -> components
        # ------------------------------------------
        for node in node_order:
            if node not in nodes:
                continue

            is_grouped = node != "undefined"
            tier_indent = "            " if is_grouped else "        "
            node_indent = "        " if is_grouped else "        "

            if is_grouped:
                node_id = f"{sub_id}_{node}"
                lines.append(f"        subgraph {node_id}[{node}]")

            tiers = {}
            for comp in nodes[node]:
                tiers.setdefault(comp.tier, []).append(comp)

            for tier in tier_order:
                if tier not in tiers:
                    continue

                tier_id = f"{sub_id}_{node}_{tier}"
                lines.append(f"{tier_indent}subgraph {tier_id}[{tier}]")

                for comp in tiers[tier]:
                    cid = safe_id(comp.name)
                    label = f"{comp.name}<br/>({comp.type})"
                    lines.append(f"{tier_indent}    {cid}[\"{label}\"]")
                lines.append(f"{tier_indent}end")

            if node != "undefined":
                lines.append(f"{node_indent}end")

        lines.append("")

        # ------------------------------------------
        # 3. Conectores internos
        # ------------------------------------------
        connectors = [e for e in sub.elements if e.__class__.__name__ == 'Connector']
        
        for c in connectors:
            src_node = getattr(c, 'from')
            dst_node = getattr(c, 'to')
            
            label = c.type
            if getattr(c, 'properties', None) and getattr(c.properties, 'protocol', None):
                label += f" ({c.properties.protocol})"

            lines.append(
                f"    {safe_id(src_node.name)} -- \"{label}\" --> {safe_id(dst_node.name)}"
            )

        lines.append("    end")
        lines.append("```\n")
        
    # Write to diagram file
    with open('diagrams.md', 'w') as f:
        f.write('\n'.join(lines))

    print("✅ Generated diagrams.md successfully.")


if __name__ == '__main__':
    generate_diagrams()
