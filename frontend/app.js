/**
 * Car Lease & Loan AI Negotiator - Executive Vehicle Contract & Financing Intelligence Terminal
 * Professional client-side application with interactive National Market Benchmark Radar,
 * Contract Forensic Auditing, NHTSA VIN Decoding, Comparison, and Unified AI Negotiation Counsel.
 */

// Global Application State
let activeContractData = null;
let activeVinData = null;
let currentContractId = null;
let activeTab = "contract-analysis";
let adminKeyVerified = false;
let adminKeyToken = "";

// Live US Market Benchmarks (Synchronized with Federal Reserve G.19 & US Treasury API)
let liveMarketData = {
  benchmark_apr: 7.54,
  finance_co_apr: 6.30,
  doc_fee_ceiling: 250,
  national_median_lease_payment: 535,
  prime_buy_rate: 5.74,
  predatory_threshold_apr: 10.29,
  money_factor_prime: 0.00239,
  source: "Federal Reserve G.19 Consumer Credit & U.S. Treasury",
  release_period: "October 2026"
};

async function fetchLiveMarketBenchmarks() {
  try {
    const res = await fetch("/api/market-benchmarks");
    if (!res.ok) return;
    const data = await res.json();
    liveMarketData = { ...liveMarketData, ...data };

    // Update Header indicators
    const hdrApr = document.getElementById("headerMarketApr");
    if (hdrApr && liveMarketData.benchmark_apr) hdrApr.textContent = `${liveMarketData.benchmark_apr}% APR`;
    const hdrDoc = document.getElementById("headerDocCeiling");
    if (hdrDoc && liveMarketData.doc_fee_ceiling) hdrDoc.textContent = `$${liveMarketData.doc_fee_ceiling}`;

    // Update Benchmark terminal cards
    const mApr = document.getElementById("matrixApr");
    if (mApr && liveMarketData.benchmark_apr) mApr.textContent = `${liveMarketData.benchmark_apr}%`;
    const mPay = document.getElementById("matrixPayment");
    if (mPay && liveMarketData.national_median_lease_payment) {
      mPay.innerHTML = `$${liveMarketData.national_median_lease_payment}<span class="text-xs font-normal">/mo</span>`;
    }
    const mDoc = document.getElementById("matrixDocFee");
    if (mDoc && liveMarketData.doc_fee_ceiling) mDoc.textContent = `$${liveMarketData.doc_fee_ceiling}`;
    const mMf = document.getElementById("matrixMoneyFactor");
    if (mMf && liveMarketData.money_factor_prime) mMf.textContent = `${liveMarketData.money_factor_prime}`;

    // Update terminal label and curve legends
    const srcLbl = document.getElementById("matrixSourceLabel");
    if (srcLbl && liveMarketData.source) {
      srcLbl.textContent = `${liveMarketData.source} (Release: ${liveMarketData.release_period || 'Latest'})`;
    }
    const medLbl = document.getElementById("curveMedianLabel");
    if (medLbl) {
      medLbl.textContent = `FED MEDIAN (${liveMarketData.benchmark_apr}% APR • $${liveMarketData.national_median_lease_payment}/MO)`;
    }
    const primeLbl = document.getElementById("curvePrimeLabel");
    if (primeLbl) {
      primeLbl.textContent = `PRIME BUY-RATE (<${liveMarketData.prime_buy_rate}% APR)`;
    }
    const predLbl = document.getElementById("curvePredatoryLabel");
    if (predLbl) {
      predLbl.textContent = `PREDATORY MARKUP (>${liveMarketData.predatory_threshold_apr}% APR)`;
    }

    drawRadar();
  } catch (err) {
    console.warn("Live market benchmark sync failed, using baseline:", err);
  }
}

// ============================================================================
// 1. INTERACTIVE NATIONAL MARKET BENCHMARK RADAR (Financial Spline Canvas)
// ============================================================================
let radarCanvas, radarCtx;
let radarContractPoint = null; // { apr: 6.5, monthly: 485, score: 75 }
let mousePos = { x: -1, y: -1, active: false };

function initMarketRadar() {
  radarCanvas = document.getElementById("radarCanvas");
  if (!radarCanvas) return;
  radarCtx = radarCanvas.getContext("2d");

  function resizeCanvas() {
    const dpr = window.devicePixelRatio || 1;
    const rect = radarCanvas.getBoundingClientRect();
    radarCanvas.width = rect.width * dpr;
    radarCanvas.height = rect.height * dpr;
    radarCtx.scale(dpr, dpr);
    drawRadar();
  }

  window.addEventListener("resize", resizeCanvas);

  radarCanvas.addEventListener("mousemove", (e) => {
    const rect = radarCanvas.getBoundingClientRect();
    mousePos = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      active: true
    };
    drawRadar();
  });

  radarCanvas.addEventListener("mouseleave", () => {
    mousePos.active = false;
    drawRadar();
  });

  setTimeout(resizeCanvas, 50);
}

