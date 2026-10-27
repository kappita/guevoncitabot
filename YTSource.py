import os

import requests
import yt_dlp

POT_PROVIDER_URL = os.getenv('YTDL_POT_PROVIDER_URL', '')
PLAYER_CLIENT = os.getenv('YTDL_PLAYER_CLIENT', 'default,web_safari')
COOKIEFILE = os.getenv('YTDL_COOKIEFILE', '')

YDL_OPTIONS = {'extract_flat': 'in_playlist', 'format': "bestaudio", 'playlistend': '-1', 'default_search': 'ytsearch1:'}


def _options(extract_flat):
    options = {**YDL_OPTIONS, 'extract_flat': extract_flat}

    extractor_args = {}
    if PLAYER_CLIENT.strip():
        extractor_args['youtube'] = {'player_client': PLAYER_CLIENT.split(',')}
    if POT_PROVIDER_URL.strip():
        extractor_args['youtubepot-bgutilhttp'] = {'base_url': [POT_PROVIDER_URL]}
    if extractor_args:
        options['extractor_args'] = extractor_args

    if COOKIEFILE and os.path.isfile(COOKIEFILE):
        options['cookiefile'] = COOKIEFILE

    return options


def describe():
    if COOKIEFILE and os.path.isfile(COOKIEFILE):
        with open(COOKIEFILE) as f:
            count = sum(1 for line in f if line.strip() and not line.startswith('#'))
        cookies = f'{COOKIEFILE} ({count} cookies)'
    else:
        cookies = 'none'
    return (f'player_client={PLAYER_CLIENT or "yt-dlp default"}, '
            f'pot_provider={POT_PROVIDER_URL or "none"}, cookies={cookies}')


# yt-dlp prefers vi_webp/*.webp thumbnails, which Discord embeds don't reliably
# render, so use the plain JPEG variants. maxresdefault doesn't exist for every
# video; hqdefault always does.
def _thumbnail(video_id):
    maxres = f'https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg'
    try:
        if requests.head(maxres, timeout=3).status_code == 200:
            return maxres
    except requests.RequestException:
        pass
    return f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg'


# Downloads the song data and returns it
def getSongSource(link: str) -> dict:
    with yt_dlp.YoutubeDL(_options(False)) as ydl:
        info = ydl.extract_info(link, download=False)
        if '_type' in info:
            info = info['entries'][0]
        return {'extracted': True, 'source': info['url'], 'id': info['id'],
                'thumbnail': _thumbnail(info['id']),
                'webpage_url': info.get('webpage_url') or 'https://www.youtube.com/watch?v=' + info['id'],
                'title': info['title']}


# Gets the playlist data, exactly, the title and url of every song.
def getPlaylistSource(link: str) -> list:
    with yt_dlp.YoutubeDL(_options('in_playlist')) as ydl:
        info = ydl.extract_info(link, download=False)
        return [{'extracted': False, 'title': song['title'], 'search': song['url']}
                for song in info['entries']]
