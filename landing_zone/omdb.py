import os
import requests
import pandas as pd
from dotenv import dotenv_values
import json
import time
from typing import List, Dict, Optional, Set

TMDB_DIR = "landing_zone/tmdb"
OMDB_OUTPUT_DIR = "landing_zone/omdb"
OMDB_DATA_CSV = os.path.join(OMDB_OUTPUT_DIR, "movie_details.csv")
TOP_N_COUNT = 1000


def load_json(path: str) -> dict:
    """Safely loads a JSON file."""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(f"[Warning] Could not decode JSON from {path}. Skipping.")
            return {}

def get_top_movies_with_imdb_id(tmdb_dir: str, top_n: int) -> pd.DataFrame:
    print(f"Scanning {tmdb_dir} to find top {top_n} movies with IMDb IDs...")
    all_movies = []
    
    movie_ids = set()
    for filename in os.listdir(tmdb_dir):
        if "_info.json" in filename:
            movie_ids.add(filename.split('_')[0])

    for movie_id in movie_ids:
        info_path = os.path.join(tmdb_dir, f"{movie_id}_info.json")
        movie_data = load_json(info_path)
        
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

def fetch_omdb_data(imdb_id: str, api_key: str) -> Optional[Dict]:
    if not imdb_id or not imdb_id.startswith("tt"):
        print(f"  [Skipped] Invalid IMDb ID format: {imdb_id}")
        return None

    url = "http://www.omdbapi.com/"
    params = {
        "i": imdb_id,
        "apikey": api_key,
        "plot": "full"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("Response") == "True":
            return data
        else:
            print(f"  [Failed] OMDb API error for {imdb_id}: {data.get('Error', 'Unknown error')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"  [Failed] Network error for {imdb_id}: {e}")
        return None


def main():
    os.makedirs(OMDB_OUTPUT_DIR, exist_ok=True)
    try:
        api_key = dotenv_values(".env")["OMDB_KEY"]
    except KeyError:
        print("[FATAL] OMDB_KEY not found in .env file. Please add it and try again.")
        return

    top_movies_df = get_top_movies_with_imdb_id(TMDB_DIR, TOP_N_COUNT)
    if top_movies_df.empty:
        print("No movies to process. Exiting.")
        return

    existing_imdb_ids: Set[str] = set()
    if os.path.exists(OMDB_DATA_CSV):
        print(f"Loading existing data from {OMDB_DATA_CSV} to prevent duplicates.")
        existing_df = pd.read_csv(OMDB_DATA_CSV)
        if "imdbID" in existing_df.columns:
            existing_imdb_ids = set(existing_df["imdbID"].dropna())
        print(f"Found {len(existing_imdb_ids)} movies already in the CSV.")

    new_movie_records = []
    movies_to_fetch = top_movies_df[~top_movies_df["imdb_id"].isin(existing_imdb_ids)]

    if movies_to_fetch.empty:
        print("\nAll top movies are already fetched. Nothing to do.")
        return

    print(f"\nStarting to fetch data for {len(movies_to_fetch)} new movies...")
    for index, movie in movies_to_fetch.iterrows():
        title, imdb_id = movie["title"], movie["imdb_id"]
        print(f"[{index + 1}/{len(top_movies_df)}] Fetching: {title} ({imdb_id})")

        omdb_data = fetch_omdb_data(imdb_id, api_key)

        if omdb_data:
            ratings = omdb_data.get("Ratings", [])
            omdb_data["Ratings_flat"] = "; ".join([f"{r['Source']}: {r['Value']}" for r in ratings])
            del omdb_data["Ratings"]
            new_movie_records.append(omdb_data)

        time.sleep(0.1)

    if new_movie_records:
        new_df = pd.DataFrame(new_movie_records)

        write_header = not os.path.exists(OMDB_DATA_CSV)
        new_df.to_csv(OMDB_DATA_CSV, mode='a', header=write_header, index=False)
        
        print(f"\n✅ Success! Appended data for {len(new_movie_records)} new movies to {OMDB_DATA_CSV}")
    else:
        print("\nNo new movie data was successfully fetched.")

if __name__ == "__main__":
    main()