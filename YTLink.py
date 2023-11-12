import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

load_dotenv('.env')
SpotifyClient = os.environ.get('SPOTIFY_CLIENT')
SpotifySecret = os.environ.get('SPOTIFY_SECRET')

SpotiApi = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SpotifyClient, client_secret=SpotifySecret))

## Function to process links
def YTid(link):
    original=link 
    if link.startswith('https://', 0, 8):
        link = link[8:]

    if link.startswith('www.', 0, 5):
        link = link[4:]


    if link.startswith('youtube.com', 0, 11):
        
        if link[12:20] == 'playlist':
            playlist = {'url': original}
            return {'mediaSource': 'youtube', 'type': 'playlist', 'url': original, 'entries':[playlist]}
        
        elif link[12:18] == 'shorts':
            playlist = {'url': original}
            return {'mediaSource': 'youtube', 'type': 'short', 'url': original, 'entries':[playlist]}

        else:
            id = link[20:31]

            if link[31:36] == '&list':
                playlist = {'url': original}
                return {'mediaSource': 'youtube', 'type': 'playlist', 'url': original, 'entries': [playlist]}

            else:
                song = {'url': 'https://www.youtube.com/watch?v=' + id}
                return {'mediaSource': 'youtube', 'type': 'song', 'url': original, 'entries': [song]}


    elif link.startswith('youtu.be', 0, 8):
        id = link[9:20]
        song = {'url': 'https://www.youtube.com/watch?v=' + id}
        return {'mediaSource': 'youtube', 'type': 'song', 'url': original, 'entries': [song]}

    #If the link is from spotify, will check if the link is a track or a playlist
    # in each case, it will obtain the data from the spotify api
    elif link.startswith('open.spotify.com', 0, 20):
        link =  link[17:]
        if link.startswith('track', 0, 10):
            song = SpotiApi.track(original)
            song = {'title': song['name'], 'search': song['artists'][0]['name'] + ' ' + song['name'], 'url': original}
            return {'mediaSource': 'spotify', 'type': 'song', 'url': 'original', 'entries': [song]}
        
        
        elif link.startswith('playlist', 0, 10):
            playlist = []
            tracks = SpotiApi.playlist(original)
            for track in tracks['tracks']['items']:
                playlist.append({'title': track['track']['name'], 'search': track['track']['artists'][0]['name'] + ' ' + track['track']['name']})
            
            return {'mediaSource': 'spotify', 'type': 'playlist', 'url': original, 'entries': playlist}

    #if the input isn't a link, it is considered a search instead of a link
    else:

        query = {'search' : original}
        return {'mediaSource': 'youtube', 'type': 'search', 'entries': [query]}

    