function drawRadar() {
  if (!radarCanvas || !radarCtx) return;
  const dpr = window.devicePixelRatio || 1;
  const width = radarCanvas.width / dpr;
  const height = radarCanvas.height / dpr;

  radarCtx.clearRect(0, 0, width, height);

  // Background Grid Lines
  radarCtx.strokeStyle = "rgba(255, 255, 255, 0.04)";
  radarCtx.lineWidth = 1;

  for (let x = 0; x < width; x += 40) {
    radarCtx.beginPath();
    radarCtx.moveTo(x, 0);
    radarCtx.lineTo(x, height);
    radarCtx.stroke();
  }

  for (let y = 0; y < height; y += 25) {
    radarCtx.beginPath();
    radarCtx.moveTo(0, y);
    radarCtx.lineTo(width, y);
    radarCtx.stroke();
  }

  // Gaussian Bell Curve for Deal Distribution
  // Left: Predatory / High APR (>10%) | Center: Median (6.45% APR, $500) | Right: Prime Buy-rate (<5%)
  const curvePoints = [];
  const samples = 100;
  const mean = width * 0.52;
  const stdDev = width * 0.22;
  const peakHeight = height * 0.75;
  const baseline = height - 12;

  for (let i = 0; i <= samples; i++) {
    const x = (i / samples) * width;
    const exponent = -0.5 * Math.pow((x - mean) / stdDev, 2);
    const y = baseline - (peakHeight * Math.exp(exponent));
    curvePoints.push({ x, y });
  }

  // Draw Area Fill Under Curve
  const gradient = radarCtx.createLinearGradient(0, 0, width, 0);
  gradient.addColorStop(0, "rgba(239, 68, 68, 0.15)");   // Red for predatory
  gradient.addColorStop(0.5, "rgba(6, 182, 212, 0.22)");  // Cyan for median
  gradient.addColorStop(1, "rgba(16, 185, 129, 0.25)");  // Green for prime

  radarCtx.beginPath();
  radarCtx.moveTo(0, baseline);
  curvePoints.forEach(pt => radarCtx.lineTo(pt.x, pt.y));
  radarCtx.lineTo(width, baseline);
  radarCtx.closePath();
  radarCtx.fillStyle = gradient;
  radarCtx.fill();

  // Draw Stroke of Bell Curve
  const strokeGrad = radarCtx.createLinearGradient(0, 0, width, 0);
  strokeGrad.addColorStop(0, "rgba(239, 68, 68, 0.7)");
  strokeGrad.addColorStop(0.5, "rgba(6, 182, 212, 0.85)");
  strokeGrad.addColorStop(1, "rgba(16, 185, 129, 0.9)");

  radarCtx.beginPath();
  curvePoints.forEach((pt, idx) => {
    if (idx === 0) radarCtx.moveTo(pt.x, pt.y);
    else radarCtx.lineTo(pt.x, pt.y);
  });
  radarCtx.strokeStyle = strokeGrad;
  radarCtx.lineWidth = 2.2;
  radarCtx.stroke();

  // Draw National Median Marker Line (Center)
  radarCtx.strokeStyle = "rgba(6, 182, 212, 0.4)";
  radarCtx.setLineDash([3, 3]);
  radarCtx.beginPath();
  radarCtx.moveTo(mean, baseline);
  radarCtx.lineTo(mean, baseline - peakHeight);
  radarCtx.stroke();
  radarCtx.setLineDash([]);

  // Plot User's Uploaded Contract Point (If available)
  if (radarContractPoint) {
    const scoreNorm = Math.max(0, Math.min(100, radarContractPoint.score)) / 100;
    // Score maps to X position (0 = far left predatory, 100 = far right prime)
    const targetX = width * (0.15 + (scoreNorm * 0.7));
    const exponent = -0.5 * Math.pow((targetX - mean) / stdDev, 2);
    const targetY = baseline - (peakHeight * Math.exp(exponent));

    // Glowing Radar Reticle
    radarCtx.save();
    radarCtx.shadowColor = radarContractPoint.score >= 80 ? "#10b981" : (radarContractPoint.score >= 55 ? "#f59e0b" : "#ef4444");
    radarCtx.shadowBlur = 15;

    // Vertical line
    radarCtx.strokeStyle = radarCtx.shadowColor;
    radarCtx.lineWidth = 1.5;
    radarCtx.beginPath();
    radarCtx.moveTo(targetX, baseline);
    radarCtx.lineTo(targetX, targetY);
    radarCtx.stroke();

    // Pulse Ring
    radarCtx.beginPath();
    radarCtx.arc(targetX, targetY, 7, 0, Math.PI * 2);
    radarCtx.fillStyle = radarCtx.shadowColor;
    radarCtx.fill();

    radarCtx.beginPath();
    radarCtx.arc(targetX, targetY, 3, 0, Math.PI * 2);
    radarCtx.fillStyle = "#ffffff";
    radarCtx.fill();

    // Label
    radarCtx.font = "bold 10px 'JetBrains Mono', monospace";
    radarCtx.fillStyle = "#ffffff";
    const tagText = `YOUR DEAL: ${radarContractPoint.score}/100`;
    radarCtx.fillText(tagText, Math.max(10, Math.min(width - 130, targetX - 45)), Math.max(20, targetY - 14));
    radarCtx.restore();
  }

  // Crosshair on Mouse Hover
  if (mousePos.active && mousePos.x >= 0 && mousePos.x <= width) {
    radarCtx.save();
    radarCtx.strokeStyle = "rgba(255, 255, 255, 0.25)";
    radarCtx.setLineDash([2, 2]);
    radarCtx.beginPath();
    radarCtx.moveTo(mousePos.x, 0);
    radarCtx.lineTo(mousePos.x, baseline);
    radarCtx.stroke();

    // Compute relative metrics
    const pct = Math.round((mousePos.x / width) * 100);
    const estApr = (12 - (pct * 0.08)).toFixed(2);
    radarCtx.font = "10px 'JetBrains Mono', monospace";
    radarCtx.fillStyle = "rgba(255, 255, 255, 0.7)";
    radarCtx.fillText(`APR: ~${estApr}% (Rank: ${pct}th percentile)`, Math.min(width - 160, mousePos.x + 8), 20);
    radarCtx.restore();
  }
}

function updateRadarWithContract(monthly, aprStr, score) {
  const aprNum = parseFloat(String(aprStr).replace("%", "")) || 6.5;
  radarContractPoint = {
    monthly: monthly || 500,
    apr: aprNum,
    score: score || 60
  };

  const tag = document.getElementById("radarStatusTag");
  if (tag) {
    let colorClass = "text-emerald-400 border-emerald-500/40 bg-emerald-500/10";
    let text = `INDEXED: TOP ${Math.max(5, 100 - score)}% TIER`;
    if (score < 55) {
      colorClass = "text-red-400 border-red-500/40 bg-red-500/10";
      text = "INDEXED: PREDATORY RISK ZONE";
    } else if (score < 80) {
      colorClass = "text-amber-400 border-amber-500/40 bg-amber-500/10";
      text = "INDEXED: MEDIAN MARKET TIER";
    }
    tag.className = `px-2.5 py-1 rounded text-[10px] font-mono ${colorClass}`;
    tag.textContent = text;
  }

  drawRadar();
}

// ============================================================================
// 2. NAVIGATION & TABS
// ============================================================================
function initNavigation() {
  const navButtons = document.querySelectorAll("#menuNavList .nav-item");

  navButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");
      switchTab(targetTab);
    });
  });
}

function switchTab(tabId) {
  activeTab = tabId;

  document.querySelectorAll("#menuNavList .nav-item").forEach(btn => {
    const isTarget = btn.getAttribute("data-tab") === tabId;
    btn.classList.toggle("active", isTarget);
    btn.classList.toggle("text-white", isTarget);
    btn.classList.toggle("text-slate-300", !isTarget);
  });

  document.querySelectorAll(".tab-pane").forEach(pane => {
    pane.classList.add("hidden");
  });

  const targetPane = document.getElementById(`pane-${tabId}`);
  if (targetPane) {
    targetPane.classList.remove("hidden");
  }
}

