# ------------------------------------------------------------------------------
# Imports
# ------------------------------------------------------------------------------
import threading
import time

import pygame


# ------------------------------------------------------------------------------
# AudioPlayer Class
# ------------------------------------------------------------------------------
class AudioPlayer:
    """
    AudioPlayer handles audio playback using pygame.

    It supports an optional playback delay and looping functionality.
    Audio playback occurs in a separate thread so as not to block the main program.
    """

    def __init__(self, audio_file=None, delay=0.0, loop=False):
        # --------------------------------------------------------------------------
        # Initialization of Audio Playback Settings
        # --------------------------------------------------------------------------
        self.audio_file = audio_file  # Path to the audio file
        self.delay = delay  # Optional delay (in seconds) before playback starts
        self.loop = loop  # Boolean flag to enable looping playback

        # --------------------------------------------------------------------------
        # Thread Control Attributes
        # --------------------------------------------------------------------------
        self.is_playing = threading.Event()  # Event flag to indicate if playback is active
        self.stop_event = threading.Event()  # Event flag to signal the playback thread to stop
        self.thread = None  # Handle for the playback thread

    def start(self):
        """
        Start audio playback.

        If an audio file is provided, initializes the pygame mixer,
        loads the audio file, and starts playback in a separate daemon thread.
        """
        if self.audio_file is None:
            return

        # Initialize the mixer and load the audio file
        pygame.mixer.init()
        pygame.mixer.music.load(self.audio_file)

        # Indicate that playback is starting
        self.is_playing.set()

        # Start the playback thread
        self.thread = threading.Thread(target=self.play_audio)
        self.thread.daemon = True
        self.thread.start()

    def play_audio(self):
        """
        Thread target function to handle audio playback.

        This method waits for the optional delay, starts the audio playback
        (looping if required), and monitors playback status until completion
        or until a stop signal is received.
        """
        if self.delay > 0.0:
            time.sleep(self.delay)

        # Start playing the audio; loop indefinitely if self.loop is True
        pygame.mixer.music.play(-1 if self.loop else 0)

        while not self.stop_event.is_set():
            # Break out if the mixer is no longer initialized
            if not pygame.mixer.get_init():
                break
            try:
                # If playback is finished, exit the loop
                if not pygame.mixer.music.get_busy():
                    break
            except pygame.error:
                # In case the mixer was uninitialized or encounters an error
                break
            time.sleep(0.1)

        # Clear the playback flag when finished or stopped
        self.is_playing.clear()

    def stop(self):
        """
        Stop audio playback.

        Signals the playback thread to stop, waits for it to finish,
        stops the audio, and quits the mixer.
        """
        # Signal the playback thread to stop
        self.stop_event.set()

        # Wait for the thread to finish if it is still active
        if self.thread and self.thread.is_alive():
            self.thread.join()

        # Stop the music and uninitialize the mixer if it is still active
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.quit()
