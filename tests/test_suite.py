"""
Extended Test Suite for the Fragment 3D Rendering Benchmark System (Headless/Pure Python)

This version omits any OpenGL or GPU-accelerated tests to avoid NullFunctionError
or GLError in headless CI. The tests focus on:

  - Config logic (RendererConfig), including shader discovery, add_model, add_surface,
    add_skybox, and unpack behavior.
  - Camera interpolation (CameraController)
  - Stats collection (StatsCollector)
  - Scene construction logic (SceneConstructor)
  - Benchmark management (BenchmarkManager) with a dummy run function
  - AudioPlayer logic via mocking pygame.mixer (no real audio file required)
  - Basic GUI interactions in headless mode (if App is available)

Run via:
  pytest --html-report=./report/report.html
or:
  python -m unittest discover -s tests
"""

import contextlib
import io
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

# Adjust PYTHONPATH to include project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --------------------------------------------------------------------------------
# Pure-Python Components
# --------------------------------------------------------------------------------
from components.audio_player import AudioPlayer
from components.benchmark_manager import BenchmarkManager
from components.camera_control import CameraController
from components.renderer_config import RendererConfig
from components.scene_constructor import SceneConstructor
from components.stats_collector import StatsCollector

# For GUI testing, try to import the App class (if available).
try:
    from gui.main_gui import App
except ImportError:
    App = None


# --------------------------------------------------------------------------------
# Dummy function for simulating a benchmark run (no real GL/audio).
# --------------------------------------------------------------------------------
def dummy_run_function(
    stats_queue,
    stop_event,
    resolution,
    msaa_level,
    anisotropy,
    shading_model,
    shadow_map_resolution,
    particle_render_mode,
    vsync_enabled,
    sound_enabled,
    fullscreen,
):
    """
    Fake run function that simulates a short wait and pushes some 'fps' messages
    into stats_queue. Avoids any real OpenGL or audio calls.
    """
    if stats_queue is not None:
        stats_queue.put(("ready", None))
        for _ in range(3):
            stats_queue.put(("fps", 60))
            time.sleep(0.01)
    time.sleep(0.05)


# --------------------------------------------------------------------------------
# Helper: Walk the shaders directory and return a dictionary of discovered shaders.
# --------------------------------------------------------------------------------
def walk_shaders_dir(shader_root):
    """
    Walk the shader root directory and return a dictionary mapping shader types
    ("vertex", "fragment", "compute") to a dict of {shader_dir: absolute_path}.
    """
    result = {}
    for shader_type in ["vertex", "fragment", "compute"]:
        type_path = os.path.join(shader_root, shader_type)
        if not os.path.exists(type_path):
            continue
        for shader_dir in os.listdir(type_path):
            dir_path = os.path.join(type_path, shader_dir)
            shader_file_path = os.path.join(dir_path, f"{shader_type}.glsl")
            if os.path.exists(shader_file_path):
                if shader_type not in result:
                    result[shader_type] = {}
                result[shader_type][shader_dir] = os.path.abspath(shader_file_path)
    return result


