import yt_dlp

YDL_OPTIONS = {'extract_flat': 'in_playlist', 'format': "bestaudio", 'playlistend': '-1', 'default_search': 'ytsearch1:'}


# Downloads the song data and returns it
def getSongSource(link: str) -> dict:
    options = {**YDL_OPTIONS, 'extract_flat': False}
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(link, download=False)
        if '_type' in info:
            info = info['entries'][0]
        return {'extracted': True, 'source': info['url'], 'id': info['id'],
                'thumbnail': info['thumbnail'], 'title': info['title']}


# Gets the playlist data, exactly, the title and url of every song.
def getPlaylistSource(link: str) -> list:
    options = {**YDL_OPTIONS, 'extract_flat': 'in_playlist'}
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(link, download=False)
        return [{'extracted': False, 'title': song['title'], 'search': song['url']}
                for song in info['entries']]