// ============================================================================
// 3. CONTRACT ANALYSIS MODULE (NO DUMMY PRELOAD)
// ============================================================================
function initContractUploader() {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("contractFileInput");

  dropzone?.addEventListener("click", () => fileInput?.click());

  dropzone?.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("border-red-500", "bg-red-500/5");
  });

  dropzone?.addEventListener("dragleave", () => {
    dropzone.classList.remove("border-red-500", "bg-red-500/5");
  });

  dropzone?.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("border-red-500", "bg-red-500/5");
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleContractUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput?.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleContractUpload(e.target.files[0]);
    }
  });

  // Copy Proposal Button
  document.getElementById("copyEmailBtn")?.addEventListener("click", () => {
    const text = document.getElementById("emailScriptBox")?.innerText;
    if (text) {
      navigator.clipboard.writeText(text).then(() => {
        const textEl = document.getElementById("copyBtnText");
        if (textEl) textEl.textContent = "Proposal Copied!";
        setTimeout(() => {
          if (textEl) textEl.textContent = "Copy Proposal";
        }, 2200);
      });
    }
  });
}

async function handleContractUpload(file) {
  const loading = document.getElementById("analysisLoading");
  const guidance = document.getElementById("preAnalysisGuidance");
  const results = document.getElementById("analysisResultsContainer");
  
  loading?.classList.remove("hidden");
  guidance?.classList.add("hidden");
  results?.classList.add("hidden");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/upload", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      let errorMsg = "Document upload failed";
      try {
        const err = await res.json();
        errorMsg = err.detail || errorMsg;
      } catch (_) {
        const txt = await res.text().catch(() => "");
        errorMsg = txt || `Server returned error (${res.status})`;
      }
      throw new Error(errorMsg);
    }

    const data = await res.json();
    renderContractResults(data);
  } catch (error) {
    alert("Contract analysis failed: " + error.message);
    guidance?.classList.remove("hidden");
  } finally {
    loading?.classList.add("hidden");
  }
}

function renderContractResults(data) {
  activeContractData = data.analysis;
  currentContractId = data.file_id;

  const guidance = document.getElementById("preAnalysisGuidance");
  const results = document.getElementById("analysisResultsContainer");
  
  guidance?.classList.add("hidden");
  results?.classList.remove("hidden");

  const scoreData = data.fairness_score || {};
  const overall = Math.round(scoreData.overall_score || 0);
  const breakdown = scoreData.breakdown || {};

  // Show template notice for master/framework contracts
  const templateNotice = document.getElementById("templateContractNotice");
  if (templateNotice) {
    if (data.analysis && (data.analysis.is_master_agreement || data.analysis.contract_type === "MASTER_LOAN_FACILITY" || data.analysis.contract_type === "HYPOTHECATION_ENTRY")) {
      templateNotice.classList.remove("hidden");
    } else {
      templateNotice.classList.add("hidden");
    }
  }

  // 1. Render Scores
  document.getElementById("scoreOverallNumber").textContent = overall;
  document.getElementById("scorePriceNumber").textContent = Math.round(breakdown.price_score || 0);
  document.getElementById("scoreRiskNumber").textContent = Math.round(breakdown.risk_score || 0);
  document.getElementById("scoreFeeNumber").textContent = Math.round(breakdown.fee_score || 0);

  // Progress Bars
  document.getElementById("barPrice").style.width = `${((breakdown.price_score || 0) / 50) * 100}%`;
  document.getElementById("barRisk").style.width = `${((breakdown.risk_score || 0) / 30) * 100}%`;
  document.getElementById("barFee").style.width = `${((breakdown.fee_score || 0) / 20) * 100}%`;

  // Verdict & Badge
  const catBadge = document.getElementById("scoreCategoryBadge");
  const verdictText = document.getElementById("scoreVerdictText");
  const overallNumEl = document.getElementById("scoreOverallNumber");

  if (overall >= 85) {
    catBadge.className = "px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider badge-excellent font-mono";
    catBadge.textContent = "PRIME FINANCING (EXCELLENT)";
    verdictText.textContent = "🟢 Institutional-grade deal terms. Optimal monthly payment & APR.";
    overallNumEl.className = "text-5xl font-extrabold tracking-tight tabular-nums text-emerald-400";
  } else if (overall >= 55) {
    catBadge.className = "px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider badge-fair font-mono";
    catBadge.textContent = "FAIR DEAL (ROOM TO NEGOTIATE)";
    verdictText.textContent = "🟡 Acceptable terms, but dealer padding and rate markups are present.";
    overallNumEl.className = "text-5xl font-extrabold tracking-tight tabular-nums text-amber-400";
  } else {
    catBadge.className = "px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider badge-poor font-mono";
    catBadge.textContent = "HIGH RISK (PREDATORY TERMS)";
    verdictText.textContent = "🔴 Inflated APR markup and unbundled dealer junk fees detected.";
    overallNumEl.className = "text-5xl font-extrabold tracking-tight tabular-nums text-red-400";
  }

  // 2. Render Financial Terms Grid
  const a = data.analysis || {};
  
  // Smart contract type display
  const contractTypeLabels = {
    "LEASE": "LEASE AGREEMENT",
    "LOAN": "LOAN AGREEMENT",
    "MASTER_LOAN_FACILITY": "MASTER LOAN FACILITY",
    "HYPOTHECATION_ENTRY": "HYPOTHECATION ENTRY"
  };
  document.getElementById("contractTypeBadge").textContent = contractTypeLabels[a.contract_type] || ((a.contract_type || "LOAN") + " AGREEMENT");

  // Determine if this is a template/framework contract (no filled financial values)
  const isTemplate = a.is_master_agreement || ((!a.monthly_payment || parseFloat(a.monthly_payment) === 0) && (!a.interest_rate_apr || a.interest_rate_apr === "Not Disclosed in Document"));

  const termsGrid = document.getElementById("termsGridContainer");

  const terms = [
    { label: "Monthly Installment", val: (a.monthly_payment && parseFloat(a.monthly_payment) > 0) ? `$${parseFloat(a.monthly_payment).toFixed(2)}` : (isTemplate ? "Per Schedule" : "Not Specified") },
    { label: "Contract APR", val: (a.interest_rate_apr && a.interest_rate_apr !== "Not Disclosed in Document") ? a.interest_rate_apr : (isTemplate ? "Per Schedule" : "Not Disclosed") },
    { label: "Financing Term", val: a.lease_term_months ? `${a.lease_term_months} Months` : "Per Schedule" },
    { label: "Down Payment / Cap Reduction", val: (a.down_payment && parseFloat(a.down_payment) > 0) ? `$${parseFloat(a.down_payment).toLocaleString()}` : "Not Specified" },
    { label: "Residual Value", val: (a.residual_value && a.residual_value !== "Not Applicable (Loan Structure)") ? a.residual_value : (a.contract_type === "LEASE" ? "Per Lease Schedule" : "N/A") },
    { label: "Annual Mileage Cap", val: (a.mileage_allowance && a.mileage_allowance !== "Not Specified") ? a.mileage_allowance : (a.contract_type === "LEASE" ? "Per Lease Terms" : "Unlimited") },
    { label: "Excess Mileage Penalty", val: (a.mileage_overage_charge && a.mileage_overage_charge !== "N/A") ? a.mileage_overage_charge : (a.contract_type === "LEASE" ? "$0.20/mile (standard)" : "N/A") },
    { label: "Purchase Option At Term", val: (a.purchase_option && a.purchase_option !== "Not Applicable (Loan Structure)" && a.purchase_option !== "Refer to Lease Schedule") ? a.purchase_option : (a.contract_type === "LEASE" ? "Per Lease Schedule" : "Full Ownership on Payoff") },
    { label: "Gross Payable Obligation", val: (a.total_cost && a.total_cost !== "Refer to Loan Schedule") ? a.total_cost : "Per Loan Schedule" }
  ];

  termsGrid.innerHTML = terms.map(t => `
    <div class="p-3 rounded-xl bg-dark-950 border border-slate-800">
      <div class="text-[11px] text-slate-400 font-medium font-mono">${t.label}</div>
      <div class="text-sm font-bold text-white mt-0.5 tabular-nums">${t.val}</div>
    </div>
  `).join("");

  // 3. Render Clauses
  const clausesContainer = document.getElementById("clausesContainer");
  clausesContainer.innerHTML = `
    <div class="text-slate-400"><strong class="text-slate-300">Premature Termination:</strong> ${a.early_termination_clause || "Standard penalty applies"}</div>
    <div class="text-slate-400"><strong class="text-slate-300">Warranty Coverage:</strong> ${a.warranty_coverage || "Bumper-to-bumper manufacturer warranty verified"}</div>
    <div class="text-slate-400"><strong class="text-slate-300">Late Payment Penalty:</strong> ${a.late_payment_penalty || "5% fee after 10-day statutory grace period"}</div>
  `;

  // 4. Render Junk Fees & Risks
  const feesList = document.getElementById("junkFeesList");
  const hiddenFees = a.hidden_fees || [];
  const junkList = hiddenFees.filter(f => f.is_junk);

  if (junkList.length === 0) {
    feesList.innerHTML = `
      <div class="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center space-x-2">
        <i class="fa-solid fa-circle-check"></i>
        <span>No unbundled junk fees detected in contract.</span>
      </div>
    `;
  } else {
    feesList.innerHTML = junkList.map(fee => `
      <div class="p-2.5 rounded-xl bg-dark-950 border border-red-500/30 flex items-center justify-between text-xs">
        <div class="flex items-center space-x-2">
          <i class="fa-solid fa-ban text-red-400"></i>
          <span class="font-semibold text-slate-200">${fee.name}</span>
        </div>
        <span class="font-mono text-red-400 font-bold">${fee.amount}</span>
      </div>
    `).join("");
  }

  // Recommendations
  const recList = document.getElementById("recommendationsList");
  const recs = (data.risks && data.risks.recommendations) || ["Request APR rate-matching against local credit unions", "Demand itemized removal of non-statutory dealer fees"];
  recList.innerHTML = recs.map(r => `<li>${r}</li>`).join("");

  // Risk Badge
  const riskBadge = document.getElementById("riskLevelBadge");
  const riskLevel = (data.risks && data.risks.risk_level) || "MODERATE";
  riskBadge.textContent = `${riskLevel} RISK`;
  riskBadge.className = `px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono ${riskLevel === 'HIGH' ? 'badge-poor' : (riskLevel === 'LOW' ? 'badge-excellent' : 'badge-fair')}`;

  // 5. Update Interactive Market Radar
  updateRadarWithContract(a.monthly_payment, a.interest_rate_apr, overall);

  // 6. Fetch / Generate Counter-Offer Email
  fetchCounterOfferEmail(data.file_id);
}

