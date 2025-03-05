import bpy, os, json, mathutils

jumpID = 9

requested_coordenates_dict = {
    "RightFootIndex3": "BR",
    "LeftFootIndex3": "BL",
    "RightHandIndex3": "FR",
    "LeftHandIndex3": "FL",
    "Hips": "BACK",
    # "Spine": "BACK",
    # "Spine2": "BACK",
}

# Configuración de rutas (ajusta según tu proyecto)
root = "/Users/gilbertogalvis/Work/free/oleg/repo/horsesml/JUMP_animation/"  # Ruta raíz del proyecto
glb_file = root+"render_files/JUMP-%d_training-17299_with_translation.glb" %(jumpID)  # Ruta al archivo GLB con la animación de rotaciones
output_json = root+"json_files/" + os.path.basename(glb_file).replace(".glb", ".json")  # Ruta para guardar el JSON optimizado

# Limpiar la escena actual
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Importar el archivo GLB
if os.path.exists(glb_file):
    bpy.ops.import_scene.gltf(filepath=glb_file)
else:
    raise FileNotFoundError(f"El archivo GLB no se encontró en: {glb_file}")

# Obtener el objeto de malla y armadura del caballo
horse_mesh = None
armature = None
for obj in bpy.data.objects:
    print(f"Objeto: {obj.name}, Tipo: {obj.type}")
    if obj.type == 'MESH':
        horse_mesh = obj
    elif obj.type == 'ARMATURE':
        armature = obj

if not horse_mesh:
    raise ValueError("No se encontró un objeto MESH (malla) en el GLB. Asegúrate de que el caballo tiene una malla.")
if not armature:
    raise ValueError("No se encontró una armadura (ARMATURE) en el GLB. Asegúrate de que el caballo tiene una armadura con animación.")

# Verificar que el mesh esté vinculado a la armadura mediante un modificador "Armature"
has_armature_modifier = False
for mod in horse_mesh.modifiers:
    if mod.type == 'ARMATURE' and mod.object == armature:
        has_armature_modifier = True
        break
if not has_armature_modifier:
    raise ValueError("El objeto MESH no está vinculado a la armadura mediante un modificador 'Armature'. Asegúrate de que el mesh tiene este modificador.")

# # Agregar y configurar el modificador Decimate
# mod = horse_mesh.modifiers.new(name="Decimate", type='DECIMATE')
# mod.ratio = 0.2  # Reducir al 20% de los vértices originales (ajusta según necesidad)
# bpy.ops.object.modifier_apply(modifier="Decimate")
bpy.context.view_layer.objects.active = horse_mesh
mod = horse_mesh.modifiers.new(name="Decimate", type='DECIMATE')
mod.ratio = 0.1  # Reducir al 10%
bpy.ops.object.modifier_apply(modifier="Decimate")

# Obtener el depsgraph para evaluar la animación
depsgraph = bpy.context.evaluated_depsgraph_get()

# Obtener el número de frames desde la animación de la armadura
action = armature.animation_data.action if armature.animation_data else None
if not action:
    raise ValueError("No se encontró una acción de animación en la armadura. Asegúrate de que el GLB tiene animación.")

frame_start = int(action.frame_range[0])
frame_end = int(action.frame_range[1])
num_frames = frame_end - frame_start + 1

# Extraer las caras (una sola vez, desde el primer frame)
bpy.context.scene.frame_set(frame_start)  # Establecer el primer frame
mesh_data = horse_mesh.data
faces = []
for face in mesh_data.polygons:
    faces.append([vert_idx for vert_idx in face.vertices])  # Lista de índices de vértices por cara

# Verificar si las caras son triángulos o polígonos más complejos
print(f"Número de caras: {len(faces)}, Ejemplo de cara: {faces[0]}")
if not all(len(face) == 3 for face in faces):  # Asegurarse de que son triángulos
    print("Advertencia: Las caras no son todas triángulos. Plotly podría requerir triángulos para la animación 3D.")

# Extraer los vértices deformados por frame (incluyendo rotaciones de los huesos)
vertices_by_frame = []
depsgraph = bpy.context.evaluated_depsgraph_get()  # Obtener el grafo de dependencias evaluado

# for frame in range(frame_start, frame_start + 60):
for frame in range(frame_start, frame_end + 1):
    bpy.context.scene.frame_set(frame)  # Establecer el frame actual
    
    # Evaluar la malla deformada usando el grafo de dependencias
    evaluated_mesh = horse_mesh.evaluated_get(depsgraph).data  # Obtener la malla deformada
    
    # Obtener las posiciones de los vértices deformados en este frame
    vertices = []
    for vertex in evaluated_mesh.vertices:
        world_pos = horse_mesh.matrix_world @ vertex.co  # Transformar a coordenadas mundiales (incluye deformaciones)
        vertices.append([round(world_pos.x, 3), round(world_pos.y, 3), round(world_pos.z, 3)])  # Redondear para compactar
    
    vertices_by_frame.append(vertices)
    
    # Depuración: Imprimir los primeros 5 vértices de cada frame para verificar cambios
    print(f"Frame {frame}: Primeros 5 vértices deformados: {vertices[:5]}")

# Verificar el número de vértices por frame para consistencia
num_vertices = len(vertices_by_frame[0])
for i, frame_data in enumerate(vertices_by_frame):
    if len(frame_data) != num_vertices:
        print(f"Advertencia: Frame {i + frame_start} tiene {len(frame_data)} vértices, pero se esperan {num_vertices}.")

# Crear el JSON optimizado con la estructura propuesta
output_data = {
    "faces": faces,
    "vertices_by_frame": vertices_by_frame
}

# # Guardar en un archivo JSON compacto
# with open(output_json, 'w') as f:
#     json.dump(output_data, f, separators=(',', ':'), sort_keys=True)  # Compacto para ahorrar espacio

# print(f"Datos de la malla deformada exportados con éxito a: {output_json}")
# print(f"Número total de frames: {num_frames}, Vértices por frame: {num_vertices}, Caras: {len(faces)}")

# ---------------------------------------------------------
# get requested coordinates

# Buscar la armadura en la escena importada
armature = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        armature = obj
        break

action = armature.animation_data.action
frame_start = int(action.frame_range[0])
frame_end = int(action.frame_range[1])
num_frames = frame_end - frame_start + 1  # Número total de frames

# Diccionario para almacenar los datos de los huesos
requested_coordenates = { k:[] for k in requested_coordenates_dict.values() }

# Recorrer cada frame y recolectar datos solo de los huesos especificados
for frame in range(frame_start, frame_end + 1):
    bpy.context.scene.frame_set(frame)
    for bone in armature.pose.bones:
        if not bone.name in list(requested_coordenates_dict.keys()): continue
        
        # Obtener la posición global del hueso
        bone_matrix = armature.matrix_world @ bone.matrix
        pos = bone_matrix.translation
        # Agregar la posición como lista [x, y, z] al hueso correspondiente
        requested_coordenates[requested_coordenates_dict[bone.name]].append([pos.x, pos.y, pos.z])

# Verificar que todas las listas tengan el mismo tamaño
for k in requested_coordenates:
    if len(requested_coordenates[k]) != num_frames:
        print(f"Advertencia: El hueso {k} tiene {len(requested_coordenates[k])} frames, esperaba {num_frames}.")

output_data.update(
    dict(
        coords=requested_coordenates,
    )
)

# Guardar los datos en formato JSON
with open(output_json, 'w') as f:
    json.dump(output_data, f, indent=4)

print(f"Datos exportados a {output_json}")