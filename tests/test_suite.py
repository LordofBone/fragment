"""
Extended Test Suite for the Fragment 3D Rendering Benchmark System

This module adds additional tests to cover:
  - Verification of OpenGL error–free calls via mocks
  - Walking the /shaders folder and attempting shader “compilation”
  - Headless tests of the GUI (using Tkinter’s withdraw to avoid actual windowing)
  - Testing extra pure–Python logic functions (e.g. drop shadow, config generators)
  - Creating a minimal headless OpenGL context (using patches) to run some of the
    graphics pipeline tests

All tests are designed to run in headless mode so that they can be run automatically
(e.g., on GitHub Actions) without requiring a full graphics environment.
"""

import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

# Adjust PYTHONPATH to include project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import modules from your project
from components.renderer_config import RendererConfig
from components.camera_control import CameraController
from components.shader_engine import ShaderEngine
from components.stats_collector import StatsCollector
from components.renderer_instancing import RenderingInstance

# For GUI testing, try to import the App class.
try:
    from gui.main_gui import App
except ImportError:
    App = None

# ------------------------------------------------------------------------------
# Mocks and Patches for OpenGL functions
# ------------------------------------------------------------------------------
OPENGL_PATCHES = [
    patch("OpenGL.GL.glCreateShader", MagicMock(return_value=1)),
    patch("OpenGL.GL.glShaderSource", MagicMock()),
    patch("OpenGL.GL.glCompileShader", MagicMock()),
    patch("OpenGL.GL.glGetShaderiv", MagicMock(return_value=True)),
    patch("OpenGL.GL.glGetShaderInfoLog", MagicMock(return_value=b"")),
    patch("OpenGL.GL.glCreateProgram", MagicMock(return_value=2)),
    patch("OpenGL.GL.glAttachShader", MagicMock()),
    patch("OpenGL.GL.glLinkProgram", MagicMock()),
    patch("OpenGL.GL.glGetProgramiv", MagicMock(return_value=True)),
    patch("OpenGL.GL.glDeleteShader", MagicMock()),
    patch("OpenGL.GL.glDeleteProgram", MagicMock()),
    patch("OpenGL.GL.glGenFramebuffers", MagicMock(return_value=3)),
    patch("OpenGL.GL.glGenTextures", MagicMock(return_value=4)),
    patch("OpenGL.GL.glBindTexture", MagicMock()),
    patch("OpenGL.GL.glTexImage2D", MagicMock()),
    patch("OpenGL.GL.glTexParameteri", MagicMock()),
    patch("OpenGL.GL.glFramebufferTexture2D", MagicMock()),
    patch("OpenGL.GL.glDrawBuffer", MagicMock()),
    patch("OpenGL.GL.glReadBuffer", MagicMock()),
    patch("OpenGL.GL.glCheckFramebufferStatus", MagicMock(return_value=0x8CD5)),  # FRAMEBUFFER_COMPLETE
    patch("OpenGL.GL.glDeleteFramebuffers", MagicMock()),
    patch("OpenGL.GL.glDeleteTextures", MagicMock()),
]

def apply_opengl_patches(cls):
    for patcher in OPENGL_PATCHES:
        cls = patcher(cls)
    return cls

# ------------------------------------------------------------------------------
# Dummy functions for simulating benchmark run and audio playback.
# ------------------------------------------------------------------------------
def dummy_run_function(stats_queue, stop_event, resolution, msaa_level, anisotropy, shading_model,
                       shadow_map_resolution, particle_render_mode, vsync_enabled, sound_enabled, fullscreen):
    """Fake run function that simulates a short wait and sends 'fps' into stats_queue."""
    if stats_queue is not None:
        stats_queue.put(("ready", None))
        stats_queue.put(("fps", 60))
    time.sleep(0.1)

def dummy_play_audio(self):
    """Fake play_audio function for AudioPlayer, simulating a short wait."""
    self.is_playing.set()
    time.sleep(0.1)
    self.is_playing.clear()

