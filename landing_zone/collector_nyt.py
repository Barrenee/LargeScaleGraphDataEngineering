import os
import datetime
import pandas as pd
from typing import Tuple
from pynytimes import NYTAPI
from dotenv import dotenv_values
import json
from typing import Optional
import requests

CSV_FILE = "./landing_zone/data/nyt.csv"
DATA_DIR = "./landing_zone/nyt"
TMDB_DIR = "landing_zone/tmdb"
ACTOR_CACHE = "./landing_zone/nyt/actor_cache.json"
MOVIE_CSV = "./landing_zone/nyt/movie_reviews.csv"
ACTORS_CSV = "./landing_zone/nyt/actor_articles.csv"


# === Utils ===
def load_json(path: str):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)



def get_articles(
    keyword: str,
    actor_id: str,
    date_range: Tuple[int, int, int, int, int, int],
    api_key: str,
    max_results: int = 100
) -> pd.DataFrame:
    nyt = NYTAPI(api_key, parse_dates=True)

    start_date = datetime.datetime(date_range[0], date_range[1], date_range[2])
    end_date = datetime.datetime(date_range[3], date_range[4], date_range[5])

    print(f"Searching for '{keyword}' between {start_date.date()} and {end_date.date()}")

    try:
        articles = nyt.article_search(
            query=keyword,
            dates={
                "begin": start_date,
                "end": end_date
            },
            results=max_results
        )
    except Exception as e:
        print(f"article not found for {keyword}")
        print(f'error: {e}')
        return None
    # Keep only up to max_results
    articles = articles[:max_results]

    results = []
    for article in articles:
        results.append({
            "actor_id": actor_id,
            "title": article.get("headline", {}).get("main"),
            "abstract": article.get("abstract"),
            "pub_date": article.get("pub_date"),
            "web_url": article.get("web_url"),
            "section": article.get("section_name"),
            "keywords": ", ".join([kw.get("value") for kw in article.get("keywords", [])])
        })

    return results


def get_movie_reviews(
    movie_title: str,
    date_range: Tuple[int, int, int, int, int, int],
    api_key: str,
    max_results: int = 100
) -> pd.DataFrame:
    nyt = NYTAPI(api_key, parse_dates=True)
    print(date_range)
    start_date = datetime.datetime(date_range[0], date_range[1], date_range[2])
    end_date = datetime.datetime(date_range[3], date_range[4], date_range[5])

    print(f"Fetching reviews for '{movie_title}' from {start_date.date()} to {end_date.date()}")

    try:
        reviews = nyt.article_search(
            query=movie_title,
            dates={
                "publication_date_start": start_date,
                "publication_date_end": end_date
            },
            options={"section_name":["movies"],"sort": "relevance"}
        )
    except Exception as e:
        print(f"[!] Error fetching reviews for '{movie_title}': {e}")
        return None
    
    
    reviews = reviews[:max_results]

    rows = []
    for article in reviews:
        rows.append({
            "title": article.get("headline", {}).get("main"),
            "abstract": article.get("abstract"),
            "pub_date": article.get("pub_date"),
            "web_url": article.get("web_url"),
            "section": article.get("section_name"),
            "keywords": ", ".join([kw.get("value") for kw in article.get("keywords", [])])
        })

    return pd.DataFrame(rows)





