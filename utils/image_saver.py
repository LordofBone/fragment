import os
from datetime import datetime
from threading import Lock

from utils.decorators import singleton


@singleton
class ImageSaver:
    """
    Singleton class to save images to a designated screenshots directory.

    Each saved image can have a timestamp appended to its filename.
    """

    def __init__(self, screenshots_dir="screenshots", timestamp_format="%Y%m%d_%H%M%S"):
        self.screenshots_dir = screenshots_dir
        self.timestamp_format = timestamp_format
        self.lock = Lock()
        # Create the screenshots directory if it doesn't exist.
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)

    def save_image(self, image, filename, timestamped=True):
        """
        Save a PIL Image object to the screenshots directory.

        Parameters:
            image (PIL.Image): The image to be saved.
            filename (str): The base filename for the image.
            timestamped (bool): If True, a timestamp is appended to the filename.

        The image is saved in the screenshots directory specified in self.screenshots_dir.
        """
        with self.lock:
            if timestamped:
                # Get the current timestamp.
                timestamp = datetime.now().strftime(self.timestamp_format)

                # Extract the file name and extension; default to .png if none provided.
                name, ext = os.path.splitext(filename)
                if not ext:
                    ext = ".png"
                filename = f"{name}_{timestamp}{ext}"

            # Construct the full file path.
            file_path = os.path.join(self.screenshots_dir, filename)

            # Save the image.
            image.save(file_path)

            print(f"Image saved to {file_path}")
