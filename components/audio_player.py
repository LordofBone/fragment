import threading
import time

import pygame


class AudioPlayer:
    def __init__(self, audio_file=None, delay=0.0, loop=False):
        self.audio_file = audio_file
        self.delay = delay
        self.loop = loop
        self.is_playing = False
        self.thread = None

    def start(self):
        if self.audio_file is None:
            return

        # Initialize the mixer in a separate thread to prevent blocking
        self.thread = threading.Thread(target=self.play_audio)
        self.thread.daemon = True
        self.thread.start()

    def play_audio(self):
        if self.delay > 0.0:
            time.sleep(self.delay)
        pygame.mixer.init()
        pygame.mixer.music.load(self.audio_file)
        pygame.mixer.music.play(-1 if self.loop else 0)
        self.is_playing = True
        while self.is_playing:
            if not pygame.mixer.music.get_busy():
                break
            time.sleep(0.1)

    def stop(self):
        self.is_playing = False
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        if self.thread and self.thread.is_alive():
            self.thread.join()
