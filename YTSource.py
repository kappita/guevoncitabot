import os

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


# Downloads the song data and returns it
def getSongSource(link: str) -> dict:
    with yt_dlp.YoutubeDL(_options(False)) as ydl:
        info = ydl.extract_info(link, download=False)
        if '_type' in info:
            info = info['entries'][0]
        return {'extracted': True, 'source': info['url'], 'id': info['id'],
                'thumbnail': info['thumbnail'], 'title': info['title']}


# Gets the playlist data, exactly, the title and url of every song.
def getPlaylistSource(link: str) -> list:
    with yt_dlp.YoutubeDL(_options('in_playlist')) as ydl:
        info = ydl.extract_info(link, download=False)
        return [{'extracted': False, 'title': song['title'], 'search': song['url']}
                for song in info['entries']]
