import os

# Get the directory of the current script
current_dir = os.path.dirname(os.path.realpath(__file__))

# Build the path to the model file
obj_path = os.path.join(current_dir, 'models', 'pyramid', 'pyramid.obj')
textures_dir = os.path.join(current_dir, 'textures')
cubemaps_dir = os.path.join(textures_dir, 'cubemaps')

# Build the path to the vertex shader file
vertex_shader_path = os.path.join(current_dir, 'shaders', 'default', 'vertex.glsl')

# Build the path to the fragment shader file
fragment_shader_path = os.path.join(current_dir, 'shaders', 'default', 'fragment.glsl')
