from typing import List


def remove_chars(s: str, chars: List[str]) -> str:
    title = s
    for c in chars:
        try:
            index_of = title.index(c)
            title = title[:index_of].strip()
        except ValueError:
            continue
    return title


class Song(object):

    @staticmethod
    def from_dict_data(dict_data: dict):
        artists: List[str] = list()
        artists_data = dict_data["artists"]
        for art in artists_data:
            artists.append(art["name"])
        return Song(name=dict_data["name"], artists=artists, link=dict_data["link"])

    def get_name_without_brackets(self):
        chars = ["(","-"]
        return remove_chars(self.name, chars)


    def __init__(self, name: str, artists: List[str], link: str):
        self.name: str = name
        self.artists: List[str] = artists
        self.link: str = link

    def get_name(self):
        return self.name

    def __str__(self):
        return self.name

    def get_expected_filename(self, extension: str = None):
        artists = "_".join(self.artists).replace(" ","_")
        real_name = self.name.replace(" ","_")
        name = "{}_{}".format(artists, real_name)
        name = name+"."+extension if extension is not None else name
        return name.format(artists, real_name).replace("/","")

    def get_artists(self) -> List[str]:
        return self.artists

    def get_link(self) -> str :
        return self.link

    def get_full_name(self) -> str:
        artist = ", ".join(self.artists)
        return "{} - {}".format(artist, self.name)
