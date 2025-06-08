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
TMDB_DIR = "landing_zone/tmdb"


# NEW YORK TIMES Collector

#   This script allows for occasional or periodical updates on new york time's articles that 
#   mention a given person involved in the creation of the movie. The script reads all of the
#   already retrieved raw data on movies and then iterates over the different people involved 
#   in the creation of it. By making use of a cache so as to avoid repeating api calls, 
#   the script retrieves articles for every person which still has not tried any call.


# === Utils ===
def load_json(path: str):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# === Main Functions ===
def get_articles(
    keyword: str,
    actor_id: str,
    date_range: Tuple[int, int, int, int, int, int],
    api_key: str,
    max_results: int = 100
) -> pd.DataFrame:
    """
    This function makes an api call to the new york times api and receives a number of 
    articles related to the keyword passed as an argument (in this case people who participated in the movie)

    The function returns a pandas data frame including some extra information such as the 
    actor_id used in the TMDB retrieved data 
    """
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
    """
    DEPRECATED

    The idea of this function was to retrieve a review by the new york times about a movie that was 
    received as an argument. However, the nyt api was not working correctly, so we ended up not using it
    """
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


def save_incrementally(new_df: pd.DataFrame, filename: str):
    """
    The function saves new data into an existing csv. It receives a dataframe
    and filename, and saves said dataframe in the given file, by joining them 
    and erasing possible duplicates.
    """
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


def main_iter(num:int, search_movies: bool=False, search_actors: bool=True):
    """
    This function comprises the main logic of the program. It's main objective
    is to load the already loaded movies and call the auxiliary functions so as
    to retrieve the articles related to all of the people who worked on them
    """
    api_key = dotenv_values(".env")["NYT_KEY"]

    # Load movie + credits JSONs
    credits_ = load_json(os.path.join(TMDB_DIR, f"{num}_credits.json"))
    movie = load_json(os.path.join(TMDB_DIR, f"{num}_info.json"))

    title = movie.get("title", "Unknown")
    year = int(movie.get("release_date", "1900-01-01").split("-")[0])

    date_window = (year - 1, 1, 1, year + 5, 12, 31)
    date_window = (2020,1,1,2024,1,1)

    # DEPRECATED: Movie Review search
    #               due to the nyt movie reviews api not working correctly, we did not
    #               use this section fo the code
    if search_movies:
        print("title:", title)
        print("date: ", date_window)

        df_movie = get_movie_reviews(title, date_window, api_key)
        if not df_movie is None:
            save_incrementally(df_movie, MOVIE_CSV)

    # Article search
    #   This section loops over all of the actors or workers on retrieved movies and 
    #   calls the api to retrieve articles related to them. It aksi saves all of the actors 
    #   whose articles have been retrieved into a cache file, so as to not make duplicate api calls
    if search_actors:
        
        # Load actor cache
        if not os.path.exists(ACTOR_CACHE):
            cache = {"cached_actors":[]}
            with open(ACTOR_CACHE, "w") as f:
                json.dump(cache, f) 
        else:
            cache = load_json(ACTOR_CACHE)
        
        cast_names_ids = [(person["name"],person["id"]) for person in credits_.get("cast", [])]

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


if __name__ == "__main__":
    json_nums = list(set(map(lambda x: int(x.split("_")[0]), os.listdir(TMDB_DIR))))
    for num in json_nums:
        main_iter(num)