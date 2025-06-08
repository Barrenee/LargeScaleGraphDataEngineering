import os
import datetime
import pandas as pd
from typing import Tuple, Optional
from pynytimes import NYTAPI
from dotenv import dotenv_values
import json
import time


CSV_FILE = "./landing_zone/data/nyt.csv"
TMDB_DIR = "landing_zone/tmdb"
ACTOR_CACHE = "./landing_zone/nyt/actor_cache.json"
MOVIE_CSV = "./landing_zone/nyt/movie_reviews2.csv"
ACTORS_CSV = "./landing_zone/nyt/actor_articles2.csv"
TOP_N_COUNT = 100  # Number of top entities (movies and actors) to process


# NYT2 Collector
#   Although collector nyt would be the official collector of the New York Times API, 
#   this script is used as an auxiliary script, which collects metadata about 
#   the n most popular movies and actors from TMDB and fetches related articles and reviews.  
#   The results are incrementally saved to CSV files to avoid duplicates. 
#   Cached actor IDs are stored to prevent repeated queries.


def load_json(path: str):
    """Safely load a JSON file from the given path. Return empty dict if missing or malformed."""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(f"[Warning] Could not decode JSON from {path}. Skipping.")
            return {}


def save_json(data, path: str):
    """Save data as JSON to the specified file path."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_articles(
    keyword: str,
    actor_id: str,
    date_range: Tuple[int, int, int, int, int, int],
    api_key: str,
    max_results: int = 10
) -> Optional[pd.DataFrame]:
    """Fetch NYT articles for a given actor keyword within a specified date range."""
    nyt = NYTAPI(api_key, parse_dates=True)
    start_date = datetime.datetime(*date_range[:3])
    end_date = datetime.datetime(*date_range[3:])

    print(f"Searching for '{keyword}' between {start_date.date()} and {end_date.date()}")

    try:
        articles = nyt.article_search(
            query=keyword,
            dates={"begin": start_date, "end": end_date},
            results=max_results
        )
    except Exception as e:
        print(f"article not found for {keyword}")
        print(f'error: {e}')
        return None
    
    if not articles:
        return None

    # Structure relevant fields into DataFrame
    results = [{
        "actor_id": actor_id,
        "title": a.get("headline", {}).get("main"),
        "abstract": a.get("abstract"),
        "pub_date": a.get("pub_date"),
        "web_url": a.get("web_url"),
        "section": a.get("section_name"),
        "keywords": ", ".join([kw.get("value") for kw in a.get("keywords", [])])
    } for a in articles[:max_results]]

    return pd.DataFrame(results)


def get_movie_reviews(
    movie_title: str,
    date_range: Tuple[int, int, int, int, int, int],
    api_key: str,
    max_results: int = 10
) -> Optional[pd.DataFrame]:
    """Fetch NYT reviews for a movie title within a specified date range."""
    nyt = NYTAPI(api_key, parse_dates=True)
    start_date = datetime.datetime(*date_range[:3])
    end_date = datetime.datetime(*date_range[3:])

    print(f"Fetching reviews for '{movie_title}' from {start_date.date()} to {end_date.date()}")

    try:
        reviews = nyt.article_search(
            query=f'"{movie_title}"',
            dates={"begin": start_date, "end": end_date},
            options={"sort": "relevance"}
        )
    except Exception as e:
        print(f"[!] Error fetching reviews for '{movie_title}': {e}")
        return None
    
    if not reviews:
        return None

    # Structure fields into DataFrame
    rows = [{
        "title": r.get("headline", {}).get("main"),
        "abstract": r.get("abstract"),
        "pub_date": r.get("pub_date"),
        "web_url": r.get("web_url"),
        "section": r.get("section_name"),
        "keywords": ", ".join([kw.get("value") for kw in r.get("keywords", [])])
    } for r in reviews[:max_results]]

    return pd.DataFrame(rows)


def save_incrementally(new_df: pd.DataFrame, filename: str):
    """Append only new rows to the existing CSV file, identified by web_url."""
    if new_df is None or new_df.empty:
        print(f"No new data to save to {filename}.")
        return

    if os.path.exists(filename):
        existing_df = pd.read_csv(filename)
        existing_urls = set(existing_df["web_url"].dropna()) if "web_url" in existing_df.columns else set()
    else:
        existing_df = pd.DataFrame()
        existing_urls = set()

    new_df_filtered = new_df[~new_df["web_url"].isin(existing_urls)]

    if not new_df_filtered.empty:
        df_combined = pd.concat([existing_df, new_df_filtered], ignore_index=True)
        df_combined.to_csv(filename, index=False)
        print(f"✅ Saved {len(new_df_filtered)} new articles to {filename}")
    else:
        print("No new articles to save (already exist in file).")


def get_top_entities(tmdb_dir: str, top_n: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Identify top-N movies and actors by popularity from locally saved TMDB JSON data."""
    print(f"Scanning {tmdb_dir} to find top {top_n} movies and actors...")
    all_movies = []
    all_actors = {}

    json_files = os.listdir(tmdb_dir)
    movie_ids = list(set([f.split('_')[0] for f in json_files]))

    for movie_id in movie_ids:
        # Load movie metadata
        info_path = os.path.join(tmdb_dir, f"{movie_id}_info.json")
        movie_data = load_json(info_path)
        if not movie_data or "id" not in movie_data:
            continue

        all_movies.append({
            "id": movie_data.get("id"),
            "title": movie_data.get("title"),
            "release_date": movie_data.get("release_date", "1900-01-01"),
            "popularity": movie_data.get("popularity", 0)
        })

        # Load movie credits
        credits_path = os.path.join(tmdb_dir, f"{movie_id}_credits.json")
        credits_data = load_json(credits_path)
        if not credits_data or "cast" not in credits_data:
            continue

        for person in credits_data.get("cast", []):
            actor_id = person.get("id")
            if not actor_id:
                continue

            # Update actor record if this one is more popular
            if actor_id not in all_actors or person.get("popularity", 0) > all_actors[actor_id]["popularity"]:
                all_actors[actor_id] = {
                    "id": actor_id,
                    "name": person.get("name"),
                    "popularity": person.get("popularity", 0)
                }

    # Convert to DataFrames and filter top-N
    movies_df = pd.DataFrame(all_movies)
    actors_df = pd.DataFrame(list(all_actors.values()))
    top_movies = movies_df.nlargest(top_n, "popularity").reset_index(drop=True)
    top_actors = actors_df.nlargest(top_n, "popularity").reset_index(drop=True)

    print(f"Found {len(movies_df)} unique movies and {len(actors_df)} unique actors.")
    print(f"Identified top {len(top_movies)} movies and {len(top_actors)} actors.")
    
    return top_movies, top_actors


