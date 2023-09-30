import datetime
import json
import os
import sys
from time import sleep
from typing import List
from selenium import webdriver

import requests
import logging

from selenium.webdriver.common.by import By

from commons import constants
from commons.Song import Song
from song_downloader.downloader import Downloader
from song_downloader.selenium_downloader import SeleniumSongDownloader
from song_downloader.youtube_song_downloader import YoutubeSongDownloader


FORMAT = '%(asctime)s-8s %(message)s'
logging.basicConfig(level=logging.INFO)
logging.basicConfig(format=FORMAT)
LOGGER = logging.getLogger("main")
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
file_handler = logging.FileHandler(constants.LOG_FILE)
file_handler.setFormatter(formatter)
LOGGER.addHandler(file_handler)


PLAYLIST_ID = "YOUR PLAYLIST ID"

CLIENT_ID = "YOUR CLIENT ID"
CLIENT_SECRET = "YOUR CLIENT SECRET"

SPOTIFY_PLAYLIST_ENDPOINT = "https://api.spotify.com/v1/playlists/{}"

YOUTUBE_LINK = "https://www.youtube.com"

SPOTIFY_TRACKS_IN_PLAYLIST_ENDPOINT = "https://api.spotify.com/v1/playlists/{}/tracks?limit=20"

TOKEN_REQUEST_URL = "https://accounts.spotify.com/api/token"

def get_stored_token_if_valid( path: str ) -> str:
    if not os.path.exists(path):
        return None
    with open(path) as f:
        token_dict = json.load(f)
    expiration_date = token_dict["expiration_date"]
    expires_at = datetime.datetime.fromtimestamp(expiration_date)
    if datetime.datetime.now() > expires_at:
        return None
    token = token_dict["token"]
    return token

def store_token(path: str, input_dict: dict):
    expiration_date: datetime.datetime = datetime.datetime.now() + datetime.timedelta(seconds=int(input_dict["expires_in"]))
    result = { "token": input_dict["access_token"],
               "expiration_date": expiration_date.timestamp()}
    with open(path, "w") as f:
        json.dump(result, f, indent=4)

def get_bearer_token(client_id: str, client_secret: str, store_path = "./token.json") -> str:
    current_token = get_stored_token_if_valid(path=store_path)
    if current_token is not None:
        return current_token
    headers = { "Content-Type" : "application/x-www-form-urlencoded"}
    data = "grant_type=client_credentials&client_id={}&client_secret={}".format(client_id, client_secret)
    response = requests.post(TOKEN_REQUEST_URL, headers=headers, data=data)
    if not response.status_code == 200:
        LOGGER.error("Unable to retrieve token")
        return None
    response_json = response.json()
    store_token(path=store_path, input_dict=response_json)
    return response_json["access_token"]

def get_playlist_endpoint(playlist_id: str) -> str:
    return SPOTIFY_TRACKS_IN_PLAYLIST_ENDPOINT.format(playlist_id)

def write_playlist_tracks_to_file( song_list: list, dest_path: str ):
    root = { }
    root["root"] = song_list
    with open(dest_path, "w") as f:
        json.dump(root, f, indent=4)


def get_song_name(artists: List[str], song_name: str) -> str:
    artist_names = ", ".join(artists)
    return artist_names + " : " + song_name

def load_song_list( playlist_endpoint: str, params: dict ) -> list :
    result = list()
    next_url = playlist_endpoint
    while next_url is not None:
        response = requests.get(next_url, headers=params)
        response_dict = response.json()
        next_url = response_dict.get("next")
        items = response_dict["items"]
        for item in items:
            song_data = {}
            artists = item["track"]['artists']
            song_data["artists"] = []
            for artist in artists:
                song_data["artists"].append({
                    "name": artist["name"]
                })
            name = item["track"]['name']
            song_data["name"] = name
            song_data["link"] = item["track"]["href"]
            result.append(song_data)
    return result



def download_songs(dest_dir: str, source_file:str):
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    with open(source_file) as f:
        root_file = json.load(f)
    if root_file is None:
        LOGGER.error("Unable to read file:'{}'".format(source_file))
        raise RuntimeError()
    song_list: List[Song] = list()
    for entry in root_file["root"]:
        song_list.append( Song.from_dict_data(entry) )
    downloader: Downloader = YoutubeSongDownloader(song_list=song_list, destination_dir=dest_dir)
    downloader.start_download()




def main():
    songs_destination_dir = "./with_report"
    dest_filepath = "./songs.json"
    if os.path.exists(dest_filepath):
        download_songs(dest_dir=songs_destination_dir, source_file=dest_filepath)
        return
    bearer_token = get_bearer_token(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    playlist_endpoint = get_playlist_endpoint(playlist_id=PLAYLIST_ID)
    params = {"Authorization": "Bearer {}".format(bearer_token)}
    song_list: list = load_song_list(playlist_endpoint=playlist_endpoint, params=params)
    write_playlist_tracks_to_file(song_list=song_list, dest_path="songs.json")
    download_songs(dest_dir=songs_destination_dir, source_file=dest_filepath)

if __name__ == "__main__":
    main()