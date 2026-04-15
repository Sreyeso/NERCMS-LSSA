import os
import glob
import re
import sys
from textx import metamodel_from_file
from textx.scoping.providers import FQN

def connector_processor(connector):
    from_node = getattr(connector, 'from', None)
    if connector.to.__class__.__name__ == 'Subsystem' or (from_node and from_node.__class__.__name__ == 'Subsystem'):
        print(f"⚠️ WARNING: Conector general a nivel de subsistema ({from_node.name} -> {connector.to.name}). Debería refinarse a nivel de componente mas adelante cuando se conozca.")

def build_model():
    template_path = 'main_model.template.arch'
    output_path = 'build.arch'
    metamodel_path = 'metamodel.tx'
    
    if not os.path.exists(template_path):
        print(f"Error: No se encontró la plantilla {template_path}")
        sys.exit(1)
        
    with open(template_path, 'r', encoding='utf-8') as f:
        built_content = f.read()

    placeholders = re.findall(r'\{\{\s*(team-[\w-]+)\s*\}\}', built_content)
    
    for team in placeholders:
        team_files = glob.glob(f'{team}/*.arch')
        team_arch_content = []
        
        for file in team_files:
            with open(file, 'r', encoding='utf-8') as tf:
                content = tf.read().strip()
                team_arch_content.append(content)
                
        if team_arch_content:
            combined = '\n\n'.join(team_arch_content)
            indented = '\n'.join('    ' + line if line else '' for line in combined.splitlines())
            built_content = re.sub(r'[ \t]*\{\{\s*' + team + r'\s*\}\}', indented, built_content)
        else:
            built_content = re.sub(r'\{\{\s*' + team + r'\s*\}\}', f'    // (Aun no hay definiciones para {team})', built_content)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(built_content)
        
    print(f"✅ Se compiló exitosamente el SoS global en: {output_path}")

    print("Validando sintaxis y referencias FQN con textX...")
    if not os.path.exists(metamodel_path):
        print(f"❌ Error: No se encontró el metamodelo {metamodel_path}")
        sys.exit(1)

    try:
        mm = metamodel_from_file(metamodel_path)
        mm.register_obj_processors({'Connector': connector_processor})
        mm.register_scope_providers({"*.*": FQN()})
        model = mm.model_from_file(output_path)
        print("\n🎉 ¡El modelo integrado compiló y sus referencias son válidas!")
    except Exception as e:
        print(f"❌ Error de validación textX en el modelo integrado:\n{e}")
        sys.exit(1)

if __name__ == "__main__":
    build_model()