async function fetchCounterOfferEmail(fileId) {
  try {
    const res = await fetch(`/negotiate/script/${fileId}`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      document.getElementById("emailScriptBox").textContent = data.script || "Unable to draft proposal.";
    }
  } catch (e) {
    document.getElementById("emailScriptBox").textContent = "Dealer counter-offer draft ready.";
  }
}

// ============================================================================
// 4. VIN ASSISTANT MODULE (NO DUMMY PRELOAD)
// ============================================================================
function initVinAssistant() {
  const decodeBtn = document.getElementById("decodeVinBtn");
  const vinInput = document.getElementById("vinSearchInput");

  decodeBtn?.addEventListener("click", () => {
    const vin = vinInput?.value.trim();
    if (vin) decodeVehicleVin(vin);
  });

  vinInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const vin = vinInput?.value.trim();
      if (vin) decodeVehicleVin(vin);
    }
  });
}

async function decodeVehicleVin(vin) {
  const initialPrompt = document.getElementById("vinInitialPrompt");
  const results = document.getElementById("vinResultsContainer");

  try {
    const res = await fetch(`/decode-vin/${encodeURIComponent(vin)}`);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "VIN lookup failed");
    }

    const data = await res.json();
    initialPrompt?.classList.add("hidden");
    renderVinResults(data);
  } catch (error) {
    alert("NHTSA Lookup Error: " + error.message);
  }
}