def get_omdb_review(movie_title: str, api_key: str) -> Optional[pd.DataFrame]:
    url = "http://www.omdbapi.com/"
    params = {
        "t": movie_title,
        "apikey": api_key,
        "plot": "full"
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if data.get("Response") != "True":
            print(f"❌ Movie not found: {movie_title}")
            return None

        print(f"✅ Fetched OMDb data for: {movie_title}")
        return pd.DataFrame([{
            "Title": data.get("Title"),
            "Year": data.get("Year"),
            "Rated": data.get("Rated"),
            "Released": data.get("Released"),
            "Runtime": data.get("Runtime"),
            "Genre": data.get("Genre"),
            "Director": data.get("Director"),
            "Writer": data.get("Writer"),
            "Actors": data.get("Actors"),
            "Plot": data.get("Plot"),
            "Language": data.get("Language"),
            "Country": data.get("Country"),
            "Awards": data.get("Awards"),
            "Poster": data.get("Poster"),
            "Metascore": data.get("Metascore"),
            "imdbRating": data.get("imdbRating"),
            "imdbVotes": data.get("imdbVotes"),
            "imdbID": data.get("imdbID"),
            "BoxOffice": data.get("BoxOffice"),
            "Production": data.get("Production"),
            "Website": data.get("Website"),
            "Ratings": "; ".join([f"{r['Source']}: {r['Value']}" for r in data.get("Ratings", [])])
        }])
    except Exception as e:
        print(f"Error fetching from OMDb: {e}")
        return None

def save_incrementally(new_df: pd.DataFrame, filename: str):
    if os.path.exists(filename):
        existing_df = pd.read_csv(filename)
        existing_urls = set(existing_df["web_url"].dropna())
    else:
        existing_df = pd.DataFrame()
        existing_urls = set()

    new_df_filtered = new_df[~new_df["web_url"].isin(existing_urls)]

    if not new_df_filtered.empty:
        df_combined = pd.concat([existing_df, new_df_filtered], ignore_index=True)
        df_combined.to_csv(filename, index=False)
        print(f"Saved {len(new_df_filtered)} new articles to {filename}")
    else:
        print("No new articles to save.")


'''        
def save_articles(new_df: pd.DataFrame, filename: str = CSV_FILE):
    if os.path.exists(filename):
        existing_df = pd.read_csv(filename)
        already_saved_urls = set(existing_df["web_url"].dropna().unique())
    else:
        existing_df = pd.DataFrame()
        already_saved_urls = set()

    # Filter out duplicates based on web_url
    new_df_filtered = new_df[~new_df["web_url"].isin(already_saved_urls)]

    if not new_df_filtered.empty:
        updated_df = pd.concat([existing_df, new_df_filtered], ignore_index=True)
        updated_df.to_csv(filename, index=False)
        print(f"Added {len(new_df_filtered)} new articles. Total now: {len(updated_df)}")
    else:
        print("No new articles to save.")
'''




def main_iter(num:int, search_movies: bool=False, search_actors: bool=True):
    #os.makedirs(TMDB_DIR, exist_ok=True)
    api_key = dotenv_values(".env")["NYT_KEY"]

    # Load movie + credits JSONs
    credits = load_json(os.path.join(TMDB_DIR, f"{num}_credits.json"))
    movie = load_json(os.path.join(TMDB_DIR, f"{num}_info.json"))

    title = movie.get("title", "Unknown")
    year = int(movie.get("release_date", "1900-01-01").split("-")[0])


    # Setup NYT API client
    date_window = (year - 1, 1, 1, year + 5, 12, 31)
    date_window = (2020,1,1,2024,1,1)
    # === Movie Article Search ===

    if search_movies:
        print("title:", title)
        print("date: ", date_window)

        df_movie = get_movie_reviews(title, date_window, api_key)
        if not df_movie is None:
            save_incrementally(df_movie, MOVIE_CSV)

    # === Actor Article Search + Cache Update ===
    if search_actors:
        
        # Load actor cache
        if not os.path.exists(ACTOR_CACHE):
            cache = {"cached_actors":[]}
            with open(ACTOR_CACHE, "w") as f:
                json.dump(cache, f)
            
        else:
            cache = load_json(ACTOR_CACHE)
        

        actors_found = []
        
        cast_names_ids = [(person["name"],person["id"]) for person in credits.get("cast", [])]

        for name,id_ in cast_names_ids[:5]:
            if id_ in cache["cached_actors"]:
                print(f" >> Skipping cached actor: {name}")
                continue

            actor = get_articles(name,id_, date_window, api_key, 2)
            if actor is not None:

                save_incrementally(pd.DataFrame(actor), ACTORS_CSV)
            cache["cached_actors"] += [id_]
        # Save cache
        save_json(cache, ACTOR_CACHE)
    #print("here")


def main():
    TMDB_DIR = "landing_zone/tmdb"
    json_nums = list(set(map(lambda x: int(x.split("_")[0]), os.listdir(TMDB_DIR))))
    for num in json_nums:
        main_iter(num)

if __name__ == "__main__":
    main()