# --------------------------------------------------------------------------------
# Tests: RendererConfig and Config Logic
# --------------------------------------------------------------------------------
class TestRendererConfig(unittest.TestCase):
    """
    Tests around RendererConfig to ensure it accepts/validates configuration properly.
    """

    maxDiff = None

    def test_basic_initialization(self):
        """
        Verify that RendererConfig can be constructed with minimal arguments
        and has the default attributes.
        """

        rc = RendererConfig(window_title="Test", window_size=(800, 600))
        self.assertEqual(rc.window_title, "Test")
        self.assertEqual(rc.window_size, (800, 600))
        self.assertTrue(rc.vsync_enabled)
        self.assertFalse(rc.fullscreen)
        self.assertEqual(rc.lighting_mode, "diffuse")  # default

    def test_shader_discovery(self):
        """
        Test that discover_shaders() correctly walks the shader directory.
        The expected dictionary is computed by walk_shaders_dir().
        If the shaders directory does not exist, skip this test.
        """
        shader_root = os.path.abspath(os.path.join("shaders"))
        if not os.path.exists(shader_root):
            self.skipTest("Shaders directory does not exist.")
        rc = RendererConfig(window_title="Test", window_size=(800, 600))
        rc.discover_shaders()
        expected = walk_shaders_dir(shader_root)
        self.assertEqual(rc.shaders, expected)

    def test_add_model_valid(self):
        """
        Test that add_model accepts valid overrides (e.g. front_face_winding, lighting_mode).
        """
        rc = RendererConfig(window_title="RCtest")
        model_cfg = rc.add_model(
            obj_path="mesh.obj",
            texture_paths={"diffuse": "mesh_diffuse.png"},
            front_face_winding="CW",
            lighting_mode="phong",
            legacy_roughness=32,
            debug_mode=True,
        )
        self.assertEqual(model_cfg["obj_path"], "mesh.obj")
        self.assertEqual(model_cfg["front_face_winding"], "CW")
        self.assertEqual(model_cfg["lighting_mode"], "phong")
        self.assertEqual(model_cfg["legacy_roughness"], 32)
        self.assertTrue(model_cfg["debug_mode"])

    def test_add_model_invalid_front_face_winding(self):
        """
        Test that add_model rejects an invalid front_face_winding.
        """
        rc = RendererConfig()
        with self.assertRaises(ValueError) as ctx:
            rc.add_model(
                obj_path="mesh.obj",
                texture_paths={"diffuse": "mesh_diffuse.png"},
                front_face_winding="INVALID",  # Not "CW" or "CCW"
            )
        self.assertIn("Invalid front_face_winding option", str(ctx.exception))

    def test_add_model_invalid_lighting_mode(self):
        """
        Test that add_model rejects an invalid lighting mode string.
        """
        rc = RendererConfig()
        with self.assertRaises(ValueError) as ctx:
            rc.add_model(
                obj_path="mesh.obj",
                texture_paths={"diffuse": "mesh_diffuse.png"},
                lighting_mode="cartoon",  # not diffuse/phong/pbr
            )
        self.assertIn("Invalid lighting mode option", str(ctx.exception))

    def test_add_model_invalid_legacy_roughness_range(self):
        """
        Test that add_model rejects legacy_roughness out of [0, 100] range if lighting mode is 'phong'.
        """
        rc = RendererConfig()
        with self.assertRaises(ValueError) as ctx:
            rc.add_model(
                obj_path="mesh.obj",
                texture_paths={"diffuse": "mesh_diffuse.png"},
                lighting_mode="phong",
                legacy_roughness=200,  # out of range
            )
        self.assertIn("Invalid legacy_roughness value", str(ctx.exception))

    def test_add_model_valid_pbr_overrides(self):
        """
        Test that valid PBR override keys are accepted and stored correctly.
        """
        rc = RendererConfig(window_title="RCtest")
        model_cfg = rc.add_model(
            obj_path="mesh.obj",
            texture_paths={"diffuse": "mesh_diffuse.png"},
            pbr_extension_overrides={"roughness": 0.3, "metallic": 0.7, "sheen": 0.2},
        )
        # Check that the returned config contains the valid pbr overrides.
        self.assertEqual(model_cfg["pbr_extension_overrides"]["roughness"], 0.3)
        self.assertEqual(model_cfg["pbr_extension_overrides"]["metallic"], 0.7)
        self.assertEqual(model_cfg["pbr_extension_overrides"]["sheen"], 0.2)

    def test_add_model_invalid_pbr_overrides(self):
        """
        Test that invalid PBR overrides are rejected.
        """
        rc = RendererConfig(window_title="RCtest")
        with self.assertRaises(ValueError) as ctx:
            rc.add_model(
                obj_path="mesh.obj",
                texture_paths={"diffuse": "mesh_diffuse.png"},
                pbr_extension_overrides={"bread": 1, "cheese": 2},
            )
        self.assertIn("No such material property: bread, cheese", str(ctx.exception))
        self.assertIn("available pbr overrides are:", str(ctx.exception))

    def test_add_particle_renderer_valid(self):
        """
        Test valid particle renderer config.
        """
        rc = RendererConfig()
        pcfg = rc.add_particle_renderer(
            particle_render_mode="cpu",
            particle_type="points",
            alpha_blending=True,
        )
        self.assertEqual(pcfg["particle_render_mode"], "cpu")
        self.assertTrue(pcfg["alpha_blending"])
        self.assertEqual(pcfg["particle_type"], "points")

    def test_add_particle_renderer_invalid_mode(self):
        """
        Test that an invalid particle_render_mode is rejected.
        """
        rc = RendererConfig()
        with self.assertRaises(ValueError) as ctx:
            rc.add_particle_renderer(particle_render_mode="invalid_mode")
        self.assertIn("Invalid particle render mode option", str(ctx.exception))

    def test_add_particle_renderer_invalid_type(self):
        """
        Test that an invalid particle_type is rejected.
        """
        rc = RendererConfig()
        with self.assertRaises(ValueError) as ctx:
            rc.add_particle_renderer(particle_render_mode="cpu", particle_type="unknown_primitive")
        self.assertIn("Invalid particle type option", str(ctx.exception))

    def test_add_surface_valid(self):
        """
        Test that add_surface accepts valid overrides and extra keyword arguments.
        """
        rc = RendererConfig(window_title="SurfaceTest", window_size=(1024, 768))
        surface_cfg = rc.add_surface(
            shader_names=("basic", "default"),
            width=600.0,
            height=400.0,
            cubemap_folder="textures/cube",
            debug_mode=True,
            extra_param="extra_value",
        )
        self.assertEqual(surface_cfg["shader_names"], ("basic", "default"))
        self.assertEqual(surface_cfg["width"], 600.0)
        self.assertEqual(surface_cfg["height"], 400.0)
        self.assertEqual(surface_cfg["cubemap_folder"], "textures/cube")
        self.assertEqual(surface_cfg["debug_mode"], True)
        self.assertEqual(surface_cfg["extra_param"], "extra_value")

    def test_add_skybox_valid(self):
        """
        Test that add_skybox accepts valid parameters and extra keyword arguments.
        """
        rc = RendererConfig(window_title="SkyboxTest", window_size=(800, 600))
        skybox_cfg = rc.add_skybox(
            cubemap_folder="textures/skybox", shader_names=("skybox_vertex", "skybox_fragment"), extra_setting="extra"
        )
        self.assertEqual(skybox_cfg["cubemap_folder"], "textures/skybox")
        self.assertEqual(skybox_cfg["shader_names"], ("skybox_vertex", "skybox_fragment"))
        self.assertEqual(skybox_cfg["extra_setting"], "extra")

    def test_unpack_returns_copy(self):
        """
        Test that unpack() returns a deep copy of the configuration dictionary.
        Modifying the returned dict should not affect the original config.
        """
        rc = RendererConfig(window_title="UnpackTest", window_size=(800, 600))
        data1 = rc.unpack()
        data1["window_title"] = "Changed"
        data2 = rc.unpack()
        self.assertNotEqual(data2["window_title"], "Changed")
        self.assertEqual(data2["window_title"], "UnpackTest")