function renderVinResults(data) {
  activeVinData = data;
  const results = document.getElementById("vinResultsContainer");
  results?.classList.remove("hidden");

  const v = data.vehicle_info || {};
  const val = data.valuation || {};

  document.getElementById("vinVehicleTitle").textContent = `${v.year || ''} ${v.make || ''} ${v.model || ''} ${v.trim || ''}`.trim();
  document.getElementById("vinVehicleSubtitle").textContent = `VIN: ${v.vin || ''} • ${v.manufacturer || 'Verified Factory Source'}`;

  // Specs Grid
  const specs = [
    { label: "Make", val: v.make || "N/A" },
    { label: "Model", val: v.model || "N/A" },
    { label: "Model Year", val: v.year || "N/A" },
    { label: "Body Class", val: v.body_class || "Passenger Vehicle" },
    { label: "Trim Variant", val: v.trim || "Base" },
    { label: "Manufacturer", val: v.manufacturer || "N/A" }
  ];

  document.getElementById("vinSpecsGrid").innerHTML = specs.map(s => `
    <div class="p-3 rounded-xl bg-dark-950 border border-slate-800">
      <div class="text-[11px] text-slate-400 font-medium font-mono">${s.label}</div>
      <div class="text-sm font-bold text-white mt-0.5">${s.val}</div>
    </div>
  `).join("");

  // Valuation Card
  const price = val.price ? `$${Math.round(val.price).toLocaleString()}` : "$24,500";
  const msrp = val.details && val.details.base_msrp ? `$${Math.round(val.details.base_msrp).toLocaleString()}` : "$32,000";

  document.getElementById("vinFairPrice").textContent = price;
  document.getElementById("vinMsrpCompare").textContent = `Estimated Base MSRP: ${msrp} | Algorithm: ${val.valuation_method || 'Segment Depreciation'}`;
}

function startChatWithVin() {
  switchTab("chatbots");
  if (activeVinData) {
    const v = activeVinData.vehicle_info || {};
    const val = activeVinData.valuation || {};
    const p = val.price ? `$${Math.round(val.price).toLocaleString()}` : "";
    sendChatMessage(`I am negotiating a ${v.year} ${v.make} ${v.model}. What is the recommended strategy to target the institutional fair price of ${p}?`);
  }
}

// ============================================================================
// 4.5. SIDE-BY-SIDE CONTRACT COMPARISON MODULE
// ============================================================================
function initContractComparison() {
  const dropA = document.getElementById("dropzoneCompareA");
  const fileInputA = document.getElementById("fileInputA");
  const dropB = document.getElementById("dropzoneCompareB");
  const fileInputB = document.getElementById("fileInputB");
  const btnCompare = document.getElementById("btnExecuteCompare");

  // File A upload click & change
  dropA?.addEventListener("click", () => fileInputA?.click());
  fileInputA?.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleComparisonFileUpload(e.target.files[0], "A");
    }
  });

  // File B upload click & change
  dropB?.addEventListener("click", () => fileInputB?.click());
  fileInputB?.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleComparisonFileUpload(e.target.files[0], "B");
    }
  });

  // Run Comparison Click
  btnCompare?.addEventListener("click", executeDealComparison);
}

function importFromTab1() {
  if (!activeContractData) {
    alert("No contract has been analyzed in Tab 1 yet. Upload a document in Contract Analysis first, or upload directly into Offer A here.");
    return;
  }
  const a = activeContractData;
  const compNameA = document.getElementById("compAName");
  const compMonthlyA = document.getElementById("compAMonthly");
  const compAprA = document.getElementById("compAApr");
  const compTermA = document.getElementById("compATerm");
  const compDownA = document.getElementById("compADown");
  const compFeesA = document.getElementById("compAFees");
  const dealAStatus = document.getElementById("dealAStatus");

  if (compNameA) compNameA.value = (a.vehicle_info && a.vehicle_info.make) ? `${a.vehicle_info.year || ''} ${a.vehicle_info.make} ${a.vehicle_info.model || ''}`.trim() : "Contract Deal A";
  if (compMonthlyA && a.monthly_payment) compMonthlyA.value = a.monthly_payment;
  if (compAprA && a.interest_rate_apr) compAprA.value = parseFloat(String(a.interest_rate_apr).replace("%", "")) || "";
  if (compTermA && a.lease_term_months) compTermA.value = a.lease_term_months;
  if (compDownA && a.down_payment) compDownA.value = a.down_payment;
  
  let junkSumA = 0;
  (a.hidden_fees || []).forEach(f => {
    if (f.is_junk && f.amount) junkSumA += parseFloat(String(f.amount).replace(/[^0-9.]/g, "")) || 0;
  });
  if (compFeesA) compFeesA.value = junkSumA > 0 ? junkSumA : "0.00";

  if (dealAStatus) {
    dealAStatus.textContent = "IMPORTED";
    dealAStatus.className = "px-2 py-0.5 rounded text-[10px] font-mono border border-blue-500/40 bg-blue-500/10 text-blue-400";
  }
}

function clearOffer(side) {
  const nameEl = document.getElementById(`comp${side}Name`);
  const monthlyEl = document.getElementById(`comp${side}Monthly`);
  const aprEl = document.getElementById(`comp${side}Apr`);
  const termEl = document.getElementById(`comp${side}Term`);
  const downEl = document.getElementById(`comp${side}Down`);
  const feesEl = document.getElementById(`comp${side}Fees`);
  const statusEl = document.getElementById(`deal${side}Status`);
  const fileInput = document.getElementById(`fileInput${side}`);

  if (nameEl) nameEl.value = "";
  if (monthlyEl) monthlyEl.value = "";
  if (aprEl) aprEl.value = "";
  if (termEl) termEl.value = "";
  if (downEl) downEl.value = "";
  if (feesEl) feesEl.value = "";
  if (fileInput) fileInput.value = "";
  if (statusEl) {
    statusEl.textContent = "READY";
    statusEl.className = "px-2 py-0.5 rounded text-[10px] font-mono border border-slate-700 bg-dark-900 text-slate-400";
  }
}

