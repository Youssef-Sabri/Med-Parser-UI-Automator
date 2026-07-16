# Med-Parser: Pharmaceutical Clinical Automation

**Med-Parser** is a secure, professional-grade pharmacy automation platform designed to bridge the gap between paper-based clinical workflows and legacy Pharmacy Management Systems (PMS). By leveraging Google Gemini Vision AI and a specialized RPA Bridge Agent, Med-Parser digitizes prescription faxes and injects verified data directly into target software with zero manual transcription.

---

## The Core Problem
Pharmacists spend hours manually transcribing handwritten or faxed prescriptions into legacy systems, a process prone to human error and fatigue. **Med-Parser** solves this by:
1.  **Extracting**: Using Vision AI to digitize unstructured clinical images.
2.  **Verifying**: Providing a high-fidelity dashboard for Human-in-the-Loop (HITL) review.
3.  **Injecting**: Using an RPA agent to "type" verified data into legacy Windows software.

---

## System Architecture

```
Prescription Fax
        |
        v
  [Upload] --> FastAPI Backend (Python 3.12)
        |
        v
  Secure Image Storage (staging/)
        |
        v
  Gemini Vision AI Extraction
        |
        v
  Guardrail Engine (drug interactions, dosage limits)
        |
        v
  Pharmacist Dashboard (React 19 + TailwindCSS)
        |
   [Review / Edit / Approve]
        |
        v
  Local Bridge Agent (Flask + PyAutoGUI)
        |
        v
  Legacy PMS Software (Notepad, etc.)
        |
        v
  Status Callback --> FastAPI Backend
```

---

## Key Features

### Intelligent Extraction
- **Multimodal AI**: Leverages the Google Gemini Vision API for high-speed, accurate clinical text extraction. Concurrency is throttled via `asyncio.Semaphore` to prevent API rate-limit crashes.
- **Split-Faxes**: Automatically detects and handles multiple prescriptions within a single multi-page document.
- **Semantic Deduplication**: Prevents duplicate processing by checking HMAC-SHA256 clinical hashes within a 30-day window.
- **Magic-Byte Validation**: Uploaded files are validated against expected content-type magic bytes before being written to disk.

### Security & Compliance
- **At-Rest Encryption**: Field-level AES-256 (Fernet) encryption for all Patient Health Information (PHI).
- **Secure Wipe**: Automatic multi-pass overwriting of clinical images before deletion to meet compliance schedules.
- **Timing-Safe Auth**: All API endpoints enforce timing-safe API key comparison via `hmac.compare_digest`.
- **CSP Headers**: Strict Content-Security-Policy with no `unsafe-eval`.
- **Stateless Agent**: The Bridge Agent operates locally near the PMS, minimizing the exposure of sensitive data over the network.

### Production-Grade RPA Bridge Agent
- **ScreenSeeker visual pipeline**: A robust 4-stage fallback discovery process to locate the target software:
  1. Active Window Name matching.
  2. Desktop Icon visual search (Gemini AI vision).
  3. Taskbar visual search (Gemini AI vision).
  4. OS-level Start Menu search fallback.
- **Strict Focus Guarding**: Enforces strict window title verification to prevent PHI from being injected into the wrong application (Anti-Browser Shield).
- **Per-Case Aborts**: Allows emergency aborts via global hotkey (`CTRL+SHIFT+Z`), immediately reverting the script to a "Ready" state on the dashboard for quick retries without interfering with parallel tasks.
- **Public Health Check**: The agent's `/health` endpoint is unauthenticated for dashboard status polling.
- **Zero-Fallback Config**: All system settings and specific PMS hotkeys MUST be configured in `.env`; the system intentionally drops hardcoded defaults to ensure strict behavior control.

---

## Tech Stack
- **Frontend**: React 19, TypeScript 5.9, TailwindCSS 3.4, Lucide Icons, Vite 5.
- **Backend**: FastAPI 0.115 (Python 3.12), SQLAlchemy 2.0 (SQLite/PostgreSQL), Pydantic v2 with `pydantic-settings`, Alembic migrations.
- **AI/ML**: Google Gemini Vision API (gemini-3.1-flash-lite-preview).
- **RPA**: Flask, PyAutoGUI, PyGetWindow, local HTTP Bridge Agent.
- **Testing**: pytest (backend, 18 tests), `tsc -b && vite build` (frontend).

---

## Getting Started

### Requirements
*   **Docker Desktop** (for the Platform)
*   **Python 3.12+** (for the local Bridge Agent, runs on the Windows host with the PMS)
*   **Google Gemini API Key**

### 1. Clone & Configure

```bash
git clone https://github.com/Youssef-Sabri/Med-Parser-UI-Automator.git
cd Med-Parser-UI-Automator

# Configure environment (all variables are MANDATORY)
cp .env.example .env
# Edit .env with your actual API keys and secrets
```

### 2. Platform Setup (Backend & UI)

The system operates under a strict **Zero-Fallback** policy. All environment variables in `.env` MUST be populated for the backend and agent to boot.

```bash
# Launch via Docker Compose
docker compose up --build
```

The clinical dashboard will be available at `http://localhost:5173`.

### 3. Local Development (without Docker)

```bash
# Backend
cd backend
pip install -r requirements.txt
python ../backend/prestart.py    # Initialize DB schema
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### 4. Local Bridge Agent (RPA)

The agent must be run directly on the **Windows host** where the target Pharmacy Management System (PMS) is installed:

```bash
cd automation
pip install -r requirements.txt
python agent.py
```

---

## Testing

```bash
# Backend tests (18 tests)
python -m pytest backend/tests/ -v

# Frontend type check + production build
cd frontend
npm run build    # runs: tsc -b && vite build
```

---

## Directory Structure
- `backend/`: FastAPI orchestration, encryption services, Alembic migrations, and database logic.
- `frontend/`: React 19 clinical dashboard and verification UI (served via nginx in production).
- `automation/`: The local RPA Bridge Agent (Flask + PyAutoGUI) and ScreenSeeker visual grounding engine.
- `common/`: Shared utilities, secure wipe, input sanitization, and formatting helpers.
- `docs/`: Centralized Product Requirement Documents (PRDs).
- `staging/`: PHI file staging area (gitignored, wiped after 24h).
