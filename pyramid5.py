from components.model_renderer import ModelRenderer

texture_paths = {
    'diffuse': 'textures/diffuse/crystal.png',
    'normal': 'textures/normals/crystal.png',
    'height': 'textures/height/crystal.png'
}
cubemap_folder = 'textures/cube/mountain_lake/'
lod_level = 7.0  # Default level of detail
camera_position = (4, 2, 4)  # Camera position
camera_target = (0, 0, 0)  # Camera target
up_vector = (0, 1, 0)  # Up vector
fov = 45  # Field of view
near_plane = 0.1  # Near plane
far_plane = 100  # Far plane
light_positions = [(3.0, 3.0, 3.0), (0.0, 3.0, 3.0)]  # Light positions
light_colors = [(1.0, 1.0, 1.0), (1.0, 0.5, 0.5)]  # Light colors
light_strengths = [0.8, 0.5]  # Light strengths
anisotropy = 16.0  # Texture anisotropy
rotation_speed = 2000.0  # Model rotation speed
rotation_axis = (0, 3, 0)  # Model rotation axis

model_renderer = ModelRenderer(
    "models/pyramid.obj",
    "shaders/embm/vertex.glsl",
    "shaders/embm/fragment.glsl",
    texture_paths,
    cubemap_folder,
    lod_level,
    window_size=(800, 600),
    camera_position=camera_position,
    camera_target=camera_target,
    up_vector=up_vector,
    fov=fov,
    near_plane=near_plane,
    far_plane=far_plane,
    light_positions=light_positions,
    light_colors=light_colors,
    light_strengths=light_strengths,
    anisotropy=anisotropy,
    rotation_speed=rotation_speed,
    rotation_axis=rotation_axis
)
model_renderer.mainloop()
