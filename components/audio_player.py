import threading
import time

import pygame


class AudioPlayer:
    def __init__(self, audio_file=None, delay=0.0, loop=False):
        self.audio_file = audio_file
        self.delay = delay
        self.loop = loop
        self.is_playing = threading.Event()
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        if self.audio_file is None:
            return

        # Initialize the mixer before starting the thread
        pygame.mixer.init()
        pygame.mixer.music.load(self.audio_file)

        # Set the event to indicate playback is ongoing
        self.is_playing.set()

        # Start the audio playback in a separate thread
        self.thread = threading.Thread(target=self.play_audio)
        self.thread.daemon = True
        self.thread.start()

    def play_audio(self):
        if self.delay > 0.0:
            time.sleep(self.delay)

        # Start playing the audio
        pygame.mixer.music.play(-1 if self.loop else 0)

        while not self.stop_event.is_set():
            # Check if the mixer is initialized
            if not pygame.mixer.get_init():
                break
            try:
                if not pygame.mixer.music.get_busy():
                    break
            except pygame.error:
                # Mixer might have been uninitialized; exit the loop
                break
            time.sleep(0.1)

        # Playback finished or stopped; clear the is_playing event
        self.is_playing.clear()

    def stop(self):
        # Signal the play_audio thread to stop
        self.stop_event.set()

        # Wait for the playback thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join()

        # Stop the music and uninitialize the mixer
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.quit()
