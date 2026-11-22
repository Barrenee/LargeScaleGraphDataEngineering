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

-   [`landing_zone/`](./landing_zone/): Python scripts to fetch data from various APIs. 
-   [`formatted_zone.ipynb`](./formatted_zone/formatted_zone.ipynb): Defines the PostgreSQL schema and loads raw data into tables.
-   [`trusted_zone.ipynb`](./trusted_zone/README.md): Applies data quality rules and validation to the data in PostgreSQL.
-   [`graph_zone.ipynb`](./exploitation_zone/README.md#rdf-graph-construction-semantic-querying-embeddings-and-applications): Constructs the RDF knowledge graph from the trusted PostgreSQL data and serializes it to `knowledge_graph.ttl`.
-   [`embeddings.py`](./exploitation_zone/README.md#kg-embeddings-training-and-evaluation): Trains and evaluates KGE models, saving the best-performing model and its mappings.
-   [`sparql_analysis.ipynb`](./exploitation_zone/sparql_analysis.ipynb): Querying of the KG via a GraphDB SPARQL endpoint.
-   [`recommendation.ipynb`](./exploitation_zone/README.md#movie-recommendations-based-on-embeddings): A movie recommender system built on the trained embeddings.
-   [`synergy.ipynb`](./exploitation_zone/README.md#synergy-prediction-between-actors-and-directors): Predicts actor-director collaboration ratings using an MLP on combined embeddings.

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


## Why new data?

Our original landing zone, trusted and formatted contained data which mainly consisted on Time Series. Due to its nature, the integration between the different databases was very difficult, and modeling it as a graph didn't make a lot of sense (we had tweets, which usually create nice KGs, but stock prices and energy demand were difficult to integrate with it).

So, we decided to find out new sources of data. We finally used some movie APIs, together with Spotify. They create a very nice graph, with logical relations and were easier to integrate.