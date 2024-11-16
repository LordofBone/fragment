import os

# Get the directory of the current script
current_dir = os.path.dirname(os.path.realpath(__file__))


# Function to build paths relative to the config directory
def get_path(*path_parts):
    return os.path.join(current_dir, *path_parts)


# Directories
audio_dir = get_path("..", "audio")
benchmarks_dir = get_path("..", "benchmarks")
components_dir = get_path("..", "components")
config_dir = current_dir
gui_dir = get_path("..", "gui")
images_dir = get_path("..", "images")
misc_dir = get_path("..", "misc")
models_dir = get_path("..", "models")
screenshots_dir = get_path("..", "screenshots")
shaders_dir = get_path("..", "shaders")
textures_dir = get_path("..", "textures")
themes_dir = get_path("..", "themes")
utils_dir = get_path("..", "utils")

# Textures
diffuse_textures_dir = get_path("..", "textures", "diffuse")
displacement_textures_dir = get_path("..", "textures", "displacement")
normal_textures_dir = get_path("..", "textures", "normal")
cubemaps_dir = get_path("..", "textures", "cube")
