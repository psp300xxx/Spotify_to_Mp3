
from enum import Enum

class DownloaderConstants(Enum):

    YOUTUBE_LINK = "https://www.youtube.com"

    def get_value(self):
        return self.value