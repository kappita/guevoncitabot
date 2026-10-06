import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv('.env')
TidalClient = os.getenv('TIDAL_CLIENT')
TidalSecret = os.getenv('TIDAL_SECRET')
tidalCredentials = f"{TidalClient}:{TidalSecret}"
print(tidalCredentials)
b64_TidalCredentials = base64.b64encode(tidalCredentials.encode()).decode()
print(b64_TidalCredentials)

# Prepare headers and data
headers = {
    "Authorization": f"Basic {b64_TidalCredentials}",
    "Content-Type": "application/x-www-form-urlencoded"
}
data = {
    "grant_type": "client_credentials"
}

response = requests.post("https://auth.tidal.com/v1/oauth2/token", headers=headers, data=data)
if response.status_code == 200:
    token_data = response.json()
    tidal_token = token_data['access_token']
    req_header = {
        "Authorization": f"Bearer {tidal_token}",
        "accept": "application/vnd.api+json"
    }
    print("Access token:", tidal_token)
else:
    print("OTDO SALIO MAL HERMANO WTF", response.status_code)

def getTidalTrack(songId: str):
    req_url = f"https://openapi.tidal.com/v2/tracks/{songId}?countryCode=CL&include=artists"
    res = requests.get(req_url, headers=req_header)
    res = res.json()
    title = res['data']['attributes']['title']
    artist = res['included'][0]['attributes']['name']
    url = res['data']['attributes']['externalLinks'][0]['href']
    return {'title': title, 'search': artist + ' ' + title, 'url': url}

def getTidalPlaylist(playlistId: str):
    req_url = f"https://openapi.tidal.com/v2/playlists/{playlistId}?countryCode=CL&include=items"
    res = requests.get(req_url, headers=req_header)
    res = res.json()
    playlist = []
    for song in res['included']:
        title = song['attributes']['title']
        url = song['attributes']['externalLinks'][0]['href']
        playlist.append({'title': title, 'search': title + 'hq', 'url': url})

    return playlist

    