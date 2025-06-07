import os
import pandas as pd
from dotenv import dotenv_values
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
import json



SPOTIFY_CSV = "./landing_zone/spotify/spotify.csv"
TMDB_DIR = "./landing_zone/tmdb"
MUSIC_CACHE = "./landing_zone/spotify/soundtrack_cache.json"

def get_spotify_client():
    config = dotenv_values(".env")
    client_id = config["SPOTIFY_CLIENT_ID"]
    client_secret = config["SPOTIFY_CLIENT_SECRET"]

    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return Spotify(auth_manager=auth_manager)


def search_album_for_movie(movie_title: str, release_year: str, sp: Spotify):
    try:
        results = sp.search(q=f'{movie_title} {release_year} soundtrack', type='album', limit=1)
    except Exception as e:
        print(f"Error while searching for: {movie_title} ({release_year})")
        return None
    items = results.get('albums', {}).get('items', [])
    if not items:
        print(f"No album found for '{movie_title}'")
        return None
    return items[0]  # First result


def collect_album_tracks(album_id: str, sp: Spotify):
    # Get album-level metadata
    album_info = sp.album(album_id)
    album_genres = album_info.get("genres", [])
    album_genres_str = ", ".join(album_genres)

    tracks = album_info.get("tracks", {}).get("items", [])
    track_data = []

    for item in tracks:
        track_id = item['id']
        artist_id = item['artists'][0]['id']

        # Get track & artist metadata
        track_detail = sp.track(track_id)
        artist = sp.artist(artist_id)

        track_data.append({
            "track_name": item['name'],
            "track_id": track_id,
            "track_duration_ms": item['duration_ms'],
            "track_popularity": track_detail.get('popularity'),
            "track_number": item['track_number'],

            "artist_name": artist['name'],
            "artist_id": artist_id,
            "artist_genres": ", ".join(artist.get('genres', [])),
            "artist_popularity": artist.get('popularity'),

            # Album genres might be empty lots of times, so recommended to use
            # artist genres
            "album_genres": album_genres_str
        })

    return track_data



def save_soundtrack(movie_id: int, movie_title: str, album: dict, tracks: list, filename: str):
    album_name = album["name"]
    album_release = album.get("release_date", "")
    album_total_tracks = album.get("total_tracks", 0)
    album_url = album["external_urls"]["spotify"]
    album_img = album["images"][0]["url"] if album["images"] else None

    df = pd.DataFrame(tracks)
    df.insert(0, "movie_id", movie_id)
    df.insert(1, "movie_title", movie_title)
    df.insert(2, "album_name", album_name)
    df.insert(3, "album_release", album_release)
    df.insert(4, "album_url", album_url)
    df.insert(5, "album_img", album_img)
    df.insert(6, "album_total_tracks", album_total_tracks)

    if os.path.exists(filename):
        existing = pd.read_csv(filename)
        df = pd.concat([existing, df], ignore_index=True)

    df.to_csv(filename, index=False)
    print(f"Saved soundtrack for '{movie_title}'")


def main_iter(num: int):
    # Load movie JSON
    
    info_path = os.path.join(TMDB_DIR, f"{num}_info.json")
    if not os.path.exists(info_path):
        print(f"No info file for movie {num}")
        return

    with open(info_path, "r", encoding="utf-8") as f:
        movie = json.load(f)

    title = movie.get("title", "Unknown")
    release_year = movie.get("release_date", "Unknown").split("-")[0]
    movie_id = movie.get("id")

    if not os.path.exists(MUSIC_CACHE):
        cache = {"cached_movies":[]}
        with open(MUSIC_CACHE, "w") as f:
            json.dump(cache, f)
    else:
        with open(MUSIC_CACHE, "r") as f:
            cache = json.load(f)
    

    if movie_id in cache["cached_movies"]:
        return 0

    sp = get_spotify_client()

    album = search_album_for_movie(title, release_year, sp)
    if album:
        tracks = collect_album_tracks(album["id"], sp)
        if tracks:
            save_soundtrack(movie_id, title, album, tracks, SPOTIFY_CSV)

    cache["cached_movies"].append(movie_id)
    with open(MUSIC_CACHE, "w") as f:
        json.dump(cache, f)

def main():
    json_nums = list(set(map(lambda x: int(x.split("_")[0]), os.listdir(TMDB_DIR))))
    for num in json_nums:

        main_iter(num)


if __name__ == "__main__":
    main()
