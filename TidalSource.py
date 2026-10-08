import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv('.env')

_token = None


def _headers():
    global _token
    if _token is None:
        credentials = base64.b64encode(
            f"{os.getenv('TIDAL_CLIENT')}:{os.getenv('TIDAL_SECRET')}".encode()
        ).decode()
        response = requests.post(
            "https://auth.tidal.com/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )
        response.raise_for_status()
        _token = response.json()['access_token']
    return {"Authorization": f"Bearer {_token}", "accept": "application/vnd.api+json"}


def getTidalTrack(songId: str):
    req_url = f"https://openapi.tidal.com/v2/tracks/{songId}?countryCode=CL&include=artists"
    res = requests.get(req_url, headers=_headers()).json()
    title = res['data']['attributes']['title']
    artist = res['included'][0]['attributes']['name']
    url = res['data']['attributes']['externalLinks'][0]['href']
    return {'title': title, 'search': artist + ' ' + title, 'url': url}


def getTidalPlaylist(playlistId: str):
    req_url = f"https://openapi.tidal.com/v2/playlists/{playlistId}?countryCode=CL&include=items"
    res = requests.get(req_url, headers=_headers()).json()
    playlist = []
    for song in res['included']:
        title = song['attributes']['title']
        url = song['attributes']['externalLinks'][0]['href']
        playlist.append({'title': title, 'search': title + 'hq', 'url': url})
    return playlist