# ------------------------------------------------------------------------------
# Additional Tests for Pure-Python Logic
# ------------------------------------------------------------------------------
class TestPurePythonExtended(unittest.TestCase):
    def test_renderer_config_add_model(self):
        """Test that RendererConfig.add_model returns a valid configuration dictionary."""
        base_config = RendererConfig(window_title="ExtendedTest", window_size=(800, 600))
        model_cfg = base_config.add_model(
            obj_path="dummy.obj",
            texture_paths={"diffuse": "dummy.png"},
            shader_names=("standard", "default")
        )
        self.assertIsInstance(model_cfg, dict)
        self.assertEqual(model_cfg["obj_path"], "dummy.obj")
        self.assertEqual(model_cfg["shader_names"], ("standard", "default"))

    def test_drop_shadow_function_in_gui(self):
        """Test the drop shadow function from the GUI module.
           We simulate a simple image and ensure that a new image is returned.
        """
        from gui.main_gui import App  # assuming App contains add_drop_shadow
        from PIL import Image
        red_img = Image.new("RGBA", (50, 50), (255, 0, 0, 255))
        if App is None:
            self.skipTest("GUI module not available.")
        app = App()
        shadow_img = app.add_drop_shadow(red_img, shadow_offset=(5, 5), blur_radius=5)
        self.assertTrue(isinstance(shadow_img, Image.Image))
        self.assertGreater(shadow_img.width, red_img.width)
        self.assertGreater(shadow_img.height, red_img.height)
        app.destroy()

    def test_camera_controller_interpolation(self):
        """Test that CameraController properly interpolates camera positions and rotations."""
        positions = [(0, 0, 0, 0, 0), (10, 10, 10, 90, 45)]
        lens = [0, 90]
        cc = CameraController(positions, lens_rotations=lens, move_speed=1.0, loop=False)
        pos, rot = cc.update(0.5)
        self.assertGreater(pos.x, 0)
        self.assertLess(pos.x, 10)
        self.assertGreaterEqual(rot.x, 0)
        self.assertLessEqual(rot.x, 90)

    def test_stats_collector_add_point(self):
        """Test that StatsCollector properly adds data points."""
        sc = StatsCollector()
        sc.reset("TestBench", 123)
        sc.set_current_fps(60)
        with sc.usage_lock:
            sc.cpu_usage = 20.0
            sc.gpu_usage = 30.0
        sc.add_data_point()
        data = sc.get_all_data()
        self.assertEqual(data["TestBench"]["fps_data"], [60])
        self.assertEqual(data["TestBench"]["cpu_usage_data"], [20.0])
        self.assertEqual(data["TestBench"]["gpu_usage_data"], [30.0])
        sc.shutdown()

# ------------------------------------------------------------------------------
# Tests for the ShaderEngine and Shaders Folder Walk
# ------------------------------------------------------------------------------
def dummy_link_shader_program(self, shaders):
    return 2

@apply_opengl_patches
class TestShaderEngineAndShaders(unittest.TestCase):
    def setUp(self):
        # Manually patch glCreateProgram and glDeleteShader on the baseplatform.
        import OpenGL.platform.baseplatform as bp
        self._orig_glCreateProgram = getattr(bp, "glCreateProgram", None)
        bp.glCreateProgram = MagicMock(return_value=2)
        # Patch glDeleteShader using patch.object with create=True.
        self._delete_shader_patch = patch.object(bp, "glDeleteShader", MagicMock(return_value=None), create=True)
        self._delete_shader_patch.start()

        # Override discover_shaders in RendererConfig to use our shaders folder.
        def discover_shaders_override(self):
            shader_root = os.path.join(PROJECT_ROOT, "shaders")
            if not os.path.exists(shader_root):
                raise FileNotFoundError(f"Shaders folder not found: {shader_root}")
            for shader_type in ["vertex", "fragment", "compute"]:
                type_path = os.path.join(shader_root, shader_type)
                if not os.path.isdir(type_path):
                    continue
                for folder in os.listdir(type_path):
                    folder_path = os.path.join(type_path, folder)
                    shader_filename = "vertex.glsl" if shader_type == "vertex" else (
                        "fragment.glsl" if shader_type == "fragment" else "compute.glsl")
                    shader_file = os.path.join(folder_path, shader_filename)
                    if os.path.isfile(shader_file):
                        if shader_type not in self.shaders:
                            self.shaders[shader_type] = {}
                        self.shaders[shader_type][folder] = shader_file
        RendererConfig.discover_shaders = discover_shaders_override

        # Create a temporary directory structure with a "shaders" subfolder.
        self.temp_shaders_dir = tempfile.mkdtemp(prefix="test_shaders_")
        self.temp_shaders_root = os.path.join(self.temp_shaders_dir, "shaders")
        os.makedirs(os.path.join(self.temp_shaders_root, "vertex", "dummy"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_shaders_root, "fragment", "dummy"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_shaders_root, "compute", "dummy_compute"), exist_ok=True)

        # Create dummy shader files in proper structure.
        with open(os.path.join(self.temp_shaders_root, "vertex", "dummy", "vertex.glsl"), "w") as f:
            f.write("#version 330 core\nvoid main() {}")
        with open(os.path.join(self.temp_shaders_root, "fragment", "dummy", "fragment.glsl"), "w") as f:
            f.write("#version 330 core\nvoid main() {}")
        with open(os.path.join(self.temp_shaders_root, "compute", "dummy_compute", "compute.glsl"), "w") as f:
            f.write("#version 430 core\nvoid main() {}")

        # Patch RendererConfig.discover_shaders so it uses our temporary shaders folder.
        self.original_shaders_dir = RendererConfig.__init__.__globals__.get("PROJECT_ROOT", PROJECT_ROOT)
        RendererConfig.__init__.__globals__["PROJECT_ROOT"] = self.temp_shaders_dir

        # Patch _compile_shader to always return a dummy shader handle.
        self.compile_patch = patch.object(ShaderEngine, "_compile_shader", return_value=1)
        self.compile_patch.start()

        # Patch _link_shader_program to bypass glCreateProgram.
        self.link_patch = patch.object(ShaderEngine, "_link_shader_program", dummy_link_shader_program)
        self.link_patch.start()

    def tearDown(self):
        self.compile_patch.stop()
        self.link_patch.stop()
        self._delete_shader_patch.stop()
        shutil.rmtree(self.temp_shaders_dir)
        RendererConfig.__init__.__globals__["PROJECT_ROOT"] = self.original_shaders_dir
        try:
            import OpenGL.platform.baseplatform as bp
            if self._orig_glCreateProgram is None:
                del bp.glCreateProgram
            else:
                bp.glCreateProgram = self._orig_glCreateProgram
        except Exception:
            pass

    def test_compile_all_dummy_shaders(self):
        """Walk the temporary shaders folder and compile all dummy shaders."""
        shader_types = {"vertex": "vertex.glsl", "fragment": "fragment.glsl", "compute": "compute.glsl"}
        for stype, filename in shader_types.items():
            folder_path = os.path.join(self.temp_shaders_root, stype)
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file == filename:
                        shader_file = os.path.join(root, file)
                        rel_shader_file = os.path.relpath(shader_file, self.temp_shaders_dir)
                        if stype == "compute":
                            engine = ShaderEngine(
                                vertex_shader_path=None,
                                fragment_shader_path=None,
                                compute_shader_path=rel_shader_file,
                                shader_base_dir=self.temp_shaders_dir
                            )
                            self.assertIsNotNone(engine.compute_shader_program,
                                                 f"Failed to compile compute shader: {shader_file}")
                        else:
                            if stype == "vertex":
                                engine = ShaderEngine(
                                    vertex_shader_path=rel_shader_file,
                                    fragment_shader_path=None,
                                    shader_base_dir=self.temp_shaders_dir
                                )
                            else:
                                engine = ShaderEngine(
                                    vertex_shader_path=None,
                                    fragment_shader_path=rel_shader_file,
                                    shader_base_dir=self.temp_shaders_dir
                                )
                            self.assertIsNotNone(engine.shader_program,
                                                 f"Failed to compile {stype} shader: {shader_file}")

