# ApplyAI

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-Frontend-000000?logo=nextdotjs&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-06B6D4?logo=tailwindcss&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-111111)

ApplyAI is a local-first CV matching assistant with a FastAPI backend and a Next.js frontend.

It lets you:

- upload and cache a CV
- score a CV against a pasted job offer or uploaded offer document
- generate a tailored cover letter
- explore a search UI in public demo mode with mocked listings
- switch between local LLMs with Ollama or remote APIs such as OpenAI, Groq, Anthropic, Gemini, and Mistral

## Public Repo Safety

This public branch intentionally excludes any live job-board connectors, scraping logic, automated applications, and URL-based offer fetching.

The search workflows are kept in the UI as a demo experience:

- listing results are mocked in the frontend
- scoring and cover-letter generation still use the real backend
- local/private connectors are not included in Git

## Repository Layout

```text
.
|-- src/                     # FastAPI backend, matching, parsing, generation
|-- frontend/                # Next.js frontend
|   |-- src/
|   `-- .env.example
|-- testAI/                  # Local test assets
|-- config.json              # App/server/pipeline defaults
|-- requirements.txt         # Python dependencies
`-- .env.example
```

## Requirements

- Python 3.12 or 3.13 recommended
- Node.js 20+ recommended
- npm
- Ollama installed locally if you want local inference

Python 3.14 may still start, but LangChain currently emits compatibility warnings. If you want the least friction, stay on Python 3.12 or 3.13.

## Installation

### 1. Backend dependencies

```bash
cd /path/to/ApplyAI
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Frontend dependencies

```bash
cd /path/to/ApplyAI/frontend
npm install
```

### 3. Environment files

Backend example:

```bash
cd /path/to/ApplyAI
cp .env.example .env
```

Frontend example:

```bash
cd /path/to/ApplyAI/frontend
cp .env.example .env.local
```

## LLM Configuration

ApplyAI supports local and hosted LLM providers, plus optional task-based routing from `config.json`.

Main config keys:

```json
{
  "llm": {
    "provider": "ollama",
    "routing": {
      "mode": "single",
      "task_providers": {
        "cv_parser": null,
        "job_scraper": null,
        "matcher": null,
        "document_generator": null
      }
    }
  }
}
```

- `llm.provider` selects the default provider for the whole app
- `llm.routing.mode=by_task` lets you choose a different provider per module without editing Python code

### Ollama example

```env
APPLYAI_LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3:8b
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_NUM_CTX=8192
APPLYAI_FORCE_CUDA=0
OLLAMA_NUM_GPU=1
```

### OpenAI example

```env
APPLYAI_LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
```

## Run the Project

The project is configured to use:

- frontend: `http://localhost:3000`
- API: `http://127.0.0.1:8010`
- Swagger: `http://127.0.0.1:8010/docs`

### Start the API

```bash
cd /path/to/ApplyAI
source venv/bin/activate
python -m uvicorn src.main:app --host 127.0.0.1 --port 8010
```

### Start the frontend

```bash
cd /path/to/ApplyAI/frontend
npm run dev
```

The frontend reads its API target from `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8010/api
```

## API Endpoints

Main API routes:

- `GET /` service metadata
- `GET /api` API welcome endpoint
- `GET /health` and `GET /api/health` basic health status
- `POST /api/cv/upload` upload and cache a CV
- `POST /api/match` analyze a pasted offer or uploaded file
- `POST /api/match/cover-letter` generate a tailored cover letter

Interactive documentation is available at:

```text
http://127.0.0.1:8010/docs
```

## How to Test

### Quick smoke checks

API:

```bash
curl http://127.0.0.1:8010/api
curl http://127.0.0.1:8010/api/health
```

Frontend:

```bash
curl http://localhost:3000
```

### Manual end-to-end test

1. Start the API and frontend.
2. Open `http://localhost:3000`.
3. Upload the sample CV from `testAI/CV.pdf`.
4. Use `Analyser une Offre` with pasted job text or a PDF/DOCX file.
5. Use the search tabs to explore the public demo UI with mocked listings.

## Notes

- The public repository is intentionally limited to safe local parsing and matching workflows.
- Keep secrets out of Git. Use local `.env` and `frontend/.env.local` files.
- If you maintain private/local connectors, keep them outside this branch or in an ignored local directory.
