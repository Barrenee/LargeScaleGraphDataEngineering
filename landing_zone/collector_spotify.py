import os
import pandas as pd
from dotenv import dotenv_values
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
import json


SPOTIFY_CSV = "./landing_zone/spotify/spotify.csv"
TMDB_DIR = "./landing_zone/tmdb"
MUSIC_CACHE = "./landing_zone/spotify/soundtrack_cache.json"


# Spotify Collector

#   This script calls the spotify api for all of the movies 
#   already pulled with the tmdb script. The objective is to 
#   save information on the album connatining the soundtrack of the movie,
#   and all of the tracks included in said album/soundtrack


# == Utils ==
def get_spotify_client():
    """
    Loads Spotify API credentials from .env and returns a Spotify client object using client credentials.
    """
    config = dotenv_values(".env")
    client_id = config["SPOTIFY_CLIENT_ID"]
    client_secret = config["SPOTIFY_CLIENT_SECRET"]

    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return Spotify(auth_manager=auth_manager)


# == Main Functions ==
def search_album_for_movie(movie_title: str, release_year: str, sp: Spotify):
    """
    Given a movie title and release year, attempts to find a corresponding album
    on Spotify by searching with the movie name and the word 'soundtrack'.
    
    Returns the first album found, or None if no results are returned or an error occurs.
    """
    try:
        results = sp.search(q=f'{movie_title} {release_year} soundtrack', type='album', limit=1)
    except Exception as e:
        print(f"Error while searching for: {movie_title} ({release_year})")
        return None

    items = results.get('albums', {}).get('items', [])
    if not items:
        print(f"No album found for '{movie_title}'")
        return None
    return items[0]  # Return the first album result


def collect_album_tracks(album_id: str, sp: Spotify):
    """
    Given an album ID, this function retrieves all the tracks from that album
    along with detailed metadata about each track and its artist.
    
    Album genres are included, but may often be empty—artist genres are also collected.
    
    Returns a list of dictionaries, one per track.
    """
    # Get album-level metadata
    album_info = sp.album(album_id)
    album_genres = album_info.get("genres", [])
    album_genres_str = ", ".join(album_genres)

    tracks = album_info.get("tracks", {}).get("items", [])
    track_data = []

    for item in tracks:
        track_id = item['id']
        artist_id = item['artists'][0]['id']

        # Retrieve detailed info about the track and artist
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

            # Album genres (may be empty, fallback is artist genres)
            "album_genres": album_genres_str
        })

    return track_data


def save_soundtrack(movie_id: int, movie_title: str, album: dict, tracks: list, filename: str):
    """
    Receives metadata and track information for a given album related to a movie,
    and stores the data into a CSV file. If the file already exists, new data is appended.

    Includes movie and album-level metadata as well as per-track metadata.
    """
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


def main_iter(num: int, sp: Spotify):
    """
    Core logic function that retrieves the soundtrack of a movie based on its title and year.

    - Loads the movie JSON based on its TMDB ID
    - Checks if the soundtrack has already been cached
    - Searches for an album on Spotify and, if found, retrieves and stores track and artist info
    - Caches movie IDs to avoid redundant API calls
    """
    info_path = os.path.join(TMDB_DIR, f"{num}_info.json")
    if not os.path.exists(info_path):
        print(f"No info file for movie {num}")
        return

    with open(info_path, "r", encoding="utf-8") as f:
        movie = json.load(f)

    title = movie.get("title", "Unknown")
    release_year = movie.get("release_date", "Unknown").split("-")[0]
    movie_id = movie.get("id")

    # Load or create soundtrack cache
    if not os.path.exists(MUSIC_CACHE):
        cache = {"cached_movies": []}
        with open(MUSIC_CACHE, "w") as f:
            json.dump(cache, f)
    else:
        with open(MUSIC_CACHE, "r") as f:
            cache = json.load(f)

    # Skip if movie is already cached
    if movie_id in cache["cached_movies"]:
        print(">> Skipping movie, already saved")
        return 0

    # Search for album and collect track data
    album = search_album_for_movie(title, release_year, sp)
    if album:
        tracks = collect_album_tracks(album["id"], sp)
        if tracks:
            save_soundtrack(movie_id, title, album, tracks, SPOTIFY_CSV)

    # Update cache
    cache["cached_movies"].append(movie_id)
    with open(MUSIC_CACHE, "w") as f:
        json.dump(cache, f)


def get_top_movies_with_imdb_id(tmdb_dir: str, top_n: int) -> pd.DataFrame:
    print(f"Scanning {tmdb_dir} to find top {top_n} movies with IMDb IDs...")
    all_movies = []
    
    movie_ids = set()
    for filename in os.listdir(tmdb_dir):
        if "_info.json" in filename:
            movie_ids.add(filename.split('_')[0])

    for movie_id in movie_ids:
        info_path = os.path.join(tmdb_dir, f"{movie_id}_info.json")
        with open(info_path, "r") as f:
            movie_data = json.load(f)
        
        if movie_data and "imdb_id" in movie_data and movie_data["imdb_id"]:
            all_movies.append({
                "tmdb_id": movie_data.get("id"),
                "imdb_id": movie_data.get("imdb_id"),
                "title": movie_data.get("title"),
                "popularity": movie_data.get("popularity", 0)
            })

    if not all_movies:
        print("No movies with IMDb IDs found.")
        return pd.DataFrame()

    movies_df = pd.DataFrame(all_movies)
    top_movies = movies_df.drop_duplicates(subset=["imdb_id"]).nlargest(top_n, "popularity")
    
    print(f"Found {len(movies_df)} unique movies with IMDb IDs. Identified top {len(top_movies)}.")
    return top_movies



if __name__ == "__main__":
    """
    Entrypoint to run the full soundtrack collector over all existing TMDB movie files.

    For each movie found in the `landing_zone/tmdb` directory, it runs the main_iter function.
    """
    top_movies = get_top_movies_with_imdb_id
    top_movies_ids = top_movies["tmdb_id"]
    
    sp = get_spotify_client()
    for num in top_movies_ids:
        main_iter(num, sp)
    