def main():
    """Main entry point of the script."""
    os.makedirs(os.path.dirname(MOVIE_CSV), exist_ok=True)

    # Load NYT API key
    try:
        api_key = dotenv_values(".env")["NYT_KEY"]
    except KeyError:
        print("[Error] NYT_KEY not found in .env file. Please create one.")
        return

    # Fetch top movies and actors from local TMDB data
    top_movies_df, top_actors_df = get_top_entities(TMDB_DIR, TOP_N_COUNT)

    print(f"\n--- Processing Top {TOP_N_COUNT} Movies ---")
    for index, movie in top_movies_df.iterrows():
        title = movie["title"]
        print(f"\n[{index + 1}/{len(top_movies_df)}] Movie: {title}")

        try:
            year = int(movie.get("release_date", "1900-01-01").split("-")[0])
            date_window = (year - 1, 1, 1, year + 4, 12, 31)
        except (ValueError, IndexError):
            print(f"  [Warning] Could not parse year for {title}. Using a default wide date range.")
            year = datetime.datetime.now().year
            date_window = (1980, 1, 1, year, 12, 31)

        df_movie = get_movie_reviews(title, date_window, api_key)
        time.sleep(12)  # Avoid hitting NYT rate limits
        save_incrementally(df_movie, MOVIE_CSV)

    print(f"\n--- Processing Top {TOP_N_COUNT} Actors ---")
    actor_cache = load_json(ACTOR_CACHE)
    actor_cache.setdefault("cached_actors", [])

    for index, actor in top_actors_df.iterrows():
        actor_name = actor["name"]
        actor_id = actor["id"]
        print(f"\n[{index + 1}/{len(top_actors_df)}] Actor: {actor_name}")

        if actor_id in actor_cache["cached_actors"]:
            print(f"  >> Skipping cached actor: {actor_name}")
            continue

        current_year = datetime.datetime.now().year
        date_window = (current_year - 10, 1, 1, current_year, 12, 31)

        df_actor = get_articles(actor_name, actor_id, date_window, api_key)
        time.sleep(12)
        if df_actor is not None and not df_actor.empty:
            save_incrementally(df_actor, ACTORS_CSV)

        actor_cache["cached_actors"].append(actor_id)

    # Save updated actor cache
    save_json(actor_cache, ACTOR_CACHE)
    print("\nProcessing complete.")


if __name__ == "__main__":
    main()