# --------------------------------------------------------------------------------
# Tests: Other Pure Python Logic
# --------------------------------------------------------------------------------
class TestPurePythonExtended(unittest.TestCase):
    """
    Collection of tests for other purely Python-based logic across your code.
    """

    def test_camera_controller_interpolation(self):
        """
        Test that CameraController properly interpolates camera positions and rotations.
        """
        positions = [(0, 0, 0, 0, 0), (10, 10, 10, 90, 45)]
        lens = [0, 90]
        cc = CameraController(positions, lens_rotations=lens, move_speed=1.0, loop=False)
        pos, rot = cc.update(0.5)
        self.assertGreater(pos.x, 0)
        self.assertLess(pos.x, 10)
        self.assertGreaterEqual(rot.x, 0)
        self.assertLessEqual(rot.x, 90)

    def test_stats_collector_add_point(self):
        """
        Test that StatsCollector properly adds data points (fps, CPU, GPU usage).
        """
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

    def test_scene_constructor_basic_actions(self):
        """
        Test basic scene actions in SceneConstructor (translation, rotation, scaling).
        We mock out the AbstractRenderer so no real rendering calls occur.
        """
        from components.abstract_renderer import AbstractRenderer

        sc = SceneConstructor()
        mock_renderer = MagicMock(spec=AbstractRenderer)
        sc.add_renderer("test_renderer", mock_renderer)
        sc.translate_renderer("test_renderer", (1, 2, 3))
        sc.rotate_renderer("test_renderer", 45, (0, 1, 0))
        sc.scale_renderer("test_renderer", (2, 2, 2))
        sc.set_auto_rotation("test_renderer", True, axis=(0, 1, 0), speed=1000)
        mock_renderer.translate.assert_called_with((1, 2, 3))
        mock_renderer.rotate.assert_called_with(45, (0, 1, 0))
        mock_renderer.scale.assert_called_with((2, 2, 2))
        mock_renderer.enable_auto_rotation.assert_called_with(True, axis=(0, 1, 0), speed=1000)


