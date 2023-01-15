# TODO:
# Nice display of data
# terminal interaction
# last.fm integration
# overall update to code and git repo

import urllib.request
import re
import json
import os
from datetime import date
import yaml
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


class Releases:

    def __init__(self, no_cache=False, no_latest_release=False):
        '''
        Initialise the session with signed keys

        Parameters
        ----------
        no_cache : bool
            if no artist cache exists this will create one
        no_latest_release : bool
            if no latest release cache exists one will be created
        '''
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

        with open("../api_credentials.yaml") as file:  # Authencation file location with signed keys
            auth = yaml.load(file, Loader=yaml.FullLoader)
        file.close()
        self.auth = auth
        self.spotify = Spotify(self.auth)
        self.lastfm = LastFm(self.auth)


    def add_artist_manually(self):
        identifier = ''
        while identifier != 'q':
            identifier = input("Enter manual ID to add: ")
            if identifier == 'q':
                break
            artist_info = self.spotify.spotify.artist(identifier)
            print()
            print("Found {}".format(artist_info['name']))
            print(artist_info['genres'])
            print(artist_info['followers']['total'])
            confirmation = input('Confirm (Y)es, (n)o: ')
            confirmation = 'y' if confirmation == '' or confirmation[0].lower() == 'y'  else 'n'
            if confirmation == 'y':
                self.add_new_artist(artist_info['name'], artist_info)
            print("-"*30)


    def add_new_artist(self, artist, artist_info):

        if artist not in self.cache.keys():
            print("Adding Artist:", artist_info['name'], artist_info['genres'])
            self.cache[artist] = {}
            self.cache[artist]['id'] = artist_info['id']
            self.cache[artist]['genre'] = artist_info['genres']
            self.cache[artist]['followers'] = artist_info['followers']['total']
            url = artist_info['images'][1]['url']  # 320x320
            self.cache[artist]['image'] = url
            self.cache[artist]['latest_single'] = {'name': '', 'date': '', 'image': ''}
            self.cache[artist]['latest_album'] = {'name': '', 'date': '', 'image': ''}
            self.get_artist_image(url, artist)
            self.save_cache()

    def add_recent_lastfm_artists(self, limit=100, period='7day', page=1):

        self.lastfm.set_recent_artists(self.cache, limit, period, page)
        recent_artists = self.lastfm.artist_dict
        for artist in recent_artists:
            if artist.lower() not in [x.lower() for x in self.cache.keys()]:
                # print(artist, recent_artists[artist])
                #
                found_results = []
                for genre in recent_artists[artist]:
                    found_results = self.spotify.find_artist(artist, genre)
                    if found_results != []:
                        break
                #HACK
                if len(found_results) != 1:
                    artist_search = self.spotify.find_artist(artist)
                    if len(artist_search) > 1:
                        found_results = self.spotify.sort_artist_results(artist,artist_search)
                    else:
                        found_results = []
                elif len(found_results) == 0:
                    print('Unable to find:', artist)

                if len(found_results) == 1:
                    found_details = found_results[0]
                    self.add_new_artist(found_details['name'], found_details)

    def reconcile_artists(self):
        cached_artists = [x for x in self.cache.keys()]
        followed_artist = os.listdir('following/')
        for artist in cached_artists:
            if artist+'.jpg' not in followed_artist:
                print(artist, 'not found')
                self.unfollow_artist(artist)
                print("-"*30)


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
        Any updates will be added to a new releases log to be displayed
        """
        print("-- Searching for latest releases --")
        if artist =='all':
            for artist in self.cache:
                self.latest_release_style(artist)
        else:
            self.latest_release_style(artist)

        self.save_cache()

    def latest_release_style(self, artist):
        single = self.spotify.get_artist_album(self.cache[artist], 'single')
        self.get_album_release_details(artist, single, 'single')

        album = self.spotify.get_artist_album(self.cache[artist], 'album')
        self.get_album_release_details(artist, album, 'album')


    def get_album_release_details(self, artist, release, style):
            if release != []:
                name = release['name'].lower()
                date = release['release_date']
                image = release['images'][1]['url'] # 320x320
                name = name.replace('/', '_')
                if style == 'single':
                    key = 'latest_single'
                else:
                    key = 'latest_album'
                current_release = self.cache[artist][key]['name']
                if name != current_release:
                    # Update the current cache with latest release
                    self.update_cache_release(name, date, image, artist, key)
                    if current_release != '':
                        print("New {} Found For ** {} **".format(style, artist))
                        self.update_latest_release(name, date, image, artist)
                    else:
                        pass
                else:
                    pass
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


    def get_image(self, url, artist, name, date):
        # img_data = requests.get(url).content
        # with open('releases/{}_{}_{}.jpg'.format(date, artist, name), 'wb') as handler:
            # handler.write(img_data)
        string = "releases/{}_{}_{}.jpg".format(date, artist, name)
        out = urllib.request.urlretrieve(url, string)


    def generate_artists_folder(self):
        for artist in self.cache:
            artist_details = self.spotify.spotify.artist(self.cache[artist]['id'])
            url = artist_details['images'][1]['url']
            self.cache[artist]['image'] = url
            self.get_artist_image(url, artist)


    def get_artist_image(self, url, artist):
        # img_data = requests.get(url).content
        # with open('releases/{}_{}_{}.jpg'.format(date, artist, name), 'wb') as handler:
            # handler.write(img_data)
        string = "following/{}.jpg".format(artist)
        out = urllib.request.urlretrieve(url, string)
 


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

class Spotify:

    def __init__(self, auth):

        client_id=auth['SPOTIPY_CLIENT_ID']
        client_secret=auth['SPOTIPY_CLIENT_SECRET']
        self.spotify = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
        )

    def find_artist(self, name, genere=''):
        if genere == '':
            results = self.spotify.search(q='artist:' + name, type='artist', limit=10)
        else:
            results = self.spotify.search(q='artist:' + name + ' genre:'+ genere, type='artist', limit=10)
        artist_results = results['artists']['items']
        return artist_results

    def sort_artist_results(self, artist, items):
        print("{} - please select".format(artist))
        if len(items) == 1:
            return items[0]
        else:
            item = items[0]
            print('*', 1, item['name'], '- ID:',item['id'],'', 'Genres:',item['genres'],'', 'Followers:','',item['followers']['total'])
            count = 2
            for item in items[1:]:
                print(' ', count, item['name'], '- ID:',item['id'],'', 'Genres:',item['genres'],'', 'Followers:','',item['followers']['total'])
                count += 1
            while True:
                result = input("Which is the correct match?, (m)anual, (q)uit, (s)kip:   ")
                if result == 'q':
                    return []
                elif result == '' or result=='\r':
                    return [items[0]]
                elif result == 'm':
                    manual_id = input("Enter Manual ID: ")
                    item = [self.spotify.artist(manual_id)] #TODO Confirm this returns as a list
                    return item
                elif result == 's':
                    return []
                elif result in ['1','2','3','4','5','6','7','8','9','10']:
                    return [items[int(result) - 1]]
                else:
                    print("Not a valid response")

    def get_artist_album(self, artist, style):
        latest_album = self.spotify.artist_albums(artist['id'], album_type=style, limit=1)
        if latest_album['items'] != []:
            return latest_album['items'][0]
        else:
            return []



class LastFm:

    def __init__(self, auth):
        self.api_key_lastfm = auth['Lastfm_API_key']
        self.user_id_lastfm = auth['Lastfm_Registered_to']
        self.secret_lastfm = auth['Lastfm_Shared_secret']
        self.base_lastfm =  'http://ws.audioscrobbler.com/2.0/?'

    def get_topartists(self, period='7day', limit=200, page=1):
        api_artists = requests.get(
            self.base_lastfm+'method=user.getTopArtists&api_key={}&user={}&format=json&limit={}&period={}&page={}'.format(
                self.api_key_lastfm, self.user_id_lastfm, limit, period, page
            )
        ).json()
        artists = []
        for ii in api_artists['topartists']['artist']:
            artists.append(ii['name'])
        self.recent_artists = list(set(artists))

    def strip_artist(self, artist):
        multiple_artists = [x.lstrip().rstrip() for x in re.split("[:;]", artist)]
        multiple_artists = [x.split('ft')[0].split('feat')[0].split('FEAT')[0].split('Ft')[0].split('FT')[0].split('Feat')[0].lstrip().rstrip() for x in multiple_artists]  #HACK
        return multiple_artists

    def top_tags(self, artist):
        lastfm_tags = requests.get(self.base_lastfm+'method=artist.gettoptags&api_key={}&artist={}&format=json'.format(self.api_key_lastfm, artist)).json()
        tags = []
        for ii in lastfm_tags['toptags']['tag'][:3]:
            tags.append(ii['name'])
        return tags

    def set_recent_artists(self, cache={}, limit=100, period='7day', page=1):
        self.get_topartists(limit=limit, period=period, page=page)
        self.artist_dict = {}
        for artist in self.recent_artists:
            if artist.lower() not in [x.lower() for x in cache.keys()]:
                try:
                    for split_artist in self.strip_artist(artist):
                        print("Found Artist:", split_artist)
                        self.artist_dict[split_artist] = self.top_tags(split_artist)
                except KeyError:
                    print("Error with {} - Skipping".format(split_artist))
                    continue

# Control Block >>>
release = Releases()
spotify = Spotify(release.auth)
lastfm = LastFm(release.auth)
# Control Block <<<
#
# lastfm.set_recent_artists(5)

# release.generate_artists_folder()

# out = spotify.spotify.artist('2p1fiYHYiXz9qi0JJyxBzN')
# for heading in out:
    # print(heading, out[heading])
# release.add_artist_manually()

# release.reconcile_artists()
# release.add_recent_lastfm_artists(limit=250, period='overall', page=1)
# release.reset_releases()
# print(lastfm.top_tags('Travi$ Scott'))
# results = spotify.find_artist('Travi$ Scott')
# spotify.sort_artist_results(results)
# print(release.get_artist('Nav'))
# print(release.get_artist('LD'))
# release.get_latest_release('all')



#TODO
# Error handeling
# would be nice to not add selected artists to database
#   - return staging list and allow editing from there including an ignore list...?
# general clean up
# ability to enter manual mode where ids can be pasted to be added
# artist following folder - deletion will remove artist - will only be able to be acticvated when all images are propgated
