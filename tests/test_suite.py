"""
Extended Test Suite for the Fragment 3D Rendering Benchmark System (Headless/Pure Python)

This version removes all tests that relied on OpenGL calls (and thus caused NullFunctionError
or GLError in headless CI). The remaining tests focus on:

  - Pure-Python logic (e.g., camera interpolation, config generation, stats collection)
  - GUI logic tests that do not invoke a real OpenGL context
  - AudioPlayer tests using mock patches (no real audio file is required)

Run via:
  pytest --maxfail=1 --disable-warnings -q
or:
  python -m unittest discover -s tests
"""

import os
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

# Adjust PYTHONPATH to include project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --------------------------------------------------------------------------------
# Imports from your project (pure python modules, no OpenGL calls).
# --------------------------------------------------------------------------------
from components.camera_control import CameraController
from components.stats_collector import StatsCollector
from components.scene_constructor import SceneConstructor
from components.benchmark_manager import BenchmarkManager
from components.audio_player import AudioPlayer

# For GUI testing, try to import the App class (if available).
try:
    from gui.main_gui import App
except ImportError:
    App = None


# --------------------------------------------------------------------------------
# Dummy function for simulating a benchmark run.
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
# Tests for pure Python logic
# --------------------------------------------------------------------------------
class TestPurePythonExtended(unittest.TestCase):
    """
    Collection of tests for purely Python-based logic across your code.
    """

    def test_drop_shadow_function_in_gui(self):
        """
        Test the drop shadow function from the GUI module (if App is available).
        We simulate a simple image and ensure that a new image is returned.
        """
        from PIL import Image

        if App is None:
            self.skipTest("GUI module not available, skipping drop shadow function test.")

        app = App()
        # Create a simple 50x50 red image
        red_img = Image.new("RGBA", (50, 50), (255, 0, 0, 255))

        # Use the app's add_drop_shadow method
        shadow_img = app.add_drop_shadow(red_img, shadow_offset=(5, 5), blur_radius=5)
        self.assertTrue(isinstance(shadow_img, Image.Image))
        self.assertGreater(shadow_img.width, red_img.width)
        self.assertGreater(shadow_img.height, red_img.height)

        # Clean up the app
        app.destroy()

    def test_camera_controller_interpolation(self):
        """
        Test that CameraController properly interpolates camera positions and rotations.
        """
        positions = [(0, 0, 0, 0, 0), (10, 10, 10, 90, 45)]
        lens = [0, 90]
        cc = CameraController(positions, lens_rotations=lens, move_speed=1.0, loop=False)

        # Step halfway
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

        # Mock CPU and GPU usage
        with sc.usage_lock:
            sc.cpu_usage = 20.0
            sc.gpu_usage = 30.0

        # Add a data point
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

        # Translate, rotate, scale, set auto-rotation
        sc.translate_renderer("test_renderer", (1, 2, 3))
        sc.rotate_renderer("test_renderer", 45, (0, 1, 0))
        sc.scale_renderer("test_renderer", (2, 2, 2))
        sc.set_auto_rotation("test_renderer", True, axis=(0, 1, 0), speed=1000)

        # Ensure the calls went to the mock properly
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
        Test adding benchmarks to the manager. We won't fully run them in multiple processes,
        but we can check they get registered properly.
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
    We'll mock pygame.mixer so no file I/O or audio device is needed.
    """

    @patch("pygame.mixer.init")
    @patch("pygame.mixer.music.load")
    @patch("pygame.mixer.music.play")
    @patch("pygame.mixer.music.get_busy", return_value=True)
    @patch("pygame.mixer.music.stop")
    @patch("pygame.mixer.quit")
    def test_audio_player_start_stop(
            self, mock_quit, mock_stop, mock_busy, mock_play, mock_load, mock_init
    ):
        # Create the player with a "fake.wav" filename
        ap = AudioPlayer(audio_file="fake.wav", delay=0.0, loop=False)
        # Start playback
        ap.start()

        # Check that load, init, and play were called
        mock_init.assert_called_once()
        mock_load.assert_called_with("fake.wav")
        mock_play.assert_called_with(-1 if ap.loop else 0)

        # Now stop
        ap.stop()

        # Ensure music.stop() and mixer.quit() were called
        mock_stop.assert_called_once()
        mock_quit.assert_called_once()

        # The event is_playing should be cleared
        self.assertFalse(ap.is_playing.is_set())


# --------------------------------------------------------------------------------
# GUI tests (in headless mode). We avoid any real rendering contexts.
# --------------------------------------------------------------------------------
class TestGUIHeadless(unittest.TestCase):
    """
    Tests for GUI functionality in headless mode (does NOT invoke OpenGL).
    """

    @unittest.skipIf(App is None, "GUI module not available.")
    def test_app_instantiation_and_functions(self):
        """
        Test basic instantiation and some config changes of the GUI in headless mode.
        This should not require OpenGL calls if the user doesn't start actual rendering.
        """
        app = App()
        app.withdraw()  # Hide the window

        try:
            # Switch appearance mode
            app.change_appearance_mode_event("Light")
            # Check we can mark all benchmarks in the scenario tab
            for key, data in app.benchmark_vars.items():
                data["var"].set(True)

            # Change some settings
            app.resolution_optionmenu.set("1024x768")
            app.msaa_level_optionmenu.set("4")
            app.anisotropy_optionmenu.set("16")
            app.shading_model_optionmenu.set("pbr")
            app.shadow_quality_optionmenu.set("2048x2048")
            app.particle_render_mode_optionmenu.set("transform feedback")
            app.enable_vsync_checkbox.select()
            app.sound_enabled_checkbox.select()

            # Start run_benchmark in a separate thread (we won't wait for it fully)
            threading.Thread(target=app.run_benchmark, daemon=True).start()
            time.sleep(0.2)  # Let it spin briefly
        finally:
            app.destroy()


# --------------------------------------------------------------------------------
# Main block to run tests if this module is executed directly.
# --------------------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main()