class TestBenchmarkManagerHeadless(unittest.TestCase):
    """
    Tests for the BenchmarkManager to verify logic without real rendering or processes.
    """

    def setUp(self):
        from multiprocessing import Event

        self.stop_event = Event()
        self.manager = BenchmarkManager(self.stop_event)

    def test_add_and_run_benchmarks(self):
        """
        Test adding benchmarks to the manager. We check they are registered properly.
        """
        self.manager.add_benchmark(
            name="TestBenchmark",
            run_function=dummy_run_function,
            resolution=(800, 600),
            msaa_level=4,
            anisotropy=16,
            shading_model="pbr",
            shadow_map_resolution=1024,
            particle_render_mode="vertex",
            vsync_enabled=True,
            sound_enabled=False,
            fullscreen=False,
        )
        self.assertEqual(len(self.manager.benchmarks), 1)
        self.assertEqual(self.manager.benchmarks[0]["name"], "TestBenchmark")


# --------------------------------------------------------------------------------
# AudioPlayer tests with mocked pygame mixer calls
# --------------------------------------------------------------------------------
class TestAudioPlayer(unittest.TestCase):
    """
    Test the AudioPlayer class logic without requiring a real audio file.
    We'll patch pygame.mixer so no file I/O or audio device is needed.
    """

    @patch("pygame.mixer.get_init", return_value=True)
    @patch("pygame.mixer.init")
    @patch("pygame.mixer.music.load")
    @patch("pygame.mixer.music.play")
    @patch("pygame.mixer.music.get_busy", return_value=True)
    @patch("pygame.mixer.music.stop")
    @patch("pygame.mixer.quit")
    def test_audio_player_start_stop(
        self, mock_quit, mock_stop, mock_get_busy, mock_play, mock_load, mock_init, mock_get_init
    ):
        ap = AudioPlayer(audio_file="fake.wav", delay=0.0, loop=False)
        ap.start()
        mock_init.assert_called_once()
        mock_load.assert_called_with("fake.wav")
        mock_play.assert_called_with(-1 if ap.loop else 0)
        ap.stop()
        mock_stop.assert_called_once()
        mock_quit.assert_called_once()
        self.assertFalse(ap.is_playing.is_set())


# --------------------------------------------------------------------------------
# GUI tests (in headless mode). We avoid any real rendering contexts.
# --------------------------------------------------------------------------------
# Dummy process to avoid spawning real processes
class DummyProcess:
    def __init__(self, *args, **kwargs):
        self.pid = 1234

    def start(self):
        pass

    def is_alive(self):
        return False

    def terminate(self):
        pass

    def join(self):
        pass