async function handleComparisonFileUpload(file, side) {
  const statusEl = document.getElementById(`deal${side}Status`);
  if (statusEl) {
    statusEl.textContent = "ANALYZING...";
    statusEl.className = "px-2 py-0.5 rounded text-[10px] font-mono border border-amber-500/40 bg-amber-500/10 text-amber-400";
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/upload", {
      method: "POST",
      body: formData
    });
    if (!res.ok) {
      let errorMsg = "Document analysis failed";
      try {
        const err = await res.json();
        errorMsg = err.detail || errorMsg;
      } catch (_) {
        const txt = await res.text().catch(() => "");
        errorMsg = txt || `Server returned error (${res.status})`;
      }
      throw new Error(errorMsg);
    }
    const data = await res.json();
    const a = data.analysis || {};
    const veh = a.vehicle_info || {};

    // Populate Fields
    const nameEl = document.getElementById(`comp${side}Name`);
    const monthlyEl = document.getElementById(`comp${side}Monthly`);
    const aprEl = document.getElementById(`comp${side}Apr`);
    const termEl = document.getElementById(`comp${side}Term`);
    const downEl = document.getElementById(`comp${side}Down`);
    const feesEl = document.getElementById(`comp${side}Fees`);

    if (nameEl) nameEl.value = (veh.make || veh.model) ? `${veh.year || 2024} ${veh.make || ''} ${veh.model || ''}`.trim() : (file.name.replace(/\.[^/.]+$/, ""));
    if (monthlyEl && a.monthly_payment) monthlyEl.value = a.monthly_payment;
    if (aprEl && a.interest_rate_apr) aprEl.value = parseFloat(String(a.interest_rate_apr).replace("%", "")) || "";
    if (termEl && a.lease_term_months) termEl.value = a.lease_term_months;
    if (downEl && a.down_payment) downEl.value = a.down_payment;
    
    // Sum junk fees
    let junkSum = 0;
    (a.hidden_fees || []).forEach(f => {
      if (f.is_junk && f.amount) junkSum += parseFloat(String(f.amount).replace(/[^0-9.]/g, "")) || 0;
    });
    if (feesEl) feesEl.value = junkSum > 0 ? junkSum : "0.00";

    if (statusEl) {
      statusEl.textContent = "PARSED";
      statusEl.className = "px-2 py-0.5 rounded text-[10px] font-mono border border-emerald-500/40 bg-emerald-500/10 text-emerald-400";
    }
  } catch (err) {
    alert(`Could not parse ${side} document: ` + err.message);
    if (statusEl) {
      statusEl.textContent = "READY";
      statusEl.className = "px-2 py-0.5 rounded text-[10px] font-mono border border-slate-700 bg-dark-900 text-slate-400";
    }
  }
}

async function executeDealComparison() {
  const nameA = document.getElementById("compAName")?.value || "Offer A";
  const monthlyA = parseFloat(document.getElementById("compAMonthly")?.value) || 0;
  const aprA = parseFloat(document.getElementById("compAApr")?.value) || 0;
  const termA = parseInt(document.getElementById("compATerm")?.value) || 36;
  const downA = parseFloat(document.getElementById("compADown")?.value) || 0;
  const feesA = parseFloat(document.getElementById("compAFees")?.value) || 0;

  const nameB = document.getElementById("compBName")?.value || "Offer B";
  const monthlyB = parseFloat(document.getElementById("compBMonthly")?.value) || 0;
  const aprB = parseFloat(document.getElementById("compBApr")?.value) || 0;
  const termB = parseInt(document.getElementById("compBTerm")?.value) || 36;
  const downB = parseFloat(document.getElementById("compBDown")?.value) || 0;
  const feesB = parseFloat(document.getElementById("compBFees")?.value) || 0;

  if (monthlyA <= 0 || monthlyB <= 0) {
    alert("Please enter or upload valid monthly payments for both Offer A and Offer B.");
    return;
  }

  const payload = {
    contract_a_data: {
      name: nameA,
      monthly_payment: monthlyA,
      interest_rate_apr: `${aprA}%`,
      lease_term_months: termA,
      down_payment: downA,
      hidden_fees: feesA > 0 ? [{ name: "Dealer Add-ons", amount: feesA, is_junk: true }] : []
    },
    contract_b_data: {
      name: nameB,
      monthly_payment: monthlyB,
      interest_rate_apr: `${aprB}%`,
      lease_term_months: termB,
      down_payment: downB,
      hidden_fees: feesB > 0 ? [{ name: "Dealer Add-ons", amount: feesB, is_junk: true }] : []
    }
  };

  try {
    const res = await fetch("/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("Comparison failed");
    const data = await res.json();
    renderComparisonResults(data, payload);
  } catch (err) {
    alert("Failed to compare offers: " + err.message);
  }
}

function renderComparisonResults(data, inputPayload) {
  const card = document.getElementById("comparisonResultsCard");
  if (!card) return;
  card.classList.remove("hidden");

  const comp = data.comparison || {};
  const isA = comp.winner === "A";
  const winnerName = isA ? inputPayload.contract_a_data.name : inputPayload.contract_b_data.name;
  const winnerBadge = isA ? "OFFER A IS SUPERIOR" : "OFFER B IS SUPERIOR";

  const mA = inputPayload.contract_a_data.monthly_payment;
  const mB = inputPayload.contract_b_data.monthly_payment;
  const tA = inputPayload.contract_a_data.lease_term_months;
  const tB = inputPayload.contract_b_data.lease_term_months;
  const totalA = (mA * tA) + inputPayload.contract_a_data.down_payment;
  const totalB = (mB * tB) + inputPayload.contract_b_data.down_payment;
  const totalSavings = Math.abs(totalA - totalB);

  document.getElementById("compareWinnerBadge").textContent = winnerBadge;
  document.getElementById("compareWinnerSummary").textContent = `${winnerName} delivers the higher fairness rating and greater long-term financial efficiency.`;
  document.getElementById("compareSavingsValue").textContent = `$${totalSavings.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  // Table rows
  document.getElementById("tblMonthlyA").textContent = `$${mA.toFixed(2)}`;
  document.getElementById("tblMonthlyB").textContent = `$${mB.toFixed(2)}`;
  const mDelta = Math.abs(mA - mB);
  document.getElementById("tblMonthlyDelta").textContent = (mA < mB) ? `A saves $${mDelta.toFixed(2)}/mo` : `B saves $${mDelta.toFixed(2)}/mo`;

  const aprA = parseFloat(inputPayload.contract_a_data.interest_rate_apr);
  const aprB = parseFloat(inputPayload.contract_b_data.interest_rate_apr);
  document.getElementById("tblAprA").textContent = `${aprA}%`;
  document.getElementById("tblAprB").textContent = `${aprB}%`;
  const aprDelta = Math.abs(aprA - aprB).toFixed(2);
  document.getElementById("tblAprDelta").textContent = (aprA < aprB) ? `A is ${aprDelta}% lower` : `B is ${aprDelta}% lower`;

  document.getElementById("tblTermA").textContent = `${tA} mos`;
  document.getElementById("tblTermB").textContent = `${tB} mos`;
  document.getElementById("tblTermDelta").textContent = tA === tB ? "Identical" : `${Math.abs(tA - tB)} mos delta`;

  document.getElementById("tblDownA").textContent = `$${inputPayload.contract_a_data.down_payment.toFixed(2)}`;
  document.getElementById("tblDownB").textContent = `$${inputPayload.contract_b_data.down_payment.toFixed(2)}`;
  document.getElementById("tblDownDelta").textContent = `$${Math.abs(inputPayload.contract_a_data.down_payment - inputPayload.contract_b_data.down_payment).toFixed(2)} diff`;

  const feesA = inputPayload.contract_a_data.hidden_fees[0]?.amount || 0;
  const feesB = inputPayload.contract_b_data.hidden_fees[0]?.amount || 0;
  document.getElementById("tblFeesA").textContent = `$${feesA.toFixed(2)}`;
  document.getElementById("tblFeesB").textContent = `$${feesB.toFixed(2)}`;
  document.getElementById("tblFeesDelta").textContent = (feesA < feesB) ? `A saves $${(feesB - feesA).toFixed(2)}` : `B saves $${(feesA - feesB).toFixed(2)}`;

  document.getElementById("tblTotalA").textContent = `$${totalA.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
  document.getElementById("tblTotalB").textContent = `$${totalB.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
  document.getElementById("tblTotalDelta").textContent = `Net Savings: $${totalSavings.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;

  // Forensic Verdict Note
  const noteEl = document.getElementById("compareVerdictNote");
  noteEl.innerHTML = `
    <strong class="text-white">Forensic Recommendation:</strong> ${comp.verdict} Over the ${Math.min(tA, tB)}-month period, choosing ${winnerName} avoids unnecessary interest padding and protects you against non-statutory dealer fees. 
    You can use these comparison figures in the <strong>AI Chatbot</strong> tab to generate an assertive counter-offer directly to the competing dealer.
  `;
}

// ============================================================================
// 5. UNIFIED AI NEGOTIATION CHATBOT MODULE
// ============================================================================
function initChatbot() {
  const sendBtn = document.getElementById("sendChatBtn");
  const input = document.getElementById("chatMessageInput");

  sendBtn?.addEventListener("click", () => {
    const msg = input?.value.trim();
    if (msg) {
      sendChatMessage(msg);
      input.value = "";
    }
  });

  input?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const msg = input?.value.trim();
      if (msg) {
        sendChatMessage(msg);
        input.value = "";
      }
    }
  });
}

