# Movieverse Knowledge Graph: From Data to Embeddings

This project contains an end-to-end pipeline for building a comprehensive Knowledge Graph (KG) and leveraging it for advanced analytical and machine learning tasks. The system integrates data from multiple sources (TMDB, OMDB, Spotify, New York Times), constructs a semantic graph using RDF, trains knowledge graph embeddings, and applies them to real-world use cases like movie recommendation and synergy prediction.

## Key Features
It follows the different Data Engineering zones (landing, formatted, trusted, exploitation) and includes:

-   **Knowledge Graph Construction**: Unifies disparate data sources into a rich, interconnected graph using RDFS, FOAF, and Schema.org vocabularies.
-   **SPARQL-based Analytics**: Showcases complex analytical queries on the graph, including identifying top actor-director collaborations and finding paths between actors ("Six Degrees of Separation").
-   **Knowledge Graph Embeddings**: Trains and evaluates multiple KGE models (TransE, DistMult, ComplEx) to learn vector representations of entities and relations. DistMult was found to be the most effective for this graph's structure.
-   **Embedding-Powered Applications**:
    -   **Movie Recommendation**: A content-based recommender using cosine similarity on movie embeddings.
    -   **Synergy Prediction**: A regression model that predicts the potential success (rating) of a hypothetical actor-director collaboration.

## Core Modules & Notebooks

-   `landing_zone/`: Python scripts to fetch data from various APIs.
-   `formatted_zone.ipynb`: Defines the PostgreSQL schema and loads raw data into tables.
-   `trusted_zone.ipynb`: Applies data quality rules and validation to the data in PostgreSQL.
-   `graph_zone.ipynb`: Constructs the RDF knowledge graph from the trusted PostgreSQL data and serializes it to `knowledge_graph.ttl`.
-   `embeddings.py`: Trains and evaluates KGE models, saving the best-performing model and its mappings.
-   `sparql_analysis.ipynb`: Querying of the KG via a GraphDB SPARQL endpoint.
-   `recommendation.ipynb`: A movie recommender system built on the trained embeddings.
-   `synergy.ipynb`: Predicts actor-director collaboration ratings using an MLP on combined embeddings.

## Technology Stack

-   **Programming Language**: Python
-   **Data Processing**: PySpark, Pandas
-   **Database**: PostgreSQL
-   **Semantic Web**: RDFLib, SPARQLWrapper, GraphDB
-   **Machine Learning**: PyTorch, TorchKGE, Scikit-learn

## Setup

Ensure you have **PostgreSQL** and a **GraphDB** instance running. You can use Docker for easy setup.
-   Create a PostgreSQL database named `bdaproject2`.
-   In GraphDB, create a repository named `bdaproject2`.

**Set Up Environment Variables**
    Create a `.env` file in the root directory and add your API keys:
    ```env
    TMDB_API_KEY="your_tmdb_key"
    OMDB_KEY="your_omdb_key"
    NYT_KEY="your_nyt_key"
    SPOTIFY_CLIENT_ID="your_spotify_id"
    SPOTIFY_CLIENT_SECRET="your_spotify_secret"
    ```