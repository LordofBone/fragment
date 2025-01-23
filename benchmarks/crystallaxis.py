import os

from components.renderer_config import RendererConfig
from components.renderer_instancing import RenderingInstance
from config.path_config import (
    cubemaps_dir,
    diffuse_textures_dir,
    displacement_textures_dir,
    models_dir,
    normal_textures_dir,
)


def run_benchmark(
    stats_queue=None,
    stop_event=None,
    resolution=(800, 600),
    msaa_level=4,
    anisotropy=16,
    shadow_map_resolution=2048,
    particle_render_mode="vertex",
    vsync_enabled=True,
    sound_enabled=True,
    fullscreen=False,
):
    # Initialize the base configuration for the renderer
    base_config = RendererConfig(
        window_title="Crystallaxis",
        window_size=resolution,
        vsync_enabled=vsync_enabled,
        fullscreen=fullscreen,
        duration=60,
        cubemap_folder=os.path.join(cubemaps_dir, "magick_dome/"),
        camera_positions=[
            (4.5, 2.85, -1.4, 108.0, -24.0),
        ],
        lens_rotations=[0.0],
        fov=40,
        near_plane=0.1,
        far_plane=100,
        ambient_lighting_strength=0.05,
        ambient_lighting_color=(0.878, 0.98, 0.714),
        lights=[
            {"position": (6.85, 5.0, 4.0), "color": (0.671, 0.902, 0.98), "strength": 0.67},
            {"position": (0.0, -5.0, -10.0), "color": (0.671, 0.902, 0.98), "strength": 0.6},
            {"position": (2.2, 6.0, -4.0), "color": (0.969, 0.863, 0.431), "strength": 0.7},
            {"position": (2.2, -2.0, 0.0), "color": (0.969, 0.863, 0.431), "strength": 0.42},
        ],
        shadow_map_resolution=shadow_map_resolution,
        anisotropy=anisotropy,
        auto_camera=False,
        msaa_level=msaa_level,
        culling=True,
        lighting_mode=2,
    )

    # Create the rendering instance with the base configuration
    instance = RenderingInstance(base_config)
    instance.setup()

    # Define the configuration for the pyramid model
    pyramid_config = base_config.add_model(
        obj_path=os.path.join(models_dir, "pyramid.obj"),
        texture_paths={
            "diffuse": os.path.join(diffuse_textures_dir, "crystal.png"),
            "normal": os.path.join(normal_textures_dir, "crystal.png"),
            "displacement": os.path.join(displacement_textures_dir, "crystal.png"),
        },
        shader_names={
            "vertex": "standard",
            "fragment": "embm",
        },
        shininess=32.0,
        apply_tone_mapping=False,
        apply_gamma_correction=False,
        env_map_strength=0.45,
        texture_lod_bias=1.1,
        env_map_lod_bias=0.0,
        pbr_extensions={
            "roughness": 0.399083,  # Pr
            "metallic": 0.064220,  # Pm
            "clearcoat": 0.110092,  # Pc
            "clearcoat_roughness": 0.039174,  # Pcr
            "sheen": 0.036697,  # Ps
            "aniso": 0.036697,  # aniso
            "anisor": 0.036697,  # anisor
        },
    )

    # Define the configuration for the skybox
    skybox_config = base_config.add_skybox(
        shader_names={
            "vertex": "skybox",
            "fragment": "skybox",
        },
    )

    # Add the skybox and the pyramid to the scene
    instance.add_renderer("skybox", "skybox", **skybox_config)
    instance.add_renderer("pyramid", "model", **pyramid_config)

    # Optionally enable autorotation for the pyramid
    instance.scene_construct.set_auto_rotation("pyramid", True, axis=(0, 1, 0), speed=5000.0)

    # Run the rendering instance
    instance.run(stats_queue=stats_queue, stop_event=stop_event)
