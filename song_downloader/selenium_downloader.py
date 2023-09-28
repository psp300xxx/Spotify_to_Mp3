from typing import List

from selenium import webdriver

from song_downloader.downloader import Downloader



class SeleniumSongDownloader(Downloader):

    def __init__(self, song_list: List[str], web_driver: webdriver.Remote):
        self.list = song_list
        self.web_driver: webdriver.Remote = web_driver

    def __init__(self, song_list: List[str]):
        self.list = song_list
        self.web_driver: webdriver.Remote= webdriver.Firefox()

    def get_list(self) -> List[str]:
        return self.list

    def start_download(self):
        raise RuntimeError("Not implemented yet")