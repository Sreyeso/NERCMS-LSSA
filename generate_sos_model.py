import os
from textx import metamodel_from_file
from textx.scoping.providers import FQN

def get_subsystem_name(node):
    """Trace back up the parent tree to find the subsystem name for a node."""
    curr = node
    while curr is not None:
        if curr.__class__.__name__ == 'Subsystem':
            return curr.name
        curr = getattr(curr, 'parent', None)
    return None

def format_properties(props):
    """Format the textX properties object back into a string snippet."""
    if not props:
        return ""
    
    prop_strs = []
    if hasattr(props, 'style') and props.style is not None:
        prop_strs.append(f"style={props.style}")
    if hasattr(props, 'protocol') and props.protocol is not None:
        prop_strs.append(f"protocol={props.protocol}")
    if hasattr(props, 'timeout_ms') and props.timeout_ms is not None:
        prop_strs.append(f"timeout_ms={props.timeout_ms}")
    if hasattr(props, 'encrypted') and props.encrypted is not None:
        prop_strs.append(f"encrypted={'true' if props.encrypted else 'false'}")
    if hasattr(props, 'rate_limit') and props.rate_limit is not None:
        prop_strs.append(f"rate_limit={props.rate_limit}")
        
    if prop_strs:
        return "{\n      " + "\n      ".join(prop_strs) + "\n    }"
    return ""

def main():
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    metamodel_path = os.path.join(workspace_dir, 'metamodel.tx')
    model_path = os.path.join(workspace_dir, 'build.arch')
    out_path = os.path.join(workspace_dir, 'sos_model.arch')

    # 1. Load the metamodel and configure FQN scoping
    metamodel = metamodel_from_file(metamodel_path)
    metamodel.register_scope_providers({"*.*": FQN()})
    
    # 2. Parse the fully built model
    model = metamodel.model_from_file(model_path)
    
    subsystems = set()
    connectors = []
    
    # 3. Recursively extract all Subsystems and Connectors
    def process_elements(elements):
        for el in elements:
            type_name = el.__class__.__name__
            if type_name == 'Subsystem':
                subsystems.add(el.name)
                if hasattr(el, 'elements'):
                    process_elements(el.elements)
            elif type_name == 'Connector':
                connectors.append(el)
                
    process_elements(model.elements)
    
    cross_connectors = []
    
    # 4. Filter for cross-subsystem connectors and generalize them
    for conn in connectors:
        # Use getattr because 'from' is a reserved Python keyword
        from_node = getattr(conn, 'from')
        to_node = conn.to
        
        from_sub = get_subsystem_name(from_node)
        to_sub = get_subsystem_name(to_node)
        
        # If the connector links elements from two different subsystems
        if from_sub and to_sub and from_sub != to_sub:
            subsystems.add(from_sub)
            subsystems.add(to_sub)
            cross_connectors.append((conn.type, from_sub, to_sub, conn.properties))
            
    # 5. Generate the SoS text block
    output = []
    output.append(f"system_of_systems {model.name}_Global :")
    output.append("")
    
    # Write empty subsystems
    for sub in sorted(list(subsystems)):
        output.append(f"  subsystem {sub} {{}}")
        
    output.append("")
    
    # Write generalized connectors
    for conn_type, from_sub, to_sub, props in cross_connectors:
        prop_str = format_properties(props)
        if prop_str:
            output.append(f"  connector {conn_type} {from_sub} -> {to_sub} {prop_str}")
        else:
            output.append(f"  connector {conn_type} {from_sub} -> {to_sub}")

    output_text = "\n".join(output) + "\n"

    # 6. Save to mapped output file
    with open(out_path, 'w') as f:
        f.write(output_text)
        
    print(f"✅ Generated cross-subsystem SoS map at '{out_path}'")
    
    # 7. Validation: ensure the generated output complies with metamodel.tx
    try:
        metamodel.model_from_file(out_path)
        print("✅ The generated sos_model.arch compiles successfully against metamodel.tx.")
    except Exception as e:
        print(f"⚠️ Warning: the generated SoS might have syntax issues:\n{e}")

if __name__ == '__main__':
    main()