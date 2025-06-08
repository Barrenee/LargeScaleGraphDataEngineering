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


# OMDB Movies Collector
#   This script enriches movie metadata by fetching detailed movie information from the OMDb API,
#   based on IMDb IDs sourced from locally stored TMDb data files. It scans the TMDb directory 
#   to extract top movies by popularity that have valid IMDb IDs, queries OMDb for extended details 
#   (e.g., plot, ratings), and appends the results to a CSV while avoiding duplicate entries.


def load_json(path: str) -> dict:
    """Safely loads a JSON file, returning an empty dict on failure."""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(f"[Warning] Could not decode JSON from {path}. Skipping.")
            return {}

def get_top_movies_with_imdb_id(tmdb_dir: str, top_n: int) -> pd.DataFrame:
    """
    Scans the TMDb directory for movie info JSON files, extracts IMDb IDs,
    and returns the top N by popularity.
    """
    print(f"Scanning {tmdb_dir} to find top {top_n} movies with IMDb IDs...")
    all_movies = []
    movie_ids = set()

    # Collect all unique TMDb movie IDs from filenames
    for filename in os.listdir(tmdb_dir):
        if "_info.json" in filename:
            movie_ids.add(filename.split('_')[0])

    # Load each movie's metadata and collect relevant details
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

    # Create DataFrame and filter to top N unique IMDb entries by popularity
    movies_df = pd.DataFrame(all_movies)
    top_movies = movies_df.drop_duplicates(subset=["imdb_id"]).nlargest(top_n, "popularity")

    print(f"Found {len(movies_df)} unique movies with IMDb IDs. Identified top {len(top_movies)}.")
    return top_movies

def fetch_omdb_data(imdb_id: str, api_key: str) -> Optional[Dict]:
    """
    Queries the OMDb API for movie details based on a given IMDb ID.
    Returns the data as a dictionary or None if the fetch fails.
    """
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
    """
    Main thread of the script, which is in charge of obtaining OMDB information on the 
    top movies by popularity. It does so by retrieving the already loaded movies using the 
    TMDB script, and thn calling the necessary functions so as to make api calls, order 
    and save the results into a csv
    """
    # Ensure output directory exists
    os.makedirs(OMDB_OUTPUT_DIR, exist_ok=True)

    # Load OMDb API key from .env file
    try:
        api_key = dotenv_values(".env")["OMDB_KEY"]
    except KeyError:
        print("[FATAL] OMDB_KEY not found in .env file. Please add it and try again.")
        return

    # Get top N movies that have IMDb IDs
    top_movies_df = get_top_movies_with_imdb_id(TMDB_DIR, TOP_N_COUNT)
    if top_movies_df.empty:
        print("No movies to process. Exiting.")
        return

    # Track which IMDb IDs have already been fetched to avoid duplicates
    existing_imdb_ids: Set[str] = set()
    if os.path.exists(OMDB_DATA_CSV):
        print(f"Loading existing data from {OMDB_DATA_CSV} to prevent duplicates.")
        existing_df = pd.read_csv(OMDB_DATA_CSV)
        if "imdbID" in existing_df.columns:
            existing_imdb_ids = set(existing_df["imdbID"].dropna())
        print(f"Found {len(existing_imdb_ids)} movies already in the CSV.")

    # Filter for new movies that haven’t been fetched yet
    new_movie_records = []
    movies_to_fetch = top_movies_df[~top_movies_df["imdb_id"].isin(existing_imdb_ids)]

    if movies_to_fetch.empty:
        print("\nAll top movies are already fetched. Nothing to do.")
        return

    print(f"\nStarting to fetch data for {len(movies_to_fetch)} new movies...")
    for index, movie in movies_to_fetch.iterrows():
        title, imdb_id = movie["title"], movie["imdb_id"]
        print(f"[{index + 1}/{len(top_movies_df)}] Fetching: {title} ({imdb_id})")

        # Fetch from OMDb
        omdb_data = fetch_omdb_data(imdb_id, api_key)

        if omdb_data:
            # Flatten ratings for easier storage in CSV
            ratings = omdb_data.get("Ratings", [])
            omdb_data["Ratings_flat"] = "; ".join([f"{r['Source']}: {r['Value']}" for r in ratings])
            del omdb_data["Ratings"]
            new_movie_records.append(omdb_data)

        # Rate limiting to avoid hitting API too fast
        time.sleep(0.1)

    # Append new records to CSV
    if new_movie_records:
        new_df = pd.DataFrame(new_movie_records)
        write_header = not os.path.exists(OMDB_DATA_CSV)
        new_df.to_csv(OMDB_DATA_CSV, mode='a', header=write_header, index=False)

        print(f"\nSuccess! Appended data for {len(new_movie_records)} new movies to {OMDB_DATA_CSV}")
    else:
        print("\nNo new movie data was successfully fetched.")

# Entry point
if __name__ == "__main__":
    main()
