import bpy, os, json, math

use_pre_yaw = True
save_render = True

jumpID = 9

# Configuración de rutas (ajusta según tu proyecto)
root = "/Users/gilbertogalvis/Work/free/oleg/repo/horsesml/JUMP_animation/"  # Ruta raíz del proyecto
glb_file = root+"render_files/JUMP-%d_training-17299.glb" %(jumpID)  # Ruta al archivo GLB con la animación de rotaciones
json_file = root+"json_files/training-17299.json"  # Ruta al archivo JSON con las coordenadas (x, y)

# Limpiar la escena actual
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Importar el archivo GLB con la animación de rotaciones
if os.path.exists(glb_file):
    bpy.ops.import_scene.gltf(filepath=glb_file)
else:
    raise FileNotFoundError(f"El archivo GLB no se encontró en: {glb_file}")

# Obtener el objeto principal de la animación (puede ser el mesh o la armadura)
# Asumimos que el objeto se llama "Horse" o similar; ajusta según tu nombre real
horse_object = None
for obj in bpy.data.objects:
    print(obj.name, obj.type)
    if obj.type in ['MESH', 'ARMATURE']: # and "Horse" in obj.name:  # Ajusta el nombre según tu modelo
        horse_object = obj
        break

if not horse_object:
    raise ValueError("No se encontró un objeto principal (mesh o armadura) en el GLB. Ajusta el nombre en el script.")

# Asegurarte de que el objeto esté en modo de edición de animación
if not horse_object.animation_data:
    horse_object.animation_data_create()
horse_object.rotation_mode = 'XYZ'  # Forzar modo Euler

# Cargar las coordenadas (x, y) desde el JSON
with open(json_file, 'r') as f:
    data = json.load(f)["JUMP"][jumpID-1]["render_coordinates"]#["BACK"]
    yaw = data["yaw"]
    # yaw = data["BACK"]["yaw"]
    x_coords = data["BACK"]['x']
    y_coords = data["BACK"]['y']

if len(x_coords) != len(y_coords):
    raise ValueError("Las listas 'x' e 'y' deben tener la misma longitud (número de frames).")

# Obtener el número de frames desde la animación importada
action = horse_object.animation_data.action
if not action:
    raise ValueError("No se encontró una acción de animación en el objeto. Asegúrate de que el GLB tiene animación.")
frame_start = int(action.frame_range[0])
frame_end = int(action.frame_range[1])
num_frames = frame_end - frame_start + 1

# Verificar que las coordenadas coincidan con el número de frames
if len(x_coords) != num_frames:
    raise ValueError(f"El número de coordenadas ({len(x_coords)}) no coincide con el número de frames ({num_frames}). Ajusta el JSON o la animación.")

# Iterar sobre las coordenadas y agregar keyframes para el desplazamiento y rotación
for frame in range(frame_start, frame_end + 1):
    index = frame - frame_start  # Índice en las listas x_coords, y_coords
    if index >= len(x_coords):  # Evitar índices fuera de rango
        break
    
    x = float(x_coords[index])
    y = float(y_coords[index])
    z = 0.0  # Sin movimiento vertical, ajusta si necesitas Z
    angle = float(yaw[index]) + math.pi/2

    # Establecer la posición (traslación)
    horse_object.location = (x, y, z)
    horse_object.keyframe_insert(data_path="location", frame=frame)
    
    if use_pre_yaw:
        horse_object.rotation_euler = (math.pi/2, 0.0, angle)
        horse_object.keyframe_insert(data_path="rotation_euler", frame=frame)
        print(f"Frame {frame}: angle={math.degrees(angle)} | {angle}")
    else:
        # Calcular el ángulo de rotación en el plano XY (rotación en Z)
        if x != 0 or y != 0:  # Evitar división por cero
            angle = math.atan2(y, x) + math.pi/2  # Ángulo en radianes
            horse_object.rotation_euler = (math.pi/2, 0.0, angle)
            horse_object.keyframe_insert(data_path="rotation_euler", frame=frame)
            print(f"Frame {frame}: angle={math.degrees(angle)}")
        else:
            # Si no hay movimiento, mantener la rotación anterior
            if frame > frame_start:
                horse_object.keyframe_insert(data_path="rotation_euler", frame=frame)

print("Desplazamiento y rotación animados añadidos con éxito al caballo.")

if save_render:
    # Opcional: Exportar el resultado como GLB para mantener la animación actualizada
    # output_glb = os.path.join(root, "JUMP-1_training-17299_with_translation.glb")  # Ruta de salida
    output_glb = glb_file.replace(".glb", "_with_translation.glb")
    bpy.ops.export_scene.gltf(
        filepath=output_glb,
        export_format='GLB',
        export_apply=True,  # Aplicar transformaciones
        export_animations=True,  # Incluir animaciones (rotaciones y traslaciones)
        export_yup=True  # Usar Y como arriba (estándar GLTF)
    )
    print(f"Escena exportada como GLB en: {output_glb}")