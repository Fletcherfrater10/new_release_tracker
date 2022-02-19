# TODO:
# display new releases with images



from __future__ import print_function    # (at top of module)
import yaml
import urllib.request
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import sys
from pprint import pprint
import argparse
import logging
import time
import json
from datetime import date

logger = logging.getLogger('examples.artist_discography')
logging.basicConfig(level='INFO')

class Releases:

    def __init__(self, no_cache=False, no_latest_release=False):
        if no_cache:
            self.cache = {}
        else:
            file = open("artist_releases.json", "r")
            self.cache = json.load(file)
            file.close()

        if no_latest_release:
            self.latest_release = {}
        else:
            latest = open("latest_releases.json", "r")
            self.latest_release = json.load(latest)
            latest.close()

        with open("../spotify_api_credentials.yaml") as file:  # Authencation file location with signed keys
            auth = yaml.load(file, Loader=yaml.FullLoader)
        file.close()

        client_id=auth['SPOTIPY_CLIENT_ID']
        client_secret=auth['SPOTIPY_CLIENT_SECRET']
        self.spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=client_id,
                                                                        client_secret=client_secret))

    def add_id(self, reset=False):
        """
        Add id to the cache
        """
        self.problem_artists = {}
        if reset:
            for artist in self.cache:
                self.cache[artist]['id'] = -1
                self.cache[artist]['genre'] = -1
                # self.cache[artist].pop('genres')
                self.save_cache()
        for artist in self.cache:
            if self.cache[artist]['id'] == -1:
                print("=========")
                print(artist)
                artist_info = self.get_artist(artist)
                if artist_info == None:
                    print(artist, artist_info)
                    self.problem_artists[artist] = self.cache[artist]
                else:
                    print(artist, artist_info['name'], artist_info['genres'])
                    self.cache[artist]['id'] = artist_info['id']
                    self.cache[artist]['genre'] = artist_info['genres']
            else:
                pass

        print(self.cache)

    def add_new_artist(self, artist):
        """
        Add a new artist to the followed list;
        Will call a search and obtain associated artist id,
        artist and id will be added to the database
        {'artist': , 'id': ,'latest_single':{'name': ,'date': }
        ,'latest_album':{'name': ,'date': }}
        """
        if artist not in self.cache.keys():
            artist_info = self.get_artist(artist)
            if artist_info == None:
                print(artist, artist_info)
                self.problem_artists[artist] = self.cache[artist]
            else:
                print(artist, artist_info['name'], artist_info['genres'])
                self.cache[artist] = {}
                self.cache[artist]['id'] = artist_info['id']
                self.cache[artist]['genre'] = artist_info['genres']
                self.cache[artist]['followed_on'] = str(date.today())
                self.cache[artist]['latest_single'] = {'name': '', 'date': '', 'image': ''}
                self.cache[artist]['latest_album'] = {'name': '', 'date': '', 'image': ''}
            self.save_cache()
        else:
            print("Artist '{}' already followed".format(artist))

    def unfollow_artist(self, artist):
        """
        Remove artist from following list
        """
        self.cache.pop(artist)
        print(artist, " has been unfollowed")
        self.save_cache()

    def reset_releases(self, artist=False):
        if not artist:
            for a in self.cache:
                self.cache[a]['latest_single'] = {'name': '', 'date': '', 'image': ''}
                self.cache[a]['latest_album'] = {'name': '', 'date': '', 'image': ''}
        else:
            self.cache[artist]['latest_single'] = {'name': '', 'date': '', 'image': ''}
            self.cache[artist]['latest_album'] = {'name': '', 'date': '', 'image': ''}
        self.save_cache()

    def get_latest_release(self, artist):
        """
        Get latest release for followed artists if different from current cache,
        will search albums then singles,
        Any updates will be added to a 'new releases' log to be displayed
        """
        print("-- Searching for latest releases --")
        if artist =='all':
            for artist in self.cache:
                self.latest_release_type(artist)
        else:
            self.latest_release_type(artist)

        self.save_cache()

    def latest_release_type(self, artist):
        single = self.get_artist_album(self.cache[artist], 'single')
        self.get_album_release_details(artist, single, 'single')

        album = self.get_artist_album(self.cache[artist], 'album')
        self.get_album_release_details(artist, album, 'album')


    def get_album_release_details(self, artist, release, type):
            if release != []:
                name = release['name'].lower()
                date = release['release_date']
                image = release['images'][0]['url']
                if type == 'single':
                    key = 'latest_single'
                else:
                    key = 'latest_album'
                current_release = self.cache[artist][key]['name']
                if name != current_release:
                    print("New Release Found For ** {} **))".format(artist))
                    # Update the current cache with latest release
                    self.update_cache_release(name, date, image, artist, key)
                    self.update_latest_release(name, date, image, artist)
                else:
                    pass
                    # print("No New Release Found For {}".format(artist))
            else:
                pass

    def update_cache_release(self, name, date, image, artist, key):
        if key not in self.cache[artist].keys():
            self.reset_releases(artist)
            self.cache[artist][key] = {'name': name, 'date':date, 'image':image}
        else:
            self.cache[artist][key] = {'name': name, 'date':date, 'image':image}
        print('cache updated')

    def update_latest_release(self, name, date, image, artist):
        self.get_image(image, artist, name, date)
        if date not in self.latest_release.keys():
            self.latest_release[date] = {}
            self.latest_release[date][name] = {'artist': artist}
        else:
            self.latest_release[date][name] = {'artist': artist}
        print('latest release recorded')


    def get_artist(self, name):
        results = self.spotify.search(q='artist:' + name, type='artist', limit=10)
        items = results['artists']['items']
        count = 1
        if len(items) == 1:
            return items[0]
        elif len(items) > 1:
            for item in items:
                print(count, item['name'], item['genres'], item['id'])
                count += 1
            result = input("Which is the correct match?, (m)anual, (q)uit, (s)kip:   ")
            if result == 'q':
                self.save_cache(True)
                exit()
            elif result == '':
                return items[0]
            elif result == 'm':
                manual_id = input("Enter Manual ID: ")
                item = self.spotify.artist(manual_id)
                return item
            elif result == 's':
                return None
            else:
                return items[int(result) - 1]
        else:
            return None


    def get_artist_album(self, artist, type):
        latest = self.spotify.artist_albums(artist['id'], album_type=type, limit=1)
        if latest['items'] != []:
            return latest['items'][0]
        else:
            return []

    def get_image(self, url, artist, name, date):
        urllib.request.urlretrieve(url, "releases/{}_{}_{}.jpg".format(date, artist, name))

    def save_cache(self, problem_artists=False):
        """
        Save dictionary of artist information
        """
        if problem_artists:
            for problem_artist in self.problem_artists:
                self.cache.pop(problem_artist)
            file = open("problem_artists.json", "w")
            json.dump(self.problem_artists, file)
            file.close()
        file = open("artist_releases.json", "w")
        json.dump(self.cache, file, sort_keys=True, indent=4)
        file.close()

        latest = open("latest_releases.json", "w")
        json.dump(self.latest_release, latest, sort_keys=True, indent=4)
        latest.close()



release = Releases(no_latest_release=True)
release.get_latest_release('all')
