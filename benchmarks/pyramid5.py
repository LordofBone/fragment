from components.renderer_config import RendererConfig
from components.renderer_instancing import RenderingInstance


def run_benchmark(duration=60, stats_queue=None, stop_event=None):
    # Initialize the base configuration for the renderer
    base_config = RendererConfig(
        window_title="Pyramid 5",
        window_size=(800, 600),
        cubemap_folder="textures/cube/mountain_lake/",
        camera_positions=[
            (3.4, 3.4, 3.4, -39.0, 39.0),
        ],
        camera_target=(0, 0.75, 0),
        up_vector=(0, 1, 0),
        fov=40,
        near_plane=0.1,
        far_plane=100,
        lights=[
            {"position": (1.85, 3.0, 7.0), "color": (0.55, 0.55, 0.55), "strength": 0.8},
        ],
        anisotropy=16.0,
        auto_camera=False,
        msaa_level=8,
        culling=True,
        texture_lod_bias=0.85,
        env_map_lod_bias=2.5,
        phong_shading=True,
    )

    # Create the rendering instance with the base configuration
    instance = RenderingInstance(base_config)
    instance.setup()
    # Define the configuration for the pyramid model
    pyramid_config = base_config.add_model(
        obj_path="models/pyramid.obj",
        texture_paths={
            "diffuse": "textures/diffuse/crystal.png",
            "normal": "textures/normal/crystal.png",
            "displacement": "textures/displacement/crystal.png",
        },
        shader_names={
            "vertex": "standard",
            "fragment": "embm",
        },
        rotation_speed=5000.0,
        rotation_axis=(0, 3, 0),
        apply_tone_mapping=False,
        apply_gamma_correction=False,
    )

    # Add the pyramid renderer to the instance with a specific name
    instance.add_renderer("pyramid", "model", **pyramid_config)

    # Enable auto-rotation for the pyramid model
    instance.scene_construct.set_auto_rotation("pyramid", True)

    # Run the rendering instance
    instance.run(duration=duration, stats_queue=stats_queue, stop_event=stop_event)
