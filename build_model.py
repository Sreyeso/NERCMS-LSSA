import os
import glob
import re
import sys
from textx import metamodel_from_file
from textx.scoping.providers import FQN

def connector_processor(crossConnector):
    from_node = getattr(crossConnector, 'from', None)
    if crossConnector.to.__class__.__name__ == 'Subsystem' or (from_node and from_node.__class__.__name__ == 'Subsystem'):
        print(f"⚠️ WARNING: Conector general a nivel de subsistema ({from_node.name} -> {crossConnector.to.name}). Debería refinarse a nivel de componente mas adelante cuando se conozca.")

def build_model():
    template_path = 'main_model.template.arch'
    output_path = 'build.arch'
    metamodel_path = 'metamodel.tx'
    
    if not os.path.exists(template_path):
        print(f"Error: No se encontró la plantilla {template_path}")
        sys.exit(1)
        
    with open(template_path, 'r', encoding='utf-8') as f:
        built_content = f.read()

    placeholders = re.findall(r'\{\{\s*([\w-]+)\s*\}\}', built_content)

    for placeholder in placeholders:
        files = glob.glob(f'{placeholder}/*.arch')
        content = []
        
        for file in files:
            with open(file, 'r', encoding='utf-8') as tf:
                content.append(tf.read().strip())
    
        if content:
            combined = '\n\n'.join(content)
            indented = '\n'.join('    ' + line if line else '' for line in combined.splitlines())
        else:
            if placeholder.startswith("team-"):
                indented = f'    // (Aun no hay definiciones para {placeholder})'
            elif placeholder == "cross-connectors":
                indented = '    // (No hay conectores globales definidos)'
            else:
                indented = f'    // (Sin contenido para {placeholder})'
        
        built_content = re.sub(
            r'[ \t]*\{\{\s*' + re.escape(placeholder) + r'\s*\}\}', 
            indented, 
            built_content
        )
        
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(built_content)
        
    print(f"✅ Se compiló exitosamente el SoS global en: {output_path}")

    print("Validando sintaxis y referencias FQN con textX...")
    if not os.path.exists(metamodel_path):
        print(f"❌ Error: No se encontró el metamodelo {metamodel_path}")
        sys.exit(1)

    try:
        mm = metamodel_from_file(metamodel_path)
        mm.register_obj_processors({'CrossConnector': connector_processor})
        mm.register_scope_providers({"*.*": FQN()})
        model = mm.model_from_file(output_path)
        print("\n🎉 ¡El modelo integrado compiló y sus referencias son válidas!")
    except Exception as e:
        print(f"❌ Error de validación textX en el modelo integrado:\n{e}")
        sys.exit(1)

if __name__ == "__main__":
    build_model()
