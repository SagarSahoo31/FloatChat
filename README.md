# 🌊 ARGO FloatChat — Ocean Intelligence Platform v4.0

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3.0%2B-003B57.svg)](https://www.sqlite.org/)
[![FAISS](https://img.shields.io/badge/FAISS-Vector_Search-FF6F00.svg)](https://github.com/facebookresearch/faiss)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**ARGO FloatChat** is an advanced, production-grade Ocean Intelligence Platform designed for physical oceanographers, climate scientists, and marine researchers. It integrates real-time global Argo float profiles, vertical cast visualizers, 3D drift trajectory analysis, multi-format dataset importers (URL, CSV, Excel, NetCDF, JSON, ZIP), and an AI scientific reasoning engine backed by RAG (Retrieval-Augmented Generation) and TEOS-10 oceanographic standards.

---

## 🌟 Key Features

- **Truthful Data Source Strategy**: Every AI response and telemetry card features an explicit runtime data source badge (`🟢 Live Argovis Dataset`, `🟢 Live IFREMER Dataset`, `🟢 Live INCOIS Dataset`, `🟡 Local Indexed Dataset`, `🟠 Local Cache`, `⚪ Synthetic Demonstration Dataset`).
- **Interactive Plotly Profiles**: Full interactive vertical casts for Temperature, Salinity, Dissolved Oxygen (DOXY), Chlorophyll-a (CHLA), pH, Nitrate, and Pressure, with oceanographic depth-inverted Y-axes, hover tooltips, zoom, pan, and PNG/SVG export.
- **Interactive Ocean Map & Drift Playback**: Leaflet map featuring basemap toggles (`Dark`, `Ocean Topo`, `Satellite`), cycle playback drift animation slider (`▶ Play` / `⏸ Pause`), directional polylines, and deployment markers.
- **Universal Search Engine**: Search across WMO numbers (partial search), institutions (`INCOIS`, `CSIRO`, `JAMSTEC`), DACs, ocean basins, variables (`TEMP`, `PSAL`, `DOXY`, `CHLA`, `PH`), and BGC parameters.
- **Multi-Turn Context Memory**: Continuous conversation context retaining active float WMO across multi-turn follow-up workflows (`Tell me about float 6901234` → `Show trajectory` → `Show salinity` → `Generate report` → `Compare with 6902881`).
- **10-Stage Data Ingestion Pipeline**: Real 10-stage connector pipeline (Health Check → Discovery → Download → Checksum → Parsing → Validation → SQLite Import → FAISS Indexing → Fleet Refresh → Audit).

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ARGO FloatChat UI                             │
│       Sidebar • Map • Plotly Profiles • Float Inspector • Chat          │
└────────────────────┬────────────────────────────────────┘
                                     │ HTTP / REST API
┌────────────────────▼────────────────────────────────────┐
│                        FastAPI Core Engine                              │
│                    backend/main.py • backend/chatbot.py                 │
└───────┬────────────────────────────┬────────────────────────────┬───────┘
        │                            │                            │
┌───────▼──────────────┐   ┌─────────▼────────────┐   ┌───────────▼───────────┐
│ AI Orchestrator & RAG │   │   SQLite Indexer     │   │   FAISS Vector Store  │
│ backend/ai_orchestrator.py│   │  backend/indexer.py │   │  faiss_vector_store   │
└──────────────────────┘   └──────────────────────┘   └───────────────────────┘
```

---

## 🚀 Quickstart & Installation

### Prerequisites
- Python 3.10 or higher
- Git

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/sharathkudachi/Argo-Floatchat.git
cd Argo-Floatchat
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize Datasets & Metadata Index
```bash
python build_index.py
```

### 4. Run Server
```bash
python main.py
```
Open **`http://localhost:8000`** in your browser. API Documentation is available at **`http://localhost:8000/docs`**.

---

## 🧪 Testing & Quality Assurance

The platform includes a comprehensive automated QA test suite:

### 1. Unit Test Suite (37 Tests)
```bash
python test_all.py
```

### 2. 102-Prompt Full-Stack Acceptance Suite
```bash
python scratch/run_full_qa_audit.py
```

### 3. Data Integrity & Consistency Audit
```bash
python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/system/consistency-audit').read().decode('utf-8'))"
```

---

## 🐳 Docker & Cloud Deployment

### Run with Docker Compose
```bash
docker-compose up --build
```

### Deploying to Render
1. Connect your repository to Render.
2. Select **Web Service** with runtime **Python**.
3. Build Command: `pip install -r requirements.txt && python build_index.py`
4. Start Command: `gunicorn -w 2 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:$PORT`

