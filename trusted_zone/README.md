# Trusted Zone - Data Quality Rules

This repository implements a Trusted Zone framework designed to ensure the integrity, reliability, and high quality of data stored in our database systems. The rules and constraints defined across various datasets help detect and prevent bad data by addressing key data quality dimensions.
Core Data Quality Dimensions

The following overarching principles guide the validation rules implemented:
1. **Correctness**

    No null values should be present in any records.

    Duplicate rows are not allowed.

2. **Accuracy**

    Data values must reflect the real-world truth as closely as possible.

    Inaccurate or imprecise entries are flagged or denied.

3. **Consistency**

    Values must not contradict the semantics of their respective fields.

        Example: Songs must not have negative durations.

        Movies must have valid release dates.

## Dataset-Specific Rules

Below are the datasets handled in the notebook along with any specific rules (if defined in the following sections):

### Movies Database (TMDB)
#### 1. movies Table
**Completeness**	Fields movie_id, title, release_date must be non-null and title non-empty
**Accuracy**	Revenue and budget of 0 imply missing data
**Consistency**	budget, revenue, runtime, and vote_count must be non-negative
**Temporal Consistency**	release_date must be before January 1, 2030

#### 2. movie_genres Table
**Completeness**	Fields movie_id, genre_id, genre_name must be non-null and genre_name non-empty
#### 3. movie_production_companies Table
**Referential Integrity**	Fields movie_id, company_id must be non-null
**Completeness**	company_name must be non-null and non-empty

#### 4. movie_cast Table
**Completeness**	credit_id, movie_id, actor_id, actor_name must be present and credit_id/actor_name non-empty
**Accuracy**	popularity must be ≥ 3
**Cleaning**	profile_path column is dropped

#### 5. movie_crew Table
**Completeness**	credit_id, movie_id, crew_member_id, crew_member_name, department, crew_job must be non-null and non-empty
**Accuracy**	popularity must be ≥ 1
**Cleaning**	profile_path column is dropped

### OMDB Database (omdb_movie_details table)
**Completeness**	imdb_id, title, released, and box_office must be non-null and not empty. "N/A" box office is treated as invalid.
**Validity**	imdb_id must start with "tt" (valid IMDb ID format).
**Domain Constraint**	Only rows where type = 'movie' are allowed.
Range Checks	
    • year must be between 1888 and 2030	
    • If present, metascore must be between 0 and 100	
    • If present, imdb_rating must be between 0.0 and 10.0	
    • If present, imdb_votes must be ≥ 0	
**Temporal Consistency**	released must be before 2030
**Cleaning**	Dropped irrelevant or sparsely filled fields: dvd_date, production, and website

### NYT Database (actor_articles table)
**Completeness**	actor_id, title, abstract, web_url, section, and pub_date must be non-null and not empty.
**Temporal Consistency**	pub_date must not be in the future.
**Redundancy**	Duplicate entries based on actor_id and web_url are removed (uniqueness constraint).

### Spotify Database (music_tracks table)
**Completeness**	
 - Required fields:
    • track_id, track_name, artist_name, album_url, album_release must be non-null and not empty	
    • track_popularity must be non-null	

**Consistency**	
    • track_duration_ms and track_number must be positive	
    • album_total_tracks, if present, must be > 0	
    • album_release must be not in the future	
    
**Redundancy**	Duplicate track_id entries are removed
