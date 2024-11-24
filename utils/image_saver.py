import os
from datetime import datetime
from threading import Lock

from utils.decorators import singleton


@singleton
class ImageSaver:
    def __init__(self, screenshots_dir='screenshots', timestamp_format='%Y%m%d_%H%M%S'):
        self.screenshots_dir = screenshots_dir
        self.timestamp_format = timestamp_format
        self.lock = Lock()
        # Create the directory if it doesn't exist
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)

    def save_image(self, image, filename, timestamped=True):
        """
        Save the image with an optional timestamped filename.

        Parameters:
        - image: The PIL Image object to be saved.
        - filename: The base filename for the image.
        - timestamped: Boolean indicating whether to append a timestamp.

        The image will be saved in the screenshots directory.
        """
        with self.lock:
            if timestamped:
                # Get the current timestamp
                timestamp = datetime.now().strftime(self.timestamp_format)

                # Extract the file extension
                name, ext = os.path.splitext(filename)
                if not ext:
                    ext = '.png'  # Default to .png if no extension is provided

                # Create the timestamped filename
                filename = f"{name}_{timestamp}{ext}"

            # Construct the full file path
            file_path = os.path.join(self.screenshots_dir, filename)

            # Save the image
            image.save(file_path)

            print(f"Image saved to {file_path}")
