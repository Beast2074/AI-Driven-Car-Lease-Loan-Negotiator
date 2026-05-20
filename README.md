# 🚗 Car Lease & Loan AI Negotiator

A full-stack AI-powered assistant that analyzes car lease and loan contracts, detects hidden fees, scores the deal's fairness, and auto-generates professional counter-offer emails — helping consumers save thousands on their next car.

Built with **FastAPI**, **Streamlit**, **HuggingFace LLMs**, **Tesseract OCR**, and **PostgreSQL**.

---

## What It Does

Most people sign car contracts without truly understanding the terms buried in 20 pages of fine print. Dealers exploit this with inflated APRs, junk fees, and predatory penalty clauses.

This application puts AI in the consumer's corner:

- **Upload any contract** (PDF or image) and the AI extracts 15+ financial terms instantly — APR, monthly payment, residual value, mileage limits, penalties, warranty, and more
- **Get a Fairness Score from 0 to 100** based on how your deal compares to market averages across price, interest rate risk, and hidden fees
- **Generate a professional counter-offer email** with one click — ready to copy, paste, and send to the dealer
- **Compare two contracts side-by-side** and find out exactly which deal is better and why
- **Decode any VIN** to pull full vehicle specs and an estimated market value from the NHTSA database
- **Chat with an AI negotiation coach** that gives you specific dollar amounts, scripts, and strategies

---

## Fairness Score Algorithm

Every contract is scored on a **0–100 scale** across three dimensions:

| Component | Max Points | How It Works |
|-----------|-----------|--------------|
| **Price Score** | 50 | Compares your monthly payment to the market average ($500). Lower payment = higher score. |
| **Risk Score** | 30 | Starts at 30. Loses 5 points for every 1% your APR exceeds the 7.5% market benchmark. |
| **Fee Score** | 20 | Starts at 20. Loses 5 points for every junk fee detected (VIN etching, dealer prep, nitrogen fill, etc.). |

**Score interpretation:**
- 🟢 **85–100** — Excellent deal, sign with confidence
- 🟡 **55–84** — Fair deal, but there's room to negotiate
- 🔴 **Below 55** — Poor deal, renegotiate or walk away

---

## Tech Stack

| | Technology | Purpose |
|---|-----------|---------|
| ⚙️ | FastAPI + Flask | Backend REST APIs with auto-generated Swagger docs |
| 🧠 | HuggingFace (Qwen 2.5 7B Instruct) | Contract analysis, risk detection, chat, and email generation |
| 📄 | Tesseract OCR + PyPDF2 + OpenCV | Text extraction from scanned PDFs and images |
| 🖥️ | Streamlit + HTML/CSS/JS | Interactive dashboards and a dark-themed chat interface |
| 🗄️ | PostgreSQL (primary) + SQLite (auto-fallback) | Contract and user data storage |
| 🚗 | NHTSA API + MarketCheck API | VIN decoding and real market valuation |
| 🐳 | Docker Compose | One-command deployment of the full stack |
| 🧪 | Pytest (36 test files) | Comprehensive unit and integration tests |

---

## Getting Started

### Prerequisites

