import os
import datetime
import pandas as pd
from typing import Tuple
from pynytimes import NYTAPI
from dotenv import dotenv_values

CSV_FILE = "./landing_zone/data/nyt.csv"



def get_articles(
    keyword: str,
    pub_date_start: Tuple[int, int, int],
    pub_date_end: Tuple[int, int, int],
    key: str,
    max_results: int = 100
) -> pd.DataFrame:
    nyt = NYTAPI(key, parse_dates=True)

    start_date = datetime.datetime(*pub_date_start)
    end_date = datetime.datetime(*pub_date_end)

    print(f"Searching for '{keyword}' between {start_date.date()} and {end_date.date()}")

    articles = nyt.article_search(
        query=keyword,
        dates={
            "begin": start_date,
            "end": end_date
        },
        max_results=max_results
    )

    # Keep only up to max_results
    articles = articles[:max_results]

    results = []
    for article in articles:
        results.append({
            "title": article.get("headline", {}).get("main"),
            "abstract": article.get("abstract"),
            "pub_date": article.get("pub_date"),
            "web_url": article.get("web_url"),
            "section": article.get("section_name"),
            "keywords": ", ".join([kw.get("value") for kw in article.get("keywords", [])])
        })

    return pd.DataFrame(results)


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


def search_and_save_for_actor(actor_name: str, pub_date_start: Tuple[int,int,int], pub_date_end: Tuple[int,int,int]):
    # Ensure your NYT key is stored in an environment variable NYT_KEY
    NYT_KEY = dotenv_values(".env")["NYT_KEY"]

    #print(NYT_KEY)
    df_articles = get_articles(
        keyword=actor_name,
        pub_date_start=pub_date_start,
        pub_date_end=pub_date_end,
        key=NYT_KEY,
        max_results=3
    )
    save_articles(df_articles, "nyt.csv")