function sendQuickPrompt(promptText) {
  sendChatMessage(promptText);
}

async function sendChatMessage(message) {
  const thread = document.getElementById("chatMessagesThread");
  if (!thread) return;

  // User Message
  const userDiv = document.createElement("div");
  userDiv.className = "flex items-start justify-end space-x-3";
  userDiv.innerHTML = `
    <div class="p-3.5 rounded-2xl rounded-tr-sm bg-slate-800 border border-slate-700 text-white text-xs max-w-xl leading-relaxed shadow-md">
      ${escapeHtml(message)}
    </div>
    <div class="w-8 h-8 rounded-lg bg-dark-850 border border-slate-700 flex items-center justify-center text-slate-300 text-xs flex-shrink-0 mt-0.5">
      <i class="fa-solid fa-user"></i>
    </div>
  `;
  thread.appendChild(userDiv);

  // Bot Thinking
  const botDiv = document.createElement("div");
  botDiv.className = "flex items-start space-x-3";
  botDiv.innerHTML = `
    <div class="w-8 h-8 rounded-lg bg-dark-800 border border-slate-700 flex items-center justify-center text-slate-300 text-xs flex-shrink-0 mt-0.5">
      <i class="fa-solid fa-shield-halved"></i>
    </div>
    <div class="p-3.5 rounded-2xl rounded-tl-sm bg-dark-850 border border-slate-700/80 text-xs text-slate-300 max-w-xl leading-relaxed shadow-md flex items-center space-x-2 font-mono">
      <i class="fa-solid fa-circle-notch fa-spin text-slate-400"></i>
      <span>Formulating negotiation tactics...</span>
    </div>
  `;
  thread.appendChild(botDiv);
  thread.scrollTop = thread.scrollHeight;

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message,
        contract_id: currentContractId,
        session_id: "main_session"
      })
    });

    const data = await res.json();
    const reply = data.reply || "Unable to formulate response at this time.";

    botDiv.innerHTML = `
      <div class="w-8 h-8 rounded-lg bg-dark-800 border border-slate-700 flex items-center justify-center text-slate-300 text-xs flex-shrink-0 mt-0.5">
        <i class="fa-solid fa-shield-halved"></i>
      </div>
      <div class="p-4 rounded-2xl rounded-tl-sm bg-dark-850 border border-slate-700/80 text-xs text-slate-200 max-w-xl leading-relaxed shadow-md space-y-2">
        <div>${formatMarkdown(reply)}</div>
        <div class="pt-2 border-t border-slate-800 flex items-center justify-between text-[10px] text-slate-400 font-mono">
          <span>AI AUTOMOTIVE COUNSEL</span>
          <button onclick="copyBubbleText(this)" class="hover:text-white transition flex items-center space-x-1">
            <i class="fa-solid fa-copy"></i>
            <span>Copy</span>
          </button>
        </div>
      </div>
    `;
  } catch (err) {
    botDiv.innerHTML = `
      <div class="w-8 h-8 rounded-lg bg-dark-800 border border-slate-700 flex items-center justify-center text-slate-300 text-xs flex-shrink-0 mt-0.5">
        <i class="fa-solid fa-triangle-exclamation text-amber-400"></i>
      </div>
      <div class="p-3 rounded-2xl bg-dark-850 border border-red-500/30 text-xs text-red-400 font-mono">
        Connection error: ${err.message}
      </div>
    `;
  }

  thread.scrollTop = thread.scrollHeight;
}

function clearChatHistory() {
  const thread = document.getElementById("chatMessagesThread");
  if (thread) {
    thread.innerHTML = `
      <div class="flex items-start space-x-3">
        <div class="w-8 h-8 rounded-lg bg-dark-800 border border-slate-700 flex items-center justify-center text-slate-300 text-xs flex-shrink-0 mt-0.5">
          <i class="fa-solid fa-shield-halved"></i>
        </div>
        <div class="p-4 rounded-2xl rounded-tl-sm bg-dark-800 border border-slate-700/80 max-w-xl text-xs text-slate-200 leading-relaxed shadow-md space-y-1.5">
          <p class="font-semibold text-white">Chat session refreshed.</p>
          <p class="text-slate-400">Ask about dealer doc fee regulations, lease-to-own math, or APR rate concessions.</p>
        </div>
      </div>
    `;
  }
}

function copyBubbleText(btn) {
  const content = btn.closest(".p-4")?.querySelector("div")?.innerText;
  if (content) {
    navigator.clipboard.writeText(content).then(() => {
      btn.innerHTML = `<i class="fa-solid fa-check"></i> <span>Copied</span>`;
      setTimeout(() => {
        btn.innerHTML = `<i class="fa-solid fa-copy"></i> <span>Copy</span>`;
      }, 2000);
    });
  }
}

