import json
import logging
import os.path
import sys
from typing import List
from pytube import YouTube

from youtubesearchpython import VideoSortOrder, CustomSearch

import multiprocessing

from commons import constants
from commons.Song import Song
from song_downloader.downloader import Downloader

SONG_TITLE_ACCEPTABILITY = 0.5

LOGGER = logging.getLogger("youtube_song_downloader")
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
file_handler = logging.FileHandler(constants.LOG_FILE)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)
LOGGER.addHandler(file_handler)
# LOGGER.addHandler(sysout_handler)



class YoutubeSongDownloader(Downloader):

    def __init__(self, song_list: List[Song], destination_dir: str):
        self.list = song_list
        self.queue: multiprocessing.Queue = None
        self.failed_array: multiprocessing.Array = None
        self.success_array: multiprocessing.Array = None
        self.destination_dir: str = destination_dir

    def get_list(self) -> List[str]:
        return self.list

    def get_destination_dir(self):
        return self.destination_dir

    def __put_songs_in_queue__(self):
        self.queue = multiprocessing.Queue()
        for song in self.list:
            self.queue.put(song)

    def start_download(self):
        self.__put_songs_in_queue__()
        processes = list()
        for i in range(multiprocessing.cpu_count()):
            process = multiprocessing.Process(target=self.download_from_queue, args=(self.queue,))
            processes.append(process)
        for process in processes:
            process.start()
        for process in processes:
            process.join()

    def get_next_song(self, queue) -> Song:
        try:
            return queue.get(block=True, timeout=0.5)
        except Exception as exc:
            return None

    @staticmethod
    def compare_videos(a: dict, b: dict, song: Song) -> int:
        a_view_string = a["viewCount"]["text"]
        b_view_string = b["viewCount"]["text"]
        if a_view_string is None or a_view_string == "No views":
            return 2
        if b_view_string is None or b_view_string == "No views":
            return 1
        if song.get_name() not in a["title"]:
            return 2
        if song.get_name() not in b["title"]:
            return 1
        a_views = int(a_view_string.split()[0].replace(",",""))
        b_views = int(b_view_string.split()[0].replace(",",""))
        return 1 if a_views > b_views else 2

    @staticmethod
    def is_privileged_channel(privileged_channels: list, result: dict):
        channel = result["channel"]["name"]
        for chan in privileged_channels:
            if chan in channel:
                return True
        return False


    @staticmethod
    def author_in_authors(author, authors):
        for a in authors:
            if author in a:
                return True
        return False

    @staticmethod
    def song_title_acceptability(song_title: str, video_title: str) -> float:
        splitted = song_title.split()
        splitted = list( filter( lambda s: len(s) > 2, splitted ) )
        if not splitted:
            return 1.0
        count = 0
        for s in splitted:
            if s in video_title:
                count+=1
        return float(count)/float( len(splitted) )

    @staticmethod
    def is_valid(res: dict, song: Song, privileged_channels: List[str],invalid_ids: List[str]):
        title_name = res["title"].upper()
        id = res["id"]
        if invalid_ids is not None and id in invalid_ids:
            return False
        if YoutubeSongDownloader.song_title_acceptability(song.get_name_without_brackets().upper(), title_name) < SONG_TITLE_ACCEPTABILITY:
            return False
        if "COVER" in title_name:
            return False
        if "VOCAL" in title_name:
            return False
        return True

    @staticmethod
    def get_youtube_link_from_search(song: Song, videosearch: CustomSearch, invalid_ids: List[str] = None) -> str:
        privileged_channels = ["Vevo"] + list(map( lambda n: n.replace(" ","") ,song.get_artists()))
        current_result = videosearch.result()['result']
        attempts = 20
        has_next = True
        while has_next and attempts>0:
            attempts -= 1
            for res in current_result:
                if YoutubeSongDownloader.is_valid( res, song, privileged_channels, invalid_ids ):
                    return res
            has_next = videosearch.next()
            if has_next:
                current_result = videosearch.result()['result']
        return None

    def download_link_audio(self, link: str, song: Song):
        youtube_obj = YouTube(link)
        audio = youtube_obj.streams.get_audio_only()
        destination = os.path.join(self.get_destination_dir(), song.get_expected_filename())
        out_file = audio.download(output_path=destination)
        LOGGER.info("File downloaded in: '{}'".format(out_file))
        info_file = os.path.join(destination, "info.json")
        with open(info_file, "w") as f:
            json.dump({
                "bitrate": audio.abr
            }, f)

    def download_from_queue(self, queue):
        is_first = True
        next_song = None
        while next_song is not None or is_first:
            is_first = False
            next_song: Song = self.get_next_song(queue)
            if next_song is None:
                continue
            LOGGER.info("Working on: '{}'".format(next_song.get_full_name()))
            download_completed = False
            invalid_ids = list()
            attempts = 5
            while not download_completed and attempts>0:
                attempts -= 1
                search_name = next_song.get_full_name()
                try:
                    best_result = None
                    videosSearch = CustomSearch(search_name, VideoSortOrder.viewCount, limit=10)
                    best_result = YoutubeSongDownloader.get_youtube_link_from_search(next_song, videosSearch, invalid_ids)
                    if best_result is None:
                        LOGGER.warning("Unable to find a valid video for song: '{}'".format(next_song.get_full_name()))
                        continue
                    link = best_result['link']
                    self.download_link_audio(link, next_song)
                    download_completed = True
                except Exception as exc:
                    current_id = best_result.get("id") if best_result is not None else None
                    if current_id is not None:
                        invalid_ids.append( current_id )
                    LOGGER.warning("Download failed due to:'{}'".format(str(exc)))



