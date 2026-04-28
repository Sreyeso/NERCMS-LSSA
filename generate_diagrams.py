import os
from textx import metamodel_from_file
from textx.scoping.providers import FQN

def get_subsystem_name(node):
    if node.__class__.__name__ == 'Subsystem':
        return node.name
    elif node.__class__.__name__ == 'Component':
        return node.parent.name
    return None

def generate_diagrams():
    # Load metamodel and register FQN resolution
    mm = metamodel_from_file('metamodel.tx')
    mm.register_scope_providers({"*.*": FQN()})
    
    # Load the parsed model
    model = mm.model_from_file('build.arch')

    lines = []
    lines.append("# Architecture Diagrams\n")

    # 1. Global SoS Diagram
    lines.append("## System of Systems (Global)\n")
    lines.append("```mermaid")
    lines.append("graph TD")
    
    subsystems = [e for e in model.elements if e.__class__.__name__ == 'Subsystem']
    
    for sub in subsystems:
        # Use double brackets for subsystems
        lines.append(f"    {sub.name}[[{sub.name}]]")

    lines.append("")
    
    global_connectors = [e for e in model.elements if e.__class__.__name__ == 'Connector']
    for c in global_connectors:
        src_node = getattr(c, 'from')
        dst_node = getattr(c, 'to')
        
        src_sub = get_subsystem_name(src_node)
        dst_sub = get_subsystem_name(dst_node)
        
        if src_sub and dst_sub:
            label = c.type
            if getattr(c, 'properties', None) and getattr(c.properties, 'protocol', None):
                label += f" ({c.properties.protocol})"
            
            lines.append(f"    {src_sub} -- \"{label}\" --> {dst_sub}")

    lines.append("```\n")

    # 2. Per Subsystem Diagrams
    for sub in subsystems:
        lines.append(f"## Subsystem: {sub.name}\n")
        lines.append("```mermaid")
        lines.append("graph TD")
        
        components = [e for e in sub.elements if e.__class__.__name__ == 'Component']
        for comp in components:
            lines.append(f"    {comp.name}[\"{comp.name}<br/>({comp.type})\"]")
            
        lines.append("")
        
        connectors = [e for e in sub.elements if e.__class__.__name__ == 'Connector']
        for c in connectors:
            src_node = getattr(c, 'from')
            dst_node = getattr(c, 'to')
            
            label = c.type
            if getattr(c, 'properties', None) and getattr(c.properties, 'protocol', None):
                label += f" ({c.properties.protocol})"
                
            lines.append(f"    {src_node.name} -- \"{label}\" --> {dst_node.name}")

        lines.append("```\n")
        
    # Write to diagram file
    with open('diagrams.md', 'w') as f:
        f.write('\n'.join(lines))
    print(f"✅ Generated diagrams.md successfully.")

if __name__ == '__main__':
    generate_diagrams()
