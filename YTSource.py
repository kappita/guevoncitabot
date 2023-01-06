import yt_dlp

YDL_OPTIONS = {'extract_flat': 'in_playlist', 'format':"bestaudio", 'playlistend':'-1', 'default_search': 'ytsearch1:'}

# Downloads the song data and returns it
def getSongSource(link: str) -> dict:
    YDL_OPTIONS['extract_flat'] = 'false'
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(link, download=False)
        if '_type' in info:
            info = info['entries'][0]
        source = {'extracted':True, 'source': info['url'], 'id':info['id'], 'thumbnail': info['thumbnail'], 'title':info['title']}
    return source

# Gets the playlist data, exactly, the title and url of every song.
def getPlaylistSource(link: str) -> list:
    YDL_OPTIONS['extract_flat'] = 'in_playlist'
    sources = []
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(link, download=False)
        for song in info['entries']:
            source = {'extracted':False, 'title': song['title'], 'search': song['url']}
            sources.append(source)
    return sources

    
