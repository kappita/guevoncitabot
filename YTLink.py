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


# Every playlist ID YouTube generates by itself (Mixes, radios, "My Mix",
# YouTube Music radio/curated lists) starts with "RD". User-made playlists
# use other prefixes (PL, OLAK5uy_ albums, UU uploads, ...).
def _is_auto_playlist(list_id, query):
    return list_id.startswith('RD') or 'start_radio' in query


# Radio IDs are usually the seed video's ID with a prefix, e.g. RD<id> or RDAMVM<id>.
def _radio_seed(list_id):
    for prefix in ('RDAMVM', 'RDAO', 'RD'):
        rest = list_id[len(prefix):]
        if list_id.startswith(prefix) and len(rest) == 11:
            return rest
    return None


def _song(original, vid):
    return {'mediaSource': 'youtube', 'type': 'song', 'url': original,
            'entries': [{'url': 'https://www.youtube.com/watch?v=' + vid}]}


def _youtube(original, parsed, query, vid=None):
    path = parsed.path
    vid = vid or query.get('v', [None])[0]
    list_id = query.get('list', [''])[0]

    if list_id and _is_auto_playlist(list_id, query):
        vid = vid or _radio_seed(list_id)
        if vid:
            return _song(original, vid)
        raise ValueError('auto-generated YouTube playlist without a video: ' + original)

    if list_id:
        return {'mediaSource': 'youtube', 'type': 'playlist', 'url': original,
                'entries': [{'url': 'https://www.youtube.com/playlist?list=' + list_id}]}
    if path.startswith('/shorts/'):
        return {'mediaSource': 'youtube', 'type': 'short', 'url': original,
                'entries': [{'url': original}]}
    if vid:
        return _song(original, vid)
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
        vid = parsed.path.strip('/') if host == 'youtu.be' else None
        result = _youtube(original, parsed, query, vid)
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
    assert YTid('https://youtu.be/a?list=PL1')['type'] == 'playlist'
    assert YTid('https://www.youtube.com/watch?v=a&list=OLAK5uy_x')['type'] == 'playlist'
    mix = YTid('https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=RDdQw4w9WgXcQ&start_radio=1')
    assert mix['type'] == 'song'
    assert mix['entries'][0]['url'] == 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    assert YTid('https://youtu.be/dQw4w9WgXcQ?list=RDdQw4w9WgXcQ')['type'] == 'song'
    assert YTid('https://www.youtube.com/watch?v=abc&list=RDMM')['type'] == 'song'
    assert YTid('https://music.youtube.com/watch?v=abc&list=RDAMVMabc')['type'] == 'song'
    seed = YTid('https://www.youtube.com/playlist?list=RDdQw4w9WgXcQ')
    assert seed['entries'][0]['url'] == 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    try:
        YTid('https://www.youtube.com/playlist?list=RDCLAK5uy_abcdefghijklmnop')
        assert False, 'radio without a seed video should be rejected'
    except ValueError:
        pass
    assert YTid('https://music.youtube.com/watch?v=abc123')['type'] == 'song'
    assert YTid('daft punk one more time')['type'] == 'search'
    assert YTid('daft punk one more time')['mediaSource'] == 'youtube'
    print('YTLink demo OK')


if __name__ == '__main__':
    _demo()
