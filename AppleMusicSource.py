import json
import re

import requests

# Songs and albums come from Apple's public iTunes lookup API (no key needed).
# Playlists aren't exposed there, so they're read from the JSON the public
# playlist page embeds for its track list.
LOOKUP_URL = 'https://itunes.apple.com/lookup'
_SERVER_DATA = re.compile(r'<script type="application/json" id="serialized-server-data">(.*?)</script>', re.S)


def _song(title, artist, url=None):
    return {'title': title, 'search': f'{artist} {title}', 'url': url}


def _lookup(item_id, country, **params):
    res = requests.get(LOOKUP_URL, params={'id': item_id, 'country': country, **params}, timeout=10)
    res.raise_for_status()
    return res.json()['results']


def getAppleTrack(track_id, country='us'):
    results = [r for r in _lookup(track_id, country) if r.get('wrapperType') == 'track']
    if not results:
        raise ValueError(f'Apple Music track {track_id} not found')
    track = results[0]
    return _song(track['trackName'], track['artistName'], track.get('trackViewUrl'))


def getAppleAlbum(album_id, country='us'):
    tracks = [r for r in _lookup(album_id, country, entity='song', limit=200)
              if r.get('wrapperType') == 'track']
    if not tracks:
        raise ValueError(f'Apple Music album {album_id} not found')
    tracks.sort(key=lambda r: (r.get('discNumber', 1), r.get('trackNumber', 0)))
    return [_song(r['trackName'], r['artistName'], r.get('trackViewUrl')) for r in tracks]


def getApplePlaylist(url):
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
    res.raise_for_status()
    match = _SERVER_DATA.search(res.text)
    if not match:
        raise ValueError('Apple Music playlist page has no track data')
    data = json.loads(match.group(1))

    songs = []
    for page in data.get('data', []):
        for section in page.get('data', {}).get('sections', []):
            if section.get('itemKind') != 'trackLockup':
                continue
            for item in section.get('items', []):
                if isinstance(item.get('title'), str) and item.get('artistName'):
                    songs.append(_song(item['title'], item['artistName']))
    if not songs:
        raise ValueError('Apple Music playlist is empty or private')
    return songs
