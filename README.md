# Fandom Intelligence Graph

**Real-time internet attention map for any topics, fandoms, or brands.**

This project ingests attention signals from around the internet (Reddit, YouTube, Google Trends, etc.), builds a knowledge graph, and surfaces **what is currently trending** for the topics you care about.  

The default configuration ships with **anime titles as example topics**, but the system is completely generic — you can point it at **any set of topics, communities, or keywords** (e.g. games, brands, creators, sports teams).

---

## Features

- **LangGraph Agentic Workflow**: 13-node state machine orchestrating 5 sequential steps: parallel data collection, auto-retry logic, conditional routing, LLM judgment, and human-in-the-loop approval.
- **Parallel Data Collection**: 3 concurrent scouts (Reddit RSS, YouTube API, Google Trends) with 3x exponential backoff retry on failure.
- **Intelligent Routing**: Skips expensive analysis if no signals detected; routes medium-confidence trends to human review.
- **LLM Judgment**: Gemini integration evaluates trend authenticity with confidence scoring.
- **MongoDB Persistence**: Stores auto-approved trends, pending approvals, and historical signals.
- **Topic/entity extraction**: Uses NLP and sentence-transformers for enrichment and explosion detection.
- **FastAPI REST API**: Endpoints for trend inspection, pending approvals, and human approval workflow.
- **Interactive Graph Visualization**: NetworkX-based knowledge graph with PyVis rendering.

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
   # source .venv/bin/activate  
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables in `.env`**

   ```
   YOUTUBE_API_KEY=your_youtube_key
   Groq=your_groq_key
   MONGODB_URI=your_mongodb_connection_string
   MONGODB_DB_NAME=fanmap
   ```

5. **Ensure MongoDB is running** (used for storing trends and pending approvals)

---

## Working Structure

LangGraph agentic pipeline with 5 steps:

1. **Parallel Scouts** (Step 1-2): Reddit, YouTube, and Trends collectors run simultaneously with 3x auto-retry on failure, collecting raw attention signals.
2. **Conditional Routing** (Step 3): Router checks signal count; if empty, skips analysis to save resources.
3. **NLP Analysis** (Step 4): Enriches signals with entity extraction, topic clustering, and explosion detection (count > 5).
4. **LLM Judgment** (Step 5): Gemini evaluates sample topics for authenticity and assigns confidence score.
5. **Three-way Decision** (Step 6): High confidence (>0.85) auto-saves to trends, medium (0.60-0.85) routes to pending_approvals for human review, low (<0.60) discards.
6. **MongoDB Persistence**: Final trends and pending approvals stored for dashboard and approval workflow.
7. **Graph Building**: Generates NetworkX knowledge graph and PyVis visualization.

---

## Usage

From the project root:

- **Start the FastAPI server** 

  ```bash
  uvicorn api.server:app --reload --port 8000
  ```

- **Trigger pipeline manually**

  ```bash
  curl -X POST http://localhost:8000/api/refresh
  ```

- **Check pending approvals** (trends awaiting human review)

  ```bash
  curl http://localhost:8000/api/pending-approvals
  ```

- **Approve or reject a trend**

  ```bash
  curl -X POST "http://localhost:8000/api/approve/{trend_id}?action=approve"
  curl -X POST "http://localhost:8000/api/approve/{trend_id}?action=reject"
  ```

API available at:

- API: `http://localhost:8000/api/`
- Graph: `http://localhost:8000/graph`
- Stats: `http://localhost:8000/api/stats`
- Dashboard: `http://localhost:8000` 

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

