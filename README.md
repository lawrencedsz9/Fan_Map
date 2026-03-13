# Fandom Intelligence Graph

**Real-time internet attention map for any topics, fandoms, or brands.**

This project ingests attention signals from around the internet (Reddit, YouTube, Google Trends, etc.), builds a knowledge graph, and surfaces **what is currently trending** for the topics you care about.  

The default configuration ships with **anime titles as example topics**, but the system is completely generic — you can point it at **any set of topics, communities, or keywords** (e.g. games, brands, creators, sports teams).

---

## Features

- **Multi-source attention signals**: Reddit, YouTube, Google Trends, and more (via pluggable collectors).
- **Topic/entity extraction**: Uses NLP to enrich raw signals with entities and topics.
- **Knowledge graph**: Builds a graph of topics, co-occurrences, and relationships.
- **Trend explosion detection**: Flags topics whose attention is spiking relative to a baseline.
- **Interactive visualization**: Generates an `attention_graph.html` file you can explore.
- **Web dashboard (FastAPI)**: Simple dashboard and API to inspect stats and the graph.

---

## Setup

1. **Clone the repo and enter the folder**

   ```bash
   cd Map_fn
   ```

2. **Setup a Virtual env**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # macOS / Linux
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   - `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`
   - `YOUTUBE_API_KEY`
   - `USE_MOCK_DATA=true` to run without real API keys (uses sample/mock data)

---

## working structure

setup with the main.py:

1. **Collect attention signals** (Reddit, YouTube, Trends, etc.).
2. **Extract entities and topics** from the collected signals.
3. **Build a knowledge graph** linking topics and signals.
4. **Detect trend explosions** relative to historical baselines.
5. **Render an interactive visualization** to `data/attention_graph.html`.
6. **Optionally launch the dashboard** (FastAPI + HTML frontend).

---

## Usage

From the project root:

- **working pipeline**

  ```bash
  python main.py
  ```

- **Collect only**

  ```bash
  python main.py --collect
  ```

- **Build graph from cached signals**

  ```bash
  python main.py --graph
  ```

- **Launch dashboard only**

  ```bash
  python main.py --serve
  ```

When serving, the dashboard is available at:

- Dashboard: `http://localhost:8000`
- Graph: `http://localhost:8000/graph`
- API: `http://localhost:8000/api/stats`

---

## Customizing for your own use case

Core configuration lives in `config.py`. The most important pieces for customizing are:

- `TRACKED_TOPICS`: list of topics/keywords to track.  
  - Defaults to a set of anime titles as an example.
  - Replace these with **your own topics** (e.g. games, brands, creators, products, sports teams).
- `SUBREDDITS`: list of subreddits to monitor.  
  - Swap these for communities relevant to your domain.
- `WEIGHTS`: how much each signal source (Reddit, YouTube, Google Trends, news) contributes to the overall attention score.
- `EXPLOSION_THRESHOLD`: how big an increase over baseline is required to flag a topic as "exploding".

You can also plug in new data sources by adding collectors under the `collectors` module and wiring them into the pipeline.

---