# DummyThread that runs target code immediately on the same thread
class DummyThread:
    def __init__(self, target=None, args=(), kwargs=None, daemon=None):
        self.target = target
        self.args = args
        self.kwargs = kwargs if kwargs is not None else {}
        self.daemon = daemon

    def start(self):
        # No real threading: just run on the same thread.
        self.run()

    def run(self):
        if self.target:
            self.target(*self.args, **self.kwargs)


class TestGUIHeadless(unittest.TestCase):
    """
    Note:
      When running GUI tests in headless mode, you might see several "invalid command name" errors
      (e.g. "invalid command name '...update'") and resource warnings regarding unclosed files.
      These messages occur because Tkinter's scheduled callbacks (via 'after') can be left pending
      when the application is destroyed, and some image file handles remain open.
      These warnings are harmless and do not affect the test outcomes.
    """

    @classmethod
    def setUpClass(cls):
        # Optionally suppress ResourceWarnings and redirect stderr
        cls._stderr = io.StringIO()
        cls._stderr_context = contextlib.redirect_stderr(cls._stderr)
        cls._stderr_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._stderr_context.__exit__(None, None, None)

    @unittest.skipIf(App is None, "GUI module not available.")
    # (1) Patch StatsCollector.monitor_system_usage to immediately return
    @patch("components.stats_collector.StatsCollector.monitor_system_usage", return_value=None)
    # (2) Patch BenchmarkManager.run_benchmarks so it returns immediately
    @patch("components.benchmark_manager.BenchmarkManager.run_benchmarks", return_value=None)
    # (3) Patch the Image.open used in gui.main_gui (not PIL.Image.open).
    @patch("gui.main_gui.Image.open")
    # (4) Patch Process and Thread so that real processes/threads are not spawned.
    @patch("components.benchmark_manager.Process", new=DummyProcess)
    @patch("gui.main_gui.pygame.init", lambda: None)
    @patch("gui.main_gui.threading.Thread", new=DummyThread)
    @patch("gui.main_gui.pygame.display.Info", new=lambda: type("FakeInfo", (), {"current_w": 800, "current_h": 600})())
    def test_app_instantiation_and_functions(self, mock_image_open, mock_run_benchmarks, mock_monitor_system_usage):
        """
        Test the GUI in headless mode without spawning real threads
        or blocking in StatsCollector's infinite loop.
        """
        # Create dummy image
        dummy_image = Image.new("RGBA", (100, 100), (255, 255, 255, 255))
        dummy_image.close = lambda: None
        mock_image_open.return_value = dummy_image

        # Instantiate the GUI
        app = App()
        app.withdraw()

        def immediate_after(delay, func, *args, **kwargs):
            func(*args, **kwargs)
            return "dummy"

        app.after = immediate_after

        # Optionally disable progress bar
        if hasattr(app, "loading_progress_bar"):
            app.loading_progress_bar.after_cancel = lambda id: None
            app.loading_progress_bar.stop = lambda: None

        try:
            # Set up the GUI state
            app.change_appearance_mode_event("Light")
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

            # Kick off the benchmark (synchronous because we patched Thread).
            app.after(0, app.run_benchmark)
            app.update()
            time.sleep(0.2)

            # Confirm that run_benchmarks was called exactly once
            mock_run_benchmarks.assert_called_once()

            # Confirm StatsCollector.monitor_system_usage got called
            # (or not) depending on your needs:
            mock_monitor_system_usage.assert_called_once()

        finally:
            app.destroy()

    # -------------------------------------------------------------------------
    # Tests verifying display_image logic
    # -------------------------------------------------------------------------

    @unittest.skipIf(App is None, "GUI module not available.")
    @patch("os.path.exists")
    @patch("gui.main_gui.Image.open")
    def test_display_image_valid(self, mock_image_open, mock_path_exists):
        """
        Test that display_image with a valid name leads to a non-None image
        in image_area.
        """
        mock_path_exists.return_value = True
        dummy_image = Image.new("RGBA", (200, 200), (255, 255, 255, 255))
        dummy_image.close = lambda: None
        mock_image_open.return_value = dummy_image

        app = App()
        app.withdraw()

        # Disable resizing logic
        app.on_window_resize = lambda e=None: None
        app.unbind("<Configure>")

        # Immediate after
        app.after = lambda delay, func, *args, **kwargs: func(*args, **kwargs) or "dummy"
        app.after_cancel = lambda id: None

        try:
            valid_name = "Shimmer (Demo)"
            app.display_image(valid_name)
            self.assertEqual(app.currently_selected_benchmark_name, valid_name)
            self.assertIsNotNone(
                getattr(app.image_area, "image", None), f"Image for benchmark '{valid_name}' should be loaded."
            )
        finally:
            app.destroy()

    @unittest.skipIf(App is None, "GUI module not available.")
    @patch("os.path.exists")
    def test_display_image_invalid(self, mock_path_exists):
        """
        Test that display_image with an invalid name sets image_area to image=None.
        """
        mock_path_exists.return_value = False
        app = App()
        app.withdraw()

        # Disable resizing logic
        app.on_window_resize = lambda e=None: None
        app.unbind("<Configure>")

        app.after = lambda delay, func, *args, **kwargs: func(*args, **kwargs) or "dummy"
        app.after_cancel = lambda id: None

        configure_mock = MagicMock()
        app.image_area.configure = configure_mock

        try:
            invalid_name = "NonExistentBenchmark"
            app.display_image(invalid_name)
            configure_mock.assert_called_with(image=None)
        finally:
            app.destroy()

    @unittest.skipIf(App is None, "GUI module not available.")
    @patch("os.path.exists")
    @patch("gui.main_gui.Image.open")
    def test_all_benchmark_images_loaded(self, mock_image_open, mock_path_exists):
        """
        For each benchmark name, display_image is called, verifying the image_area
        has a non-None image (assuming the file exists).
        """

        def exists_side_effect(path):
            return path.endswith(".png")

        mock_path_exists.side_effect = exists_side_effect

        dummy_image = Image.new("RGBA", (150, 150), (255, 255, 255, 255))
        dummy_image.close = lambda: None
        mock_image_open.return_value = dummy_image

        app = App()
        app.withdraw()

        # Disable resizing logic
        app.on_window_resize = lambda e=None: None
        app.unbind("<Configure>")

        app.after = lambda delay, func, *args, **kwargs: func(*args, **kwargs) or "dummy"
        app.after_cancel = lambda id: None

        try:
            for benchmark in app.benchmark_vars.keys():
                app.display_image(benchmark)
                self.assertIsNotNone(
                    app.image_area.image,
                    f"Image for benchmark '{benchmark}' should be loaded from '{app.image_folder}'.",
                )
        finally:
            app.destroy()

    @unittest.skipIf(App is None, "GUI module not available.")
    def test_display_image_rejects_invalid_names(self):
        """
        Negative test: if a name doesn't exist or the file is missing,
        image_area is set to image=None.
        """
        original_exists = os.path.exists
        os.path.exists = lambda path: False  # Force non-existence

        app = App()
        app.withdraw()

        # Disable resizing logic
        app.on_window_resize = lambda e=None: None
        app.unbind("<Configure>")

        app.after = lambda delay, func, *args, **kwargs: func(*args, **kwargs) or "dummy"
        app.after_cancel = lambda id: None

        configure_mock = MagicMock()
        app.image_area.configure = configure_mock

        try:
            fake_name = "FakeBenchmarkName"
            app.display_image(fake_name)
            configure_mock.assert_called_with(image=None)
        finally:
            os.path.exists = original_exists
            app.destroy()


# --------------------------------------------------------------------------------
# Main block to run tests if this module is executed directly.
# --------------------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main()
