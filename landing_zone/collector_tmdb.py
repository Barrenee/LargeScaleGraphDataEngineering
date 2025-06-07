import tmdbsimple as tmdb
import time
import os
import json
from requests.exceptions import HTTPError
from dotenv import load_dotenv
import os 
load_dotenv()

tmdb.API_KEY = os.environ.get("TMDB_API_KEY")

tmdb.REQUESTS_TIMEOUT = 5

OUTPUT_DIR = './landing_zone/tmdb'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    print(f"Created directory: {OUTPUT_DIR}")

print("Starting data collection for the first 5000 movie IDs...")

for movie_id in range(5000):
    try:
        movie = tmdb.Movies(movie_id)

        info_response = movie.info()

        credits_response = movie.credits()

        info_filepath = os.path.join(OUTPUT_DIR, f"{movie_id}_info.json")
        credits_filepath = os.path.join(OUTPUT_DIR, f"{movie_id}_credits.json")

        with open(info_filepath, 'w', encoding='utf-8') as f:
            json.dump(info_response, f, ensure_ascii=False, indent=4)

        with open(credits_filepath, 'w', encoding='utf-8') as f:
            json.dump(credits_response, f, ensure_ascii=False, indent=4)

        print(f"Successfully saved data for movie ID: {movie_id} ('{info_response.get('title', 'N/A')}')")

    except HTTPError as e:
        if e.response.status_code == 404:
            print(f"Movie with ID {movie_id} not found. Skipping.")
        else:
            print(f"HTTP Error for movie ID {movie_id}: {e}. Skipping.")
    except Exception as e:
        print(f"An unexpected error occurred for movie ID {movie_id}: {e}. Skipping.")

    time.sleep(0.3)

print("\nData collection finished.")