- **Python 3.8+** — [Download](https://www.python.org/downloads/)
- **Tesseract OCR** — Windows: [Installer](https://github.com/UB-Mannheim/tesseract/wiki) · Mac: `brew install tesseract` · Linux: `sudo apt install tesseract-ocr`
- **HuggingFace Token** (free) — [Get one here](https://huggingface.co/settings/tokens)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/car-lease-loan-ai-assistant.git
cd car-lease-loan-ai-assistant

# Create a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```ini
# Required — enables all AI features
HF_TOKEN=your_huggingface_token_here

# Optional — defaults shown below
HF_MODEL=Qwen/Qwen2.5-7B-Instruct
DB_HOST=localhost
DB_PORT=5432
DB_NAME=contractdb
DB_USER=admin
DB_PASS=your_password
```

> Only `HF_TOKEN` is required. The database automatically falls back to SQLite if PostgreSQL isn't available, and the valuation engine uses a built-in depreciation model if no MarketCheck key is set.

### Running the App

You need two terminals:

**Terminal 1 — Start the backend:**
```bash
python backend/main.py
```
The API server starts at `http://localhost:8000`. Swagger docs are at `http://localhost:8000/docs`.

**Terminal 2 — Start the frontend:**
```bash
streamlit run frontend/app_streamlit.py
```
The dashboard opens at `http://localhost:8501`.

### Docker Alternative

If you prefer containers, one command brings up the entire stack:

```bash
docker-compose up --build
```

This starts the FastAPI backend (port 8000), Streamlit frontend (port 8501), PostgreSQL (port 5432), and pgAdmin (port 5050).

---

## How to Use

### Analyzing a Contract

1. Open the dashboard and go to **Contract Analysis** in the sidebar
2. Upload a PDF or image of your car lease or loan agreement
3. Click **Process Document**
4. The AI extracts all key terms, calculates a fairness score, and flags any risks or junk fees
5. Review the results — extracted terms on the left, risks and recommendations on the right

### Generating a Counter-Offer Email

1. After analyzing a contract, click **📧 AI Email Generator & Negotiator**
2. The AI generates a professional counter-offer email with your specific contract data, market comparisons, and target improvements
3. Click **📋 Copy Email to Clipboard** and paste it into your email client

### Comparing Two Contracts

1. Go to **Contract Comparison** in the sidebar
2. Upload Contract A and Contract B
3. Click **Compare Contracts**
4. See side-by-side fairness scores, a clear recommendation, and missing-data insights
5. Generate individual counter-offer emails for either contract
6. Download the hidden fees comparison as a JSON file

### Using the VIN Assistant

1. Go to **VIN Assistant** in the sidebar
2. Enter a 17-character VIN and click **Decode VIN**
3. View full vehicle details (year, make, model, trim, engine, drivetrain) and an estimated market value

### Chatting with the AI

1. Go to **Chatbots** in the sidebar
2. Ask questions like:
   - *"What is my APR and is it fair?"*
   - *"How much total interest will I pay?"*
   - *"Help me negotiate a lower monthly payment"*
   - *"What fees should I ask the dealer to remove?"*
3. The AI responds with specific numbers, strategies, and scripts you can use in real conversations

---

## API Endpoints

### FastAPI Server (port 8000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/signup` | Create user account |
| POST | `/login` | User authentication |
| POST | `/upload` | Upload and auto-analyze a contract |
| POST | `/analyze/{file_id}` | Re-analyze a contract |
| GET | `/contract/{file_id}` | Get contract data |
| POST | `/negotiate/script/{file_id}` | Generate counter-offer email |
| POST | `/negotiate/chat/{file_id}` | Chat with the AI negotiator |
| POST | `/negotiate/counter-offer` | Generate improved terms |
| DELETE | `/contract/{file_id}/clear-cache` | Clear cached analysis |
| GET | `/decode-vin/{vin}` | Decode a VIN via NHTSA |

### Flask Server (port 5000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/market_value` | Get vehicle market value by VIN |
| POST | `/api/chat` | AI chat with session history |
| GET | `/api/chat/history` | Retrieve chat history |
| POST | `/api/chat/clear` | Clear chat history |
| GET | `/api/vin_insights` | VIN market insights and negotiation tips |
| POST | `/api/document/analyze` | Analyze a document with optional prompt |

Full interactive docs are auto-generated at `http://localhost:8000/docs`.

---

## Project Structure

```
car-lease-loan-ai-assistant/
├── backend/
│   ├── main.py                      # FastAPI application with all endpoints
│   ├── config.py                    # Model config and score thresholds
│   ├── ocr.py                       # Tesseract OCR module
│   ├── Dockerfile
│   ├── app/
│   │   ├── api.py                   # Unified API controller
│   │   ├── database.py              # Database connection manager
│   │   ├── negotiation.py           # Chat engine with session history
│   │   ├── ocr.py                   # Advanced OCR with OpenCV preprocessing
│   │   ├── preprocessing.py         # Text cleaning and normalization
│   │   ├── valuation.py             # Market valuation engine
│   │   └── vin_decoder.py           # NHTSA VIN decoder
│   ├── services/
│   │   ├── huggingface_service.py   # HuggingFace API client
│   │   ├── contract_analyzer.py     # AI-powered term extraction
│   │   ├── negotiation_engine.py    # Email generation and chat logic
│   │   ├── pdf_extractor.py         # PDF text extraction
│   │   └── vin_decoder.py           # VIN decode service
│   ├── logic/
│   │   ├── fairness_scorer.py       # Fairness score algorithm
│   │   └── risk_analyzer.py         # Risk and red-flag detection
│   └── prompts/
│       ├── contract_analysis.json   # Contract extraction prompt
│       ├── negotiation_script.json  # Email generation prompt
│       └── risk_detection.json      # Risk analysis prompt
│
├── frontend/
│   ├── index.html                   # Dark-themed chat interface
│   ├── style.css                    # Premium CSS with glassmorphism
│   ├── app.js                       # JavaScript client with chat history
│   ├── app_streamlit.py             # Main Streamlit dashboard
│   ├── app.py                       # Alternate Streamlit UI
│   ├── comparison_chatbot.py        # Contract comparison dashboard
│   └── fairness.html                # Standalone fairness calculator
│
├── infra/
│   ├── docker-compose.yml           # PostgreSQL + pgAdmin
│   ├── init-db.sql                  # Database initialization
│   └── db_schema.sql                # Schema definition
│
├── tests/                           # 36 test files
├── samples/                         # 9 sample contract PDFs
├── data/                            # Uploads and extracted text
├── docs/                            # Development documentation
├── scripts/                         # Smoke test and utilities
├── dealer_message_threading/        # Dealer conversation simulator
│
├── docker-compose.yml               # Full-stack Docker Compose
├── requirements.txt                 # Python dependencies
├── server.py                        # Flask server (VIN + Chat + Document)
├── init_db.py                       # Database initializer
└── .env                             # Environment variables
```

---

## Testing

```bash
# Run the full test suite
python -m pytest tests/ -v

# Run by category
python -m pytest tests/test_ocr.py -v                     # OCR
python -m pytest tests/test_database.py -v                 # Database
python -m pytest tests/test_negotiation.py -v              # Negotiation
python -m pytest tests/test_vin_decoder.py -v              # VIN decoding
python -m pytest tests/comprehensive_system_test.py -v     # Full E2E

# Smoke test
bash scripts/smoke_test.sh
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Tesseract not found" | Install Tesseract OCR and add it to your system PATH. Restart the terminal after installation. |
| "HF_TOKEN not found" | Add your HuggingFace token to the `.env` file. Get a free token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens). |
| Slow first AI response | Normal — models take 20-30 seconds to cold-start. Subsequent calls are much faster. |
| Empty PDF extraction | The PDF may be image-only. Make sure Tesseract is installed for OCR. |
| Database connection error | No action needed — the app automatically falls back to SQLite. |
| Clipboard copy fails | `pyperclip` needs a local display. On remote servers, use the manual copy fallback in the UI. |

---

## Contributing

1. Fork the repository
2. Create a feature branch — `git checkout -b feature/your-feature`
3. Commit your changes — `git commit -m "Add your feature"`
4. Push to the branch — `git push origin feature/your-feature`
5. Open a Pull Request using the included template

---

## License

Developed as part of the **Infosys Springboard Internship Program**.

---

*Stop guessing. Start negotiating.* 🚘
