# NotePilot

An AI-powered study assistant that lets you upload documents (PDF, DOCX, TXT, MD) and chat with them. Uses RAG (Retrieval-Augmented Generation) with ChromaDB vector storage and an LLM backend to answer questions about your study material.

## Project Structure

```
notepilot/
├── .gitignore
├── README.md
├── backend/
│   ├── .env              ← NOT on git (you create this)
│   ├── .env.example      ← template for .env
│   ├── requirements.txt
│   ├── venv/             ← NOT on git (you create this)
│   ├── chroma_db/        ← auto-created by app, NOT on git
│   ├── uploads/          ← auto-created by app, NOT on git
│   ├── chats/            ← auto-created by app, NOT on git
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── routes.py
│       ├── db.py
│       ├── models.py
│       ├── rag_engine.py
│       └── document_processor.py
└── frontend/
    ├── package.json
    ├── package-lock.json
    ├── index.html
    ├── vite.config.js
    ├── node_modules/      ← NOT on git (you create this)
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── styles/
        │   └── index.css
        └── components/
            ├── Sidebar.jsx
            ├── ChatView.jsx
            └── Message.jsx
```

## Required Software

- **Python 3.10+**
- **Node.js 18+** and **npm**
- **Git**

## Fresh Setup Checklist

After cloning this repo, follow every step below:

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# If using Git Bash instead of CMD:
# source venv/Scripts/activate

# Install Python dependencies
pip install -r requirements.txt

# Create your .env file
copy .env.example .env
```

Now edit `backend/.env` and replace the placeholder with your real API key:

```
LLM_API_KEY=your_actual_api_key_here
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=nvidia/nemotron-3-nano-30b-a3b:free
```

> You need an API key from [OpenRouter](https://openrouter.ai/) or any OpenAI-compatible provider. The free nvidia/nemotron model works but you can swap it for any model your provider supports.

### 2. Frontend Setup

```bash
cd ../frontend

# Install npm dependencies
npm install
```

### 3. Run the App

Open **two terminals**:

**Terminal 1 — Backend:**
```bash
cd backend
venv\Scripts\activate
python -m app.main
```
Backend runs at `http://localhost:8000`

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```
Frontend runs at `http://localhost:5173` and proxies `/api` requests to the backend.

## Files NOT Stored on GitHub

These are excluded by `.gitignore` and must be recreated after cloning:

| File/Folder | How to Recreate | Auto-Created by App? |
|---|---|---|
| `backend/.env` | Copy `.env.example` to `.env` and add your real API key | No — you must create it manually |
| `backend/venv/` | `python -m venv venv` then `pip install -r requirements.txt` | No — you must create it manually |
| `frontend/node_modules/` | `npm install` inside `frontend/` | No — you must create it manually |
| `backend/chroma_db/` | **Yes — auto-created** by ChromaDB when the app starts | Yes |
| `backend/uploads/` | **Yes — auto-created** by the app when you upload a document | Yes |
| `backend/chats/` | **Yes — auto-created** by the app when you start chatting | Yes |
| `__pycache__/` | **Yes — auto-created** by Python automatically | Yes |
| `.DS_Store` | macOS system file, irrelevant on Windows | N/A |
