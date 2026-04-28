import os
from textx import metamodel_from_file
from textx.scoping.providers import FQN

def get_subsystem_name(node):
    if node.__class__.__name__ == 'Subsystem':
        return node.name
    elif node.__class__.__name__ == 'Component':
        return node.parent.name
    return None

def format_properties(properties):
    if not properties:
        return ""

    prop_strs = []
    

    if properties.style is not None:
        prop_strs.append(f"style={properties.style}")

    if properties.protocol is not None:
        prop_strs.append(f"protocol={properties.protocol}")

    if properties.timeout_ms != 0:
        prop_strs.append(f"timeout_ms={properties.timeout_ms}")

    if properties.encrypted is not None:
        prop_strs.append(f"encrypted={'true' if properties.encrypted else 'false'}")

    if properties.rate_limit != 0:
        prop_strs.append(f"rate_limit={properties.rate_limit}")
   
    if not prop_strs: return ""
    return "{\n        " + "\n        ".join(prop_strs) + "\n    }"

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
    cross_connectors = []
    
    # 3. Traverse the model to identify subsystems and cross-subsystem connectors
    for el in model.elements:
        type_name = el.__class__.__name__
        if type_name == 'Subsystem':
            subsystems.add(el.name)

        elif type_name == 'CrossConnector':
            from_node = getattr(el, 'from')
            to_node = el.to

            from_sub = get_subsystem_name(from_node)
            to_sub = get_subsystem_name(to_node)

            cross_connectors.append((
                el.type,
                from_sub,
                to_sub,
                el.properties
            ))

            subsystems.add(from_sub)
            subsystems.add(to_sub)

     # 4. Generate the SoS text block
    output = []
    output.append(f"system_of_systems {model.name}_Global :")
    output.append("")
    
    # Write empty subsystems
    for sub in sorted(subsystems):
        output.append(f"    subsystem {sub} {{}}")    
    output.append("")
    
    # Write generalized connectors
    for conn_type, from_sub, to_sub, properties in cross_connectors:
        prop_str = format_properties(properties)
        if prop_str:
            output.append(f"    connector {conn_type} {from_sub} -> {to_sub} {prop_str}\n")
        else:
            output.append(f"    connector {conn_type} {from_sub} -> {to_sub}\n")
    output_text = "\n".join(output)

    # 5. Save to mapped output file
    with open(out_path, 'w') as f:
        f.write(output_text) 
    print(f"✅ Generated cross-subsystem SoS map at '{out_path}'")
    
    # 6. Validation: ensure the generated output complies with metamodel.tx
    try:
        metamodel.model_from_file(out_path)
        print("✅ The generated sos_model.arch compiles successfully against metamodel.tx.")
    except Exception as e:
        print(f"⚠️ Warning: the generated SoS might have syntax issues:\n{e}")

if __name__ == '__main__':
    main()
