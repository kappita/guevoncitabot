import os
from urllib.parse import urlparse, parse_qs

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

load_dotenv('.env')
SpotifyClient = os.getenv('SPOTIFY_CLIENT')
SpotifySecret = os.getenv('SPOTIFY_SECRET')

_spoti_api = None


def _spotify_client():
    global _spoti_api
    if _spoti_api is None:
        _spoti_api = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(client_id=SpotifyClient, client_secret=SpotifySecret))
    return _spoti_api


def _youtube(original, parsed, query):
    path = parsed.path
    if path.startswith('/playlist') or 'list' in query:
        return {'mediaSource': 'youtube', 'type': 'playlist', 'url': original,
                'entries': [{'url': original}]}
    if path.startswith('/shorts/'):
        return {'mediaSource': 'youtube', 'type': 'short', 'url': original,
                'entries': [{'url': original}]}
    vid = query.get('v', [None])[0]
    if vid:
        return {'mediaSource': 'youtube', 'type': 'song', 'url': original,
                'entries': [{'url': 'https://www.youtube.com/watch?v=' + vid}]}
    return None


def _spotify(original, parsed):
    parts = [p for p in parsed.path.split('/') if p]
    if parts and parts[0].startswith('intl-'):
        parts = parts[1:]
    if parts and parts[0] == 'track':
        track = _spotify_client().track(original)
        song = {'title': track['name'], 'search': track['artists'][0]['name'] + ' ' + track['name'],
                'url': original}
        return {'mediaSource': 'spotify', 'type': 'song', 'url': original, 'entries': [song]}
    if parts and parts[0] == 'playlist':
        playlist = []
        for track in _spotify_client().playlist(original)['tracks']['items']:
            playlist.append({'title': track['track']['name'],
                             'search': track['track']['artists'][0]['name'] + ' ' + track['track']['name']})
        return {'mediaSource': 'spotify', 'type': 'playlist', 'url': original, 'entries': playlist}
    return None


def _tidal(original, parsed):
    from TidalSource import getTidalTrack, getTidalPlaylist
    parts = [p for p in parsed.path.split('/') if p]
    if parts[:2] == ['browse', 'track'] and len(parts) >= 3:
        return {'mediaSource': 'tidal', 'type': 'song', 'url': original,
                'entries': [getTidalTrack(parts[2])]}
    if parts and parts[0] == 'playlist' and len(parts) >= 2:
        return {'mediaSource': 'tidal', 'type': 'playlist', 'url': original,
                'entries': getTidalPlaylist(parts[1])}
    return None


## Function to process links or search text
def YTid(link):
    original = link.strip()
    candidate = original if '://' in original else 'https://' + original
    parsed = urlparse(candidate)
    host = parsed.netloc.lower()
    if host.startswith('www.'):
        host = host[4:]
    query = parse_qs(parsed.query)

    result = None
    if host.endswith('youtube.com') or host == 'youtu.be':
        if host == 'youtu.be':
            vid = parsed.path.lstrip('/')
            result = {'mediaSource': 'youtube', 'type': 'song', 'url': original,
                      'entries': [{'url': 'https://www.youtube.com/watch?v=' + vid}]}
        else:
            result = _youtube(original, parsed, query)
    elif host.endswith('spotify.com'):
        result = _spotify(original, parsed)
    elif host.endswith('tidal.com'):
        result = _tidal(original, parsed)

    if result is not None:
        return result

    # Anything that isn't a recognised link is treated as a YouTube search.
    return {'mediaSource': 'youtube', 'type': 'search', 'url': original,
            'entries': [{'search': original}]}


def _demo():
    assert YTid('https://www.youtube.com/watch?v=abc123')['type'] == 'song'
    assert YTid('https://youtu.be/abc123')['type'] == 'song'
    assert YTid('https://www.youtube.com/shorts/xyz')['type'] == 'short'
    assert YTid('https://www.youtube.com/playlist?list=PL1')['type'] == 'playlist'
    assert YTid('https://www.youtube.com/watch?v=a&list=PL1')['type'] == 'playlist'
    assert YTid('https://music.youtube.com/watch?v=abc123')['type'] == 'song'
    assert YTid('daft punk one more time')['type'] == 'search'
    assert YTid('daft punk one more time')['mediaSource'] == 'youtube'
    print('YTLink demo OK')


if __name__ == '__main__':
    _demo()
