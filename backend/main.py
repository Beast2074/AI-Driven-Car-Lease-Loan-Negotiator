"""
Car Lease/Loan Contract Review AI Assistant - Production Backend
Unified FastAPI application with comprehensive features:
- Contract Analysis & Fairness Scoring (0-100)
- NHTSA VIN Decoding & Valuation Engine
- Side-by-Side Contract Comparison
- Unified AI Negotiation Chatbot
- Secure Admin-Only Audit Logging
- Vercel, Cloud PostgreSQL & SQLite Ready
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import uuid4
import os
import time
import logging
import psycopg2
import sqlite3
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

from backend.services.pdf_extractor import pdf_extractor
from backend.services.contract_analyzer import contract_analyzer
from backend.logic.fairness_scorer import fairness_scorer
from backend.services.negotiation_engine import negotiation_engine
from backend.services.vin_decoder import vin_decoder
from backend.app.valuation import estimate_fair_price, get_vin_insights
from backend.services.audit_logger import audit_logger, ADMIN_SECRET_KEY
from backend.services.market_data_service import market_data_service

load_dotenv()

# Cloud & Local Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "contractdb")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "manvi123")

import tempfile
BASE_TEMP = tempfile.gettempdir()
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(BASE_TEMP, "uploads"))
TEXT_DIR = os.getenv("TEXT_DIR", os.path.join(BASE_TEMP, "text"))
try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(TEXT_DIR, exist_ok=True)
except Exception:
    pass

app = FastAPI(title="AI Car Lease & Loan Negotiator", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def audit_telemetry_middleware(request: Request, call_next):
    """
    Project-Wide Telemetry Middleware:
    Logs every HTTP transaction with execution timings, status codes, and IP address.
    Securely accessible exclusively by the admin with password '12345'.
    """
    start_time = time.time()
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "unknown")
    path = request.url.path
    method = request.method

    try:
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        
        # Avoid static file noise
        if not path.startswith("/static") and not path.endswith((".ico", ".png", ".jpg", ".svg", ".css", ".js")):
            audit_logger.log_event(
                event_type="HTTP_TRANSACTION",
                details={
                    "method": method,
                    "path": path,
                    "status_code": response.status_code
                },
                status="SUCCESS" if response.status_code < 400 else "ERROR",
                ip_address=client_ip,
                user_agent=user_agent,
                duration_ms=duration_ms
            )
        return response
    except Exception as exc:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        audit_logger.log_event(
            event_type="SYSTEM_EXCEPTION",
            details={
                "method": method,
                "path": path,
                "error": str(exc)
            },
            status="CRITICAL",
            ip_address=client_ip,
            user_agent=user_agent,
            duration_ms=duration_ms
        )
        raise exc

# In-memory storage for active contracts & sessions
uploaded_contracts: Dict[str, Dict[str, Any]] = {}
chat_sessions: Dict[str, List[Dict[str, str]]] = {}

# ============================================================================
# DATABASE UTILITIES (Postgres + SQLite Fallback)
# ============================================================================

_CACHED_DB_TYPE = None

def get_db_connection():
    """Connect to Cloud Postgres (via DATABASE_URL) or fallback to SQLite"""
    global _CACHED_DB_TYPE
    
    # Fast path if SQLite is already selected
    if _CACHED_DB_TYPE == "sqlite":
        sqlite_db = "contract_assistant.db"
        conn = sqlite3.connect(sqlite_db, check_same_thread=False)
        return conn, "sqlite"

    # 1. Try DATABASE_URL (e.g. Neon, Supabase, Vercel Postgres)
    if DATABASE_URL:
        try:
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=2)
            _CACHED_DB_TYPE = "postgresql"
            return conn, "postgresql"
        except Exception:
            pass

    # 2. Try DB_HOST only if DATABASE_URL was provided or explicitly configured
    if os.getenv("DATABASE_URL") or os.getenv("USE_POSTGRES"):
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME,
                connect_timeout=1
            )
            _CACHED_DB_TYPE = "postgresql"
            return conn, "postgresql"
        except Exception:
            pass

    # 3. Automated fast SQLite fallback
    _CACHED_DB_TYPE = "sqlite"
    sqlite_db = os.path.join(BASE_TEMP, "contract_assistant.db")
    conn = sqlite3.connect(sqlite_db, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contracts (
            id TEXT PRIMARY KEY,
            file_path TEXT,
            text_path TEXT,
            extracted_text TEXT,
            analysis_data TEXT,
            fairness_score REAL,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        cols = [c[1] for c in cur.execute('PRAGMA table_info(contracts)').fetchall()]
        if 'analysis_data' not in cols:
            cur.execute('ALTER TABLE contracts ADD COLUMN analysis_data TEXT')
        if 'fairness_score' not in cols:
            cur.execute('ALTER TABLE contracts ADD COLUMN fairness_score REAL')
    except Exception:
        pass
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            details TEXT,
            status TEXT DEFAULT 'SUCCESS',
            duration_ms REAL DEFAULT 0
        )
    """)
    conn.commit()
    return conn, "sqlite"

