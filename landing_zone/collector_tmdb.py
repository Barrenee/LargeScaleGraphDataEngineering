import tmdbsimple as tmdb
import time
import os
import json
from requests.exceptions import HTTPError
from dotenv import load_dotenv


# TMDB Collector
#   This is the main collector in this project, 
#   which pulls information about as many movies as possible.


# Load environment variables from .env file
load_dotenv()

# Set TMDB API key from environment variable
tmdb.API_KEY = os.environ.get("TMDB_API_KEY")

# Set timeout for TMDB API requests (in seconds)
tmdb.REQUESTS_TIMEOUT = 5

# Output directory for storing the collected JSON files
OUTPUT_DIR = './landing_zone/tmdb'

# If output directory doesn't exist, create it
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    print(f"Created directory: {OUTPUT_DIR}")

print("Starting data collection for the first 5000 movie IDs...")

# Loop through the first 5000 movie IDs to collect metadata and credits
for movie_id in range(5000):
    try:
        # Create a TMDB Movies object for the given movie ID
        movie = tmdb.Movies(movie_id)

        # Fetch basic information about the movie
        info_response = movie.info()

        # Fetch cast and crew information for the movie
        credits_response = movie.credits()

        # Define file paths to store info and credits JSON
        info_filepath = os.path.join(OUTPUT_DIR, f"{movie_id}_info.json")
        credits_filepath = os.path.join(OUTPUT_DIR, f"{movie_id}_credits.json")

        # Save the movie info JSON to file
        with open(info_filepath, 'w', encoding='utf-8') as f:
            json.dump(info_response, f, ensure_ascii=False, indent=4)

        # Save the movie credits JSON to file
        with open(credits_filepath, 'w', encoding='utf-8') as f:
            json.dump(credits_response, f, ensure_ascii=False, indent=4)

        print(f"Successfully saved data for movie ID: {movie_id} ('{info_response.get('title', 'N/A')}')")

    except HTTPError as e:
        # If the movie is not found (404), skip it
        if e.response.status_code == 404:
            print(f"Movie with ID {movie_id} not found. Skipping.")
        else:
            # Handle other HTTP errors
            print(f"HTTP Error for movie ID {movie_id}: {e}. Skipping.")
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred for movie ID {movie_id}: {e}. Skipping.")

    # Wait 0.3 seconds between requests to avoid hitting rate limits
    time.sleep(0.3)

print("\nData collection finished.")
