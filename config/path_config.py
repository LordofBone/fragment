import os

# ------------------------------------------------------------------------------
# Base Directory Setup
# ------------------------------------------------------------------------------
# Determine the directory of the current config file.
current_dir = os.path.dirname(os.path.realpath(__file__))


def get_path(*path_parts):
    """
    Build an absolute path by joining the current config directory with the given parts.

    Args:
        *path_parts: Variable length path segments.

    Returns:
        str: The absolute path.
    """
    return os.path.join(current_dir, *path_parts)


# ------------------------------------------------------------------------------
# Repository Directories
# ------------------------------------------------------------------------------
# These paths are relative to the repository root.
audio_dir = get_path("..", "audio")
benchmarks_dir = get_path("..", "benchmarks")
components_dir = get_path("..", "components")
gui_dir = get_path("..", "gui")
images_dir = get_path("..", "docs", "images")
misc_dir = get_path("..", "misc")
models_dir = get_path("..", "models")
screenshots_dir = get_path("..", "screenshots")
shaders_dir = get_path("..", "shaders")
textures_dir = get_path("..", "textures")
themes_dir = get_path("..", "themes")
utils_dir = get_path("..", "utils")

# The configuration directory itself
config_dir = current_dir

# ------------------------------------------------------------------------------
# Texture Directories
# ------------------------------------------------------------------------------
# Specific subdirectories for various texture types.
diffuse_textures_dir = get_path("..", "textures", "diffuse")
displacement_textures_dir = get_path("..", "textures", "displacement")
normal_textures_dir = get_path("..", "textures", "normal")
cubemaps_dir = get_path("..", "textures", "cube")
