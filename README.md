# 🌐 CiteLabs — AEO / GEO Evaluation Platform

<div align="center">

![CiteLabs Banner](assets/citelabs-home.png)

[![Next.js](https://img.shields.io/badge/Next.js-14-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![Fastify](https://img.shields.io/badge/Fastify-4-black?style=for-the-badge&logo=fastify)](https://fastify.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python_3.12-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-3.7_Flash-4285F4?style=for-the-badge&logo=google)](https://ai.google.dev/)
[![Pinecone](https://img.shields.io/badge/Pinecone-Vector_DB-000000?style=for-the-badge&logo=pinecone)](https://www.pinecone.io/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=for-the-badge&logo=supabase)](https://supabase.com/)

**An end-to-end evaluation engine for Answer Engine Optimization (AEO) and Generative Engine Optimization (GEO).**  
Analyze how your domain and competitors perform in AI-powered search engines, generative summaries, and retrieval-augmented answer engines.

</div>

---

## 📌 Overview

Traditional SEO optimizes for 10 blue links; **AEO & GEO** optimize for inclusion and citation in AI-generated answers (e.g. Gemini, ChatGPT, Perplexity).

**CiteLabs** crawls a target website, analyzes its core business intent, synthesizes realistic multi-intent user queries, retrieves competing brand data, embeds domain content into vector indices, and simulates AI search answering engines. It computes measurable brand visibility, citation likelihood, and competitor dominance scores with actionable recommendations.

---

## 📸 Screenshots

<div align="center">

### 1. Analysis Launchpad
*Submit any sandbox URL to initiate comprehensive multi-step AEO/GEO analysis.*

![CiteLabs Launchpad](assets/citelabs-home.png)

<br/>

### 2. Live Pipeline Execution
*Real-time tracking of crawling, semantic classification, competitor retrieval, vector indexing, and RAG simulation.*

![CiteLabs Progress](assets/citelabs-progress.png)

</div>

---

## 🚀 Key Features

- **Automated Web Crawling & Content Extraction**: Fast scraping and parsing of title, heading, and body semantics.
- **AI Domain Summarization & Intent Extraction**: Extracts core business intent and categorizes niche domains using Google Gemini LLMs.
- **Multi-Intent Query Generation**: Generates contextual user questions across three vital search dimensions:
  - **Intent**: Informational questions assessing direct topic relevance.
  - **Experience**: Exploratory queries on user trust, safety, and operational usage.
  - **Transaction**: Buying/deployment intent queries comparing alternatives.
- **Dynamic Competitor Discovery**: Detects direct industry competitors and crawls their public knowledge base for comparison.
- **Vector Search & Semantic Retrieval**: Embeds and indexes content using Pinecone / FAISS vector stores and sentence transformers (`all-MiniLM-L6-v2`).
- **RAG Simulation Engine**: Simulates generative search answer engines under strict citation criteria.
- **Resilient Multi-Model Failover**: Intelligent rate-limiting and automatic model pool rotation across Google Gemini models (`gemini-3.7-flash`, `gemini-3.8-flash`, `gemini-3.5-flash-lite`) to avoid free-tier quota stalls.
- **Interactive Analytics Dashboard**: Real-time polling progress bar, citation distributions, chunk analysis, and GEO/AEO scoring breakdown.

---

## 🏗️ System Architecture

```mermaid
flowchart LR
    A[Frontend Dashboard\nNext.js + TailwindCSS\n:3001] -->|REST / Polling| B[Backend API\nFastify + Prisma\n:4000]
    B -->|PostgreSQL| C[(Supabase DB)]
    B -->|Dispatch Job| D[AI Worker Service\nFastAPI + Python 3.12\n:8001]
    D -->|Inference & Embeddings| E[Google Gemini GenAI\nModel Pool Fallback]
    D -->|Vector Indexing| F[(Pinecone / FAISS)]
    D -->|Step Progress| B
```

### Monorepo Components

| Service | Technology | Port | Description |
| :--- | :--- | :--- | :--- |
| **`cl-frontend`** | Next.js 14, React 18, TailwindCSS, Recharts | `3001` | User interface, run initiator, and real-time analytics dashboard. |
| **`cl-backend`** | Fastify 4, TypeScript, Prisma ORM | `4000` | REST API layer, job manager, and Supabase event store. |
| **`cl-workers`** | Python 3.12, FastAPI, Uvicorn, Google GenAI SDK | `8001` | Core AI computation engine, crawler, vector search, and RAG simulator. |

---

## 🔄 7-Step Evaluation Pipeline

```mermaid
graph TD
    S1[1. Crawl Target Site] --> S2[2. Domain Summary & Intent Extraction]
    S2 --> S3[3. Business Category Classification]
    S3 --> S4[4. Question Generation - 15 Queries]
    S4 --> S5[5. Competitor Discovery & Crawling]
    S5 --> S6[6. Vector Indexing Pinecone / FAISS]
    S6 --> S7[7. RAG Simulation & Scoring Calculation]
```

1. **Target Crawl**: Scrapes sandbox URL, extracting metadata, semantic text, and structure.
2. **Domain Summary**: Generates concise, factual semantic summaries to optimize prompt tokens downstream.
3. **Intent & Category**: Infers user search intent and classifies the business domain.
4. **Question Generation**: Produces 15 multi-intent queries targeting typical user decision journeys.
5. **Competitor Discovery**: Identifies competing market entities and retrieves their reference content.
6. **Vector Indexing**: Chunks and embeds text into vector storage for semantic retrieval.
7. **RAG Simulation & Scoring**: Queries the indexed knowledge base through the LLM, tracking mention rates, first-source citations, and competitor dominance.

---

## ⚙️ Getting Started

### Prerequisites

- **Node.js** v18+ and **npm**
- **Python** 3.10+ (recommended 3.12)
- **Supabase** PostgreSQL instance
- **Pinecone** API Key & Index
- **Google Gemini** API Key

---

### Environment Setup

#### 1. Backend (`citelabs/cl-backend/.env`)
```env
PORT=4000
DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT_ID].supabase.co:5432/postgres"
WORKER_BASE_URL="http://localhost:8001"
```

#### 2. Worker Service (`citelabs/cl-workers/.env`)
```env
GEMINI_API_KEY="your-gemini-api-key"
GEMINI_MODEL="gemini-3.7-flash"
GEMINI_PRO_MODEL="gemini-3.7-flash"
GEMINI_EMBED_MODEL="gemini-embedding-001"
LLM_PROVIDER="gemini"

PINECONE_API_KEY="your-pinecone-api-key"
PINECONE_INDEX_NAME="citelabs-sandbox"
PINECONE_REGION="us-east-1"
PINECONE_DIMENSION=3072

BACKEND_BASE_URL="http://localhost:4000"
WORKER_BASE_URL="http://localhost:8001"
SUPABASE_URL="https://[PROJECT_ID].supabase.co"
VECTOR_DB_PROVIDER="faiss" # or "pinecone"
```

---

### Running Locally

Run each service in a separate terminal:

#### 1. Start Backend API
```bash
cd citelabs/cl-backend
npm install
npm run prisma:generate
npm run dev
# Server listening on http://localhost:4000
```

#### 2. Start Python AI Worker
```bash
cd citelabs/cl-workers
# Create & activate virtual environment if not already done:
# python -m venv env
# .\env\Scripts\activate  (Windows) or source env/bin/activate (macOS/Linux)
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
# Worker listening on http://localhost:8001
```

#### 3. Start Frontend Dashboard
```bash
cd citelabs/cl-frontend
npm install
npm run dev
# Dashboard available on http://localhost:3001
```

---

## 📊 Evaluation Metrics

- **AEO Score (Answer Engine Optimization)**: Measures likelihood of the target domain being cited as an authoritative direct source in synthesized answers.
- **GEO Score (Generative Engine Optimization)**: Measures aggregate brand visibility, entity mentions, and contextual relevance across generative search responses.
- **Citation Rate**: Percentage of simulated queries where the target domain is explicitly credited as a primary reference.
- **Competitor Dominance**: Share of citations captured by direct competitors in the same niche.

---

## 🛡️ License

This project is licensed under the [MIT License](LICENSE).