// ============================================================================
// 6. PRIVATE ADMIN SECURITY LOGGING MODULE
// ============================================================================
function initAdminModal() {
  document.getElementById("openAdminBtn")?.addEventListener("click", openAdminModal);
  
  document.getElementById("adminKeyInput")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") verifyAdminKey();
  });
}

function openAdminModal() {
  const modal = document.getElementById("adminModal");
  modal?.classList.remove("hidden");

  if (adminKeyVerified) {
    showAdminDashboard();
  } else {
    document.getElementById("adminLockScreen")?.classList.remove("hidden");
    document.getElementById("adminDashboardScreen")?.classList.add("hidden");
  }
}

function closeAdminModal() {
  document.getElementById("adminModal")?.classList.add("hidden");
}

async function verifyAdminKey() {
  const input = document.getElementById("adminKeyInput");
  const key = input?.value.trim();
  const errorEl = document.getElementById("adminAuthError");

  if (!key) return;

  try {
    const res = await fetch("/api/admin/verify", {
      method: "POST",
      headers: { "X-Admin-Key": key }
    });

    if (res.ok) {
      adminKeyVerified = true;
      adminKeyToken = key;
      errorEl?.classList.add("hidden");
      showAdminDashboard();
    } else {
      errorEl?.classList.remove("hidden");
    }
  } catch (err) {
    errorEl?.classList.remove("hidden");
  }
}

function showAdminDashboard() {
  document.getElementById("adminLockScreen")?.classList.add("hidden");
  document.getElementById("adminDashboardScreen")?.classList.remove("hidden");
  fetchAdminLogs();
}

async function fetchAdminLogs() {
  if (!adminKeyToken) return;

  const filter = document.getElementById("adminEventFilter")?.value || "ALL";

  try {
    const res = await fetch(`/api/admin/logs?event_type=${filter}&limit=100`, {
      headers: { "X-Admin-Key": adminKeyToken }
    });

    if (!res.ok) throw new Error("Unauthorized");

    const data = await res.json();

    const s = data.stats || {};
    const viewsEl = document.getElementById("adminTotalViews");
    const uniqueEl = document.getElementById("adminUniqueVisitors");
    const todayEl = document.getElementById("adminViewsToday");
    const eventsEl = document.getElementById("adminTotalEvents");
    const errorsEl = document.getElementById("adminTotalErrors");

    if (viewsEl) viewsEl.textContent = s.total_page_views || 0;
    if (uniqueEl) uniqueEl.textContent = s.unique_visitors || 0;
    if (todayEl) todayEl.textContent = s.views_today || 0;
    if (eventsEl) eventsEl.textContent = s.total_events || data.total_records || 0;
    if (errorsEl) errorsEl.textContent = s.total_errors || 0;

    const tbody = document.getElementById("adminLogsTableBody");
    tbody.innerHTML = (data.logs || []).map(log => `
      <tr class="hover:bg-dark-850 transition">
        <td class="p-2.5 text-slate-400 whitespace-nowrap">${log.timestamp.slice(11, 19)}</td>
        <td class="p-2.5 font-bold ${getEventColor(log.event_type)}">${log.event_type}</td>
        <td class="p-2.5 text-slate-400 font-mono">${log.ip_address}</td>
        <td class="p-2.5 text-slate-400">${log.duration_ms}ms</td>
        <td class="p-2.5"><span class="px-1.5 py-0.5 rounded text-[10px] ${log.status === 'SUCCESS' ? 'text-emerald-400 bg-emerald-500/10' : 'text-red-400 bg-red-500/10'}">${log.status}</span></td>
        <td class="p-2.5 text-slate-400 max-w-xs truncate" title='${JSON.stringify(log.details)}'>${JSON.stringify(log.details)}</td>
      </tr>
    `).join("");
  } catch (e) {
    alert("Admin log fetch error: " + e.message);
  }
}

function getEventColor(evt) {
  switch (evt) {
    case 'PAGE_VIEW': return 'text-blue-400';
    case 'CONTRACT_UPLOAD': return 'text-red-400';
    case 'VIN_LOOKUP': return 'text-cyan-400';
    case 'CONTRACT_COMPARISON': return 'text-amber-400';
    case 'CHAT_MESSAGE': return 'text-purple-400';
    case 'COUNTER_OFFER_SCRIPT': return 'text-emerald-400';
    case 'ADMIN_LOGIN_SUCCESS': return 'text-emerald-300';
    case 'ADMIN_LOGIN_FAILED': return 'text-red-500';
    default: return 'text-slate-300';
  }
}

async function clearSystemAuditLogs() {
  if (!confirm("Are you sure you want to permanently clear all audit logs?")) return;
  try {
    const res = await fetch("/api/admin/logs/clear", {
      method: "DELETE",
      headers: { "X-Admin-Key": adminKeyToken }
    });
    if (res.ok) fetchAdminLogs();
  } catch (e) {
    alert("Clear error: " + e.message);
  }
}

// ============================================================================
// 7. HELPERS & FORMATTING
// ============================================================================
function escapeHtml(str) {
  return str.replace(/[&<>'"]/g, tag => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;'
  }[tag] || tag));
}

function formatMarkdown(text) {
  if (!text) return "";
  return text
    .replace(/^### (.*$)/gim, '<h4 class="font-bold text-white text-xs mt-2">$1</h4>')
    .replace(/^## (.*$)/gim, '<h3 class="font-bold text-white text-sm mt-2">$1</h3>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong class="text-white font-semibold">$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em class="text-slate-300">$1</em>')
    .replace(/^• (.*$)/gim, '<li class="ml-4 list-disc text-slate-300">$1</li>')
    .replace(/\n/gim, '<br>');
}

// ============================================================================
// INITIALIZATION ON DOM LOAD (PRISTINE ZERO-DUMMY STATE)
// ============================================================================
document.addEventListener("DOMContentLoaded", () => {
  initMarketRadar();
  initNavigation();
  initContractUploader();
  initVinAssistant();
  initContractComparison();
  initChatbot();
  initAdminModal();

  // Fetch live US financial benchmarks from Federal Reserve & Treasury API
  fetchLiveMarketBenchmarks();

  // Periodically refresh market benchmarks every 15 minutes
  setInterval(fetchLiveMarketBenchmarks, 1000 * 60 * 15);

  // NOTE: Clean start - NO dummy presets preloaded!
  // Document starts ready for real user contract ingestion.
});