def save_contract_to_db(file_id: str, file_path: str, text_path: str, extracted_text: str, analysis: dict, score: float):
    try:
        conn, db_type = get_db_connection()
        cur = conn.cursor()
        import json
        analysis_json = json.dumps(analysis)

        if db_type == "postgresql":
            cur.execute("""
                CREATE TABLE IF NOT EXISTS contracts (
                    id TEXT PRIMARY KEY,
                    file_path TEXT,
                    text_path TEXT,
                    extracted_text TEXT,
                    analysis_data TEXT,
                    fairness_score REAL,
                    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                INSERT INTO contracts (id, file_path, text_path, extracted_text, analysis_data, fairness_score, ingested_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    extracted_text = EXCLUDED.extracted_text,
                    analysis_data = EXCLUDED.analysis_data,
                    fairness_score = EXCLUDED.fairness_score
            """, (file_id, file_path, text_path, extracted_text, analysis_json, score))
        else:
            cur.execute("""
                INSERT OR REPLACE INTO contracts (id, file_path, text_path, extracted_text, analysis_data, fairness_score, ingested_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (file_id, file_path, text_path, extracted_text, analysis_json, score))

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database save error (silent fallback): {e}")

# ============================================================================
# DATA MODELS
# ============================================================================

class UnifiedChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    contract_id: Optional[str] = None
    vin: Optional[str] = None

class ContractCompareRequest(BaseModel):
    contract_a_id: Optional[str] = None
    contract_b_id: Optional[str] = None
    contract_a_data: Optional[Dict[str, Any]] = None
    contract_b_data: Optional[Dict[str, Any]] = None

class CounterOfferRequest(BaseModel):
    contract_data: Dict[str, Any]
    target_improvements: List[str]

class AdminVerifyRequest(BaseModel):
    password: Optional[str] = None
    secret_key: Optional[str] = None

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/health")
def health_check():
    _, db_type = get_db_connection()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": db_type,
        "service": "AI Car Lease & Loan Negotiator API"
    }

@app.get("/api/market-benchmarks")
def get_market_benchmarks(force_refresh: bool = False):
    """
    Live US Automotive Financing Benchmark Data.
    Pulls live data from Federal Reserve G.19 Consumer Credit release and U.S. Treasury API.
    """
    return market_data_service.get_benchmarks(force_refresh=force_refresh)

# --- 1. CONTRACT ANALYSIS ---

@app.post("/upload")
async def upload_contract(request: Request, file: UploadFile = File(...)):
    """Upload and analyze a PDF or image contract file."""
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".pdf", ".png", ".jpg", ".jpeg", ".txt"]:
        raise HTTPException(status_code=400, detail="Allowed formats: PDF, PNG, JPG, JPEG, TXT")

    file_id = str(uuid4())
    filename = f"{file_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    content = await file.read()
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as write_err:
        logger.warning(f"File cache write skipped on serverless: {write_err}")

    # Text extraction
    extracted_text = ""
    try:
        if file_ext == ".pdf":
            extracted_text = pdf_extractor.extract_text(content) or ""
        elif file_ext == ".txt":
            extracted_text = content.decode("utf-8", errors="ignore")
        else:
            # Image OCR fallback
            try:
                import pytesseract
                from PIL import Image
                import io
                import platform
                if platform.system() == "Windows":
                    for cand in [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]:
                        if os.path.exists(cand):
                            pytesseract.pytesseract.tesseract_cmd = cand
                            break
                image = Image.open(io.BytesIO(content))
                extracted_text = pytesseract.image_to_string(image)
            except Exception as ocr_err:
                logger.warning(f"Image OCR failed: {ocr_err}")
                extracted_text = ""
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        extracted_text = ""

    if not extracted_text or len(extracted_text.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Unable to extract legible text from this file. Please ensure the document is clear, unscrambled, and not password-protected."
        )

    text_path = os.path.join(TEXT_DIR, f"{file_id}.txt")
    try:
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(extracted_text)
    except Exception as txt_err:
        logger.warning(f"Text cache write skipped on serverless: {txt_err}")

    # Perform Analysis & Scoring
    analysis = contract_analyzer.analyze_contract(extracted_text)
    risks = contract_analyzer.identify_risks(extracted_text)
    fairness = fairness_scorer.calculate_score(analysis)

    uploaded_contracts[file_id] = {
        "file_id": file_id,
        "filename": file.filename,
        "text_raw": extracted_text,
        "analysis": analysis,
        "risks": risks,
        "fairness_score": fairness,
        "uploaded_at": datetime.now().isoformat()
    }

    # Persist to database
    save_contract_to_db(file_id, file_path, text_path, extracted_text, analysis, fairness.get("overall_score", 60))

    duration_ms = round((time.time() - start_time) * 1000, 2)
    audit_logger.log_event(
        event_type="CONTRACT_UPLOAD",
        details={
            "file_id": file_id,
            "filename": file.filename,
            "score": fairness.get("overall_score"),
            "category": fairness.get("category"),
            "monthly_payment": analysis.get("monthly_payment"),
            "apr": analysis.get("interest_rate_apr")
        },
        status="SUCCESS",
        ip_address=client_ip,
        user_agent=user_agent,
        duration_ms=duration_ms
    )

    return {
        "file_id": file_id,
        "filename": file.filename,
        "text_length": len(extracted_text),
        "analysis": analysis,
        "risks": risks,
        "fairness_score": fairness,
        "message": "Contract analyzed successfully"
    }

@app.get("/contract/{file_id}")
@app.post("/analyze/{file_id}")
async def get_contract(file_id: str):
    if file_id in uploaded_contracts:
        return uploaded_contracts[file_id]
    raise HTTPException(status_code=404, detail="Contract not found")

@app.get("/sample-contract/{sample_id}")
async def load_sample_contract(sample_id: str, request: Request):
    """Load pre-configured sample contract for 1-click testing"""
    samples = {
        "bmw": {
            "name": "2024 BMW 330i xDrive Lease",
            "file_name": "bmw-lease-2024.pdf",
            "contract_type": "LEASE",
            "interest_rate_apr": "8.9%",
            "monthly_payment": 620.00,
            "lease_term_months": 36,
            "down_payment": 3500.00,
            "residual_value": "$26,500 (53% MSRP)",
            "mileage_allowance": "10,000 miles/year",
            "mileage_overage_charge": "$0.25/mile",
            "early_termination_clause": "Full balance of remaining payments plus $450 turn-in fee.",
            "purchase_option": "$26,850 ($26,500 Residual + $350 buyout fee)",
            "maintenance_responsibility": "Lessee responsible for all unscheduled repairs and wear items.",
            "warranty_coverage": "3-yr/36,000-mi standard manufacturer warranty included.",
            "insurance_requirements": "Full coverage ($100k/$300k liability, $500 max deductible required).",
            "late_payment_penalty": "5% of monthly payment after 10 days grace period.",
            "total_cost": "$25,820.00",
            "vehicle_info": {"year": 2024, "make": "BMW", "model": "330i xDrive", "vin": "WBASN31010B765432"},
            "hidden_fees": [
                {"name": "Dealer Prep & Inspection", "amount": "$695.00", "is_junk": True},
                {"name": "Nitrogen Tire Fill", "amount": "$199.00", "is_junk": True},
                {"name": "Window VIN Etching", "amount": "$299.00", "is_junk": True},
                {"name": "Acquisition Fee", "amount": "$925.00", "is_junk": False}
            ],
            "summary": "36-month lease for 2024 BMW 330i with inflated 8.9% APR and $1,193 in junk dealer fees."
        },
        "honda": {
            "name": "2024 Honda Accord EX Loan",
            "file_name": "honda-loan-2024.pdf",
            "contract_type": "LOAN",
            "interest_rate_apr": "4.9%",
            "monthly_payment": 440.00,
            "lease_term_months": 60,
            "down_payment": 2000.00,
            "residual_value": "N/A (Purchase Loan)",
            "mileage_allowance": "Unlimited (Ownership)",
            "mileage_overage_charge": "$0.00",
            "early_termination_clause": "No prepayment penalty. Pay off principal at any time.",
            "purchase_option": "Full Ownership upon payoff.",
            "maintenance_responsibility": "Owner responsibility; complimentary 2-year Honda Service Pass included.",
            "warranty_coverage": "3-yr/36,000-mi limited; 5-yr/60,000-mi powertrain warranty.",
            "insurance_requirements": "Comprehensive and collision coverage required during financing.",
            "late_payment_penalty": "$25 or 5% of late installment after 15-day grace period.",
            "total_cost": "$28,400.00",
            "vehicle_info": {"year": 2024, "make": "Honda", "model": "Accord EX", "vin": "1HGCG5655WA036874"},
            "hidden_fees": [
                {"name": "Doc Fee (State Capped)", "amount": "$175.00", "is_junk": False}
            ],
            "summary": "Clean 60-month loan at competitive 4.9% APR with zero dealer markup fees."
        }
    }

    selected = samples.get(sample_id.lower(), samples["bmw"])
    file_id = f"sample-{sample_id}"

    fairness = fairness_scorer.calculate_score(selected)
    risks = {
        "risk_level": "HIGH" if "bmw" in sample_id else "LOW",
        "red_flags": [
            {"issue": "Inflated APR (8.9%)", "severity": "HIGH", "explanation": "Rate exceeds market benchmark of 7.5%."}
        ] if "bmw" in sample_id else [],
        "junk_fees": [f["name"] for f in selected["hidden_fees"] if f.get("is_junk")],
        "unfair_terms": ["High excess mileage penalty ($0.25/mi)"] if "bmw" in sample_id else [],
        "recommendations": [
            "Request removal of $1,193 in dealer prep, nitrogen, and etching fees",
            "Negotiate APR down to 6.5% - 7.0%"
        ] if "bmw" in sample_id else ["Competitive terms; proceed with confidence."]
    }

    uploaded_contracts[file_id] = {
        "file_id": file_id,
        "filename": selected["file_name"],
        "analysis": selected,
        "risks": risks,
        "fairness_score": fairness,
        "uploaded_at": datetime.now().isoformat()
    }

    audit_logger.log_event(
        event_type="SAMPLE_LOAD",
        details={"sample": sample_id, "score": fairness.get("overall_score")},
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    return {
        "file_id": file_id,
        "filename": selected["file_name"],
        "analysis": selected,
        "risks": risks,
        "fairness_score": fairness
    }

# --- 2. VIN ASSISTANT & VALUATION ---

@app.get("/decode-vin/{vin}")
@app.get("/vin/{vin}")
async def decode_vin_endpoint(vin: str, request: Request):
    """Decode VIN via NHTSA, compute fair market value, and generate dealer leverage"""
    start_time = time.time()
    vin_clean = vin.strip().upper()

    if len(vin_clean) != 17:
        raise HTTPException(status_code=400, detail="VIN must be exactly 17 characters.")

    result = vin_decoder.decode_vin(vin_clean)
    if not result.get("success"):
        # Fallback to general NHTSA app decode
        from backend.app.vin_decoder import decode_vin_nhtsa
        res2 = decode_vin_nhtsa(vin_clean)
        if res2.get("success"):
            result = {
                "success": True,
                "vin": vin_clean,
                "make": res2.get("make", "Unknown"),
                "model": res2.get("model", "Vehicle"),
                "year": res2.get("year", 2023),
                "body_class": res2.get("vehicle_type", "Sedan"),
                "trim": res2.get("trim", "Standard"),
                "manufacturer": res2.get("manufacturer", "")
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Unable to decode VIN"))

    year = result.get("year") or 2023
    make = result.get("make") or "Vehicle"
    model = result.get("model") or "Sedan"

    # Compute Fair Price & Market Position
    valuation = estimate_fair_price(year, make, model, mileage=24000, vin=vin_clean)
    if "price" not in valuation and "estimated_price" in valuation:
        valuation["price"] = valuation["estimated_price"]
    insights = get_vin_insights(vin_clean)

    duration_ms = round((time.time() - start_time) * 1000, 2)
    audit_logger.log_event(
        event_type="VIN_LOOKUP",
        details={
            "vin": vin_clean,
            "make": make,
            "model": model,
            "year": year,
            "fair_price": valuation.get("price")
        },
        ip_address=request.client.host if request.client else "127.0.0.1",
        duration_ms=duration_ms
    )

    return {
        "success": True,
        "vehicle_info": result,
        "valuation": valuation,
        "insights": insights
    }

# --- 3. CONTRACT COMPARISON ---

@app.post("/compare")
@app.post("/api/compare")
async def compare_contracts(data: ContractCompareRequest, request: Request):
    """Compare two contracts side-by-side and determine winning deal"""
    doc_a = data.contract_a_data or uploaded_contracts.get(data.contract_a_id or "", {}).get("analysis")
    doc_b = data.contract_b_data or uploaded_contracts.get(data.contract_b_id or "", {}).get("analysis")

    if not doc_a or not doc_b:
        raise HTTPException(status_code=400, detail="Both Contract A and Contract B are required for comparison.")

    score_a = fairness_scorer.calculate_score(doc_a)
    score_b = fairness_scorer.calculate_score(doc_b)

    monthly_a = float(doc_a.get("monthly_payment") or 0)
    monthly_b = float(doc_b.get("monthly_payment") or 0)
    monthly_diff = abs(monthly_a - monthly_b)

    # APR comparison
    def parse_rate(v):
        try:
            return float(str(v).replace('%', '').strip())
        except Exception:
            return 0.0

    rate_a = parse_rate(doc_a.get("interest_rate_apr", 0))
    rate_b = parse_rate(doc_b.get("interest_rate_apr", 0))

    junk_a = len([f for f in doc_a.get("hidden_fees", []) if f.get("is_junk")])
    junk_b = len([f for f in doc_b.get("hidden_fees", []) if f.get("is_junk")])

    score_num_a = score_a.get("overall_score", 0)
    score_num_b = score_b.get("overall_score", 0)

    winner = "A" if score_num_a >= score_num_b else "B"
    score_delta = abs(score_num_a - score_num_b)

    if winner == "A":
        verdict = f"Contract A scores {score_delta} points higher than Contract B. "
        if monthly_a < monthly_b:
            verdict += f"It saves ${monthly_diff:,.2f}/month while charging lower interest."
    else:
        verdict = f"Contract B scores {score_delta} points higher than Contract A. "
        if monthly_b < monthly_a:
            verdict += f"It saves ${monthly_diff:,.2f}/month with fewer junk fees."

    audit_logger.log_event(
        event_type="CONTRACT_COMPARISON",
        details={
            "score_a": score_num_a,
            "score_b": score_num_b,
            "winner": winner
        },
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    return {
        "contract_a": {"data": doc_a, "score": score_a},
        "contract_b": {"data": doc_b, "score": score_b},
        "comparison": {
            "winner": winner,
            "score_delta": score_delta,
            "monthly_diff": round(monthly_diff, 2),
            "apr_diff": round(abs(rate_a - rate_b), 2),
            "junk_fees_diff": abs(junk_a - junk_b),
            "verdict": verdict
        }
    }

# --- 4. UNIFIED AI NEGOTIATION CHATBOT ---

@app.post("/chat")
async def unified_chat(req: UnifiedChatRequest, request: Request):
    """Single unified negotiation chatbot with context awareness"""
    start_time = time.time()
    user_msg = req.message.strip()
    session_id = req.session_id or "default"

    # Gather contract or VIN context if available
    contract_ctx = {}
    if req.contract_id and req.contract_id in uploaded_contracts:
        c = uploaded_contracts[req.contract_id]
        contract_ctx = {
            **c.get("analysis", {}),
            "fairness_score": c.get("fairness_score", {}),
            "risks": c.get("risks", {})
        }

    # Ask negotiation engine
    response_text = negotiation_engine.chat_negotiate(user_msg, contract_ctx)

    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    chat_sessions[session_id].append({"role": "user", "content": user_msg})
    chat_sessions[session_id].append({"role": "assistant", "content": response_text})

    duration_ms = round((time.time() - start_time) * 1000, 2)
    audit_logger.log_event(
        event_type="CHAT_MESSAGE",
        details={"message_len": len(user_msg), "session_id": session_id},
        ip_address=request.client.host if request.client else "127.0.0.1",
        duration_ms=duration_ms
    )

    return {
        "reply": response_text,
        "session_id": session_id,
        "history_count": len(chat_sessions[session_id])
    }

@app.post("/negotiate/script/{file_id}")
async def generate_counter_script(file_id: str, request: Request):
    """Generate negotiation email script for uploaded contract"""
    start_time = time.time()
    if file_id not in uploaded_contracts:
        raise HTTPException(status_code=404, detail="Contract not found")

    c = uploaded_contracts[file_id]
    script = negotiation_engine.generate_negotiation_script(
        c.get("analysis", {}),
        c.get("fairness_score", {})
    )
    duration_ms = round((time.time() - start_time) * 1000, 2)
    client_ip = request.client.host if request.client else "127.0.0.1"
    audit_logger.log_event(
        event_type="COUNTER_OFFER_SCRIPT",
        details={"file_id": file_id, "script_len": len(script)},
        status="SUCCESS",
        ip_address=client_ip,
        duration_ms=duration_ms
    )
    return {"script": script}

# --- 5. PRIVATE ADMIN AUDIT LOGS (SECRET KEY PROTECTED) ---

@app.get("/api/admin/logs")
async def get_admin_logs(
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    admin_key: Optional[str] = Query(None),
    limit: int = 100,
    event_type: Optional[str] = "ALL"
):
    """
    Secure Admin Endpoint: Access full system audit logs.
    Restricted: requires valid ADMIN_SECRET_KEY.
    """
    provided_key = x_admin_key or admin_key
    if not provided_key or provided_key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: Access Denied. Valid Admin Key required.")

    logs = audit_logger.get_logs(limit=limit, event_type=event_type)
    stats = audit_logger.get_stats()

    return {
        "authorized": True,
        "total_records": len(logs),
        "stats": stats,
        "logs": logs
    }

@app.post("/api/admin/verify")
async def verify_admin_key(
    request: Request,
    body: Optional[AdminVerifyRequest] = None,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    admin_key: Optional[str] = Query(None)
):
    provided_key = None
    if body and (body.password or body.secret_key):
        provided_key = body.password or body.secret_key
    if not provided_key:
        provided_key = x_admin_key or admin_key

    client_ip = request.client.host if request.client else "127.0.0.1"
    if provided_key == ADMIN_SECRET_KEY:
        audit_logger.log_event(
            event_type="ADMIN_LOGIN_SUCCESS",
            details={"message": "Admin authorization granted via password"},
            status="SUCCESS",
            ip_address=client_ip
        )
        return {"valid": True, "token": ADMIN_SECRET_KEY, "message": "Admin authorization verified."}

    audit_logger.log_event(
        event_type="ADMIN_LOGIN_FAILED",
        details={"attempted_key": (provided_key[:2] + "***") if provided_key else "EMPTY"},
        status="WARNING",
        ip_address=client_ip
    )
    raise HTTPException(status_code=401, detail="Invalid admin secret key.")

@app.delete("/api/admin/logs/clear")
async def clear_admin_logs(
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    admin_key: Optional[str] = Query(None)
):
    provided_key = x_admin_key or admin_key
    if provided_key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    audit_logger.clear_logs()
    return {"message": "Audit logs cleared successfully."}

# ============================================================================
# SERVE FRONTEND (HTML / CSS / JS / Tailwind)
# ============================================================================

frontend_path = os.path.abspath("frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def serve_index(request: Request):
        client_ip = request.client.host if request.client else "127.0.0.1"
        user_agent = request.headers.get("user-agent", "unknown")
        audit_logger.log_event(
            event_type="PAGE_VIEW",
            details={"path": "/", "referrer": request.headers.get("referer", "direct")},
            status="SUCCESS",
            ip_address=client_ip,
            user_agent=user_agent
        )
        return FileResponse(os.path.join(frontend_path, "index.html"))

    @app.get("/{filename}.html")
    async def serve_html_pages(filename: str, request: Request):
        client_ip = request.client.host if request.client else "127.0.0.1"
        user_agent = request.headers.get("user-agent", "unknown")
        audit_logger.log_event(
            event_type="PAGE_VIEW",
            details={"path": f"/{filename}.html", "referrer": request.headers.get("referer", "direct")},
            status="SUCCESS",
            ip_address=client_ip,
            user_agent=user_agent
        )
        target = os.path.join(frontend_path, f"{filename}.html")
        if os.path.exists(target):
            return FileResponse(target)
        return FileResponse(os.path.join(frontend_path, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