# ------------------------------------------------------------------------------
# Tests for GUI functions (Headless Mode)
# ------------------------------------------------------------------------------
class TestGUIHeadless(unittest.TestCase):
    @unittest.skipIf(App is None, "GUI module not available.")
    def test_app_instantiation_and_functions(self):
        """Test basic instantiation and functions of the GUI in headless mode."""
        app = App()
        app.withdraw()  # Hide the window
        try:
            app.change_appearance_mode_event("Light")
            app.display_demo_image()
            for key, data in app.benchmark_vars.items():
                data["var"].set(True)
            app.resolution_optionmenu.set("1024x768")
            app.msaa_level_optionmenu.set("4")
            app.anisotropy_optionmenu.set("16")
            app.shading_model_optionmenu.set("pbr")
            app.shadow_quality_optionmenu.set("2048x2048")
            app.particle_render_mode_optionmenu.set("transform feedback")
            app.enable_vsync_checkbox.select()
            app.sound_enabled_checkbox.select()
            threading.Thread(target=app.run_benchmark, daemon=True).start()
            time.sleep(0.5)
        finally:
            app.destroy()

# ------------------------------------------------------------------------------
# Tests for RenderingInstance and basic scene functions (with patched OpenGL)
# ------------------------------------------------------------------------------
@apply_opengl_patches
class TestRenderingInstanceHeadless(unittest.TestCase):
    def setUp(self):
        self.config = RendererConfig(window_title="TestInstance", window_size=(800, 600))
        self.config.duration = 0.5  # Short duration for testing
        self.config.shaders = {"vertex": {"dummy": "dummy.glsl"},
                               "fragment": {"dummy": "dummy.glsl"}}

    def test_rendering_instance_runs(self):
        instance = RenderingInstance(self.config)
        instance.setup = MagicMock()
        instance.render_scene = MagicMock()
        instance.shutdown = MagicMock()
        from multiprocessing import Event, Queue
        stop_event = Event()
        stats_queue = Queue()
        thread = threading.Thread(target=instance.run, args=(stats_queue, stop_event), daemon=True)
        thread.start()
        thread.join(timeout=2)
        instance.shutdown.assert_called()

# ------------------------------------------------------------------------------
# Main block to run tests if this module is executed directly.
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main()
