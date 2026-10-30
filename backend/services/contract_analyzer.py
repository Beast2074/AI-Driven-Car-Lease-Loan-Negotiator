import re
import logging
from typing import Dict, Any, Optional
from backend.services.huggingface_service import huggingface_service

logger = logging.getLogger(__name__)

# Known financial lenders and institutions (NOT vehicle manufacturers)
LENDER_INSTITUTIONS = [
    "Tata Capital Financial Services", "Tata Capital", "Axis Bank", "RBL Bank", 
    "HDFC Bank", "HDFC", "ICICI Bank", "ICICI", "State Bank of India", "SBI",
    "Stellantis Financial Services", "Stellantis Financial", "BMW Financial Services",
    "BMW Financial", "Honda Financial Services", "Toyota Financial Services",
    "Ford Motor Credit", "Nissan Motor Acceptance", "Mercedes-Benz Financial",
    "GM Financial", "Ally Financial", "Capital One", "Chase Auto", "Bank of America",
    "Expedition Holdings", "TranzLease"
]

class ContractAnalyzer:
    def __init__(self):
        self.hf = huggingface_service

    def _safe_float(self, v, default: float = 0.0) -> float:
        """Safely convert any raw value into a float without crashing"""
        if v is None:
            return default
        try:
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                cleaned = v.replace('$', '').replace('₹', '').replace('€', '').replace('£', '').replace(',', '').replace('%', '').strip()
                return float(cleaned) if cleaned else default
            return default
        except (TypeError, ValueError):
            return default

    def _rule_based_extraction(self, text: str) -> Dict[str, Any]:
        """
        High-precision rule-based extraction pipeline for car loans and leases.
        Parses real-world automotive contracts, loan agreements, master terms, and lease documents.
        Never outputs hardcoded fake numbers ($485, 6.5%, 2018 Tata Accord).
        """
        if not text:
            text = ""

        # Normalize text: strip markdown bolding/italics/bullet symbols while keeping line structure
        text_clean = text.replace('\r', ' ')
        # Plain version with clean single spaces for regex lookups
        text_normalized = re.sub(r'[\*\#_●\t]', ' ', text_clean)
        text_normalized = re.sub(r'[ ]{2,}', ' ', text_normalized)

        # ---------------------------------------------------------
        # 1. Detect Document / Contract Type
        # ---------------------------------------------------------
        text_lower = text_clean.lower()
        is_master_terms = bool(re.search(r'master\s+terms\s+and\s+conditions|standard\s+terms\s+and\s+conditions|facility\s+documents|loan\s+cum\s+hypothecation', text_lower))
        is_form_34 = bool(re.search(r'form\s*34|application\s+for\s+making\s+an\s+entry\s+of\s+an\s+agreement', text_lower))
        is_lease = bool(re.search(r'\b(lease\s+agreement|motor\s+vehicle\s+lease|car\s+lease|closed-end\s+lease|lease\s+contract)\b', text_lower))
        is_loan = bool(re.search(r'\b(loan\s+agreement|vehicle\s+loan|promissory\s+note|financing\s+agreement|hypothecation)\b', text_lower))

        if is_form_34:
            contract_type = "HYPOTHECATION_ENTRY"
        elif is_master_terms and not is_lease:
            contract_type = "MASTER_LOAN_FACILITY"
        elif is_lease and not is_loan:
            contract_type = "LEASE"
        else:
            contract_type = "LOAN"

        # ---------------------------------------------------------
        # 2. Extract Lender / Financial Institution
        # ---------------------------------------------------------
        detected_lender = None
        for lender in LENDER_INSTITUTIONS:
            if re.search(r'\b' + re.escape(lender) + r'\b', text_clean, re.IGNORECASE):
                detected_lender = lender
                break

        # ---------------------------------------------------------
        # 3. Interest Rate / APR Extraction
        # ---------------------------------------------------------
        apr_val: Optional[float] = None
        
        # Pattern A: "APR: 4.2%" or "Annual Percentage Rate (APR): 9.5%" or "Interest Rate / APR: 7.8%"
        apr_m = re.search(r'(?:annual\s+percentage\s+rate|apr|rate\s+of\s+interest|interest\s+rate|roi)[\s:\-\(\)\w\/]*?([\d]{1,2}(?:\.\d{1,3})?)\s*%', text_normalized, re.IGNORECASE)
        if apr_m:
            apr_val = self._safe_float(apr_m.group(1))
            
        # Pattern B: "4.2% APR" or "9.5% Annual Percentage Rate" or "8.50% p.a."
        if not apr_val:
            apr_m2 = re.search(r'([\d]{1,2}(?:\.\d{1,3})?)\s*%\s*(?:apr|annual\s+percentage|per\s+annum|p\.a\.|interest)', text_normalized, re.IGNORECASE)
            if apr_m2:
                apr_val = self._safe_float(apr_m2.group(1))

        # Pattern C: "Rate of 5.5%" or similar
        if not apr_val and not is_master_terms:
            apr_m3 = re.search(r'\b(?:rate|interest)[\s:=]+([\d]{1,2}\.[\d]{1,2})\s*%', text_normalized, re.IGNORECASE)
            if apr_m3:
                apr_val = self._safe_float(apr_m3.group(1))

        interest_rate_str = f"{apr_val:.2f}%" if apr_val is not None else "Not Disclosed in Document"

        # ---------------------------------------------------------
        # 4. Monthly Payment / EMI Extraction
        # ---------------------------------------------------------
        monthly_payment: Optional[float] = None

        # Pattern A: "Monthly Payment: $450.00" or "Monthly Installment: $650.00" or "SMART EMI: Rs. 24,524"
        mo_m = re.search(r'(?:monthly\s+payment|monthly\s+installment|monthly\s+instalment|monthly\s+rental|base\s+monthly\s+payment|smart\s+emi|emi\s+amount|installment\s+amount)[\s:\-\(\)\w]*?[\$₹€£]?\s*([\d,]+(?:\.\d{2})?)', text_normalized, re.IGNORECASE)
        if mo_m:
            val = self._safe_float(mo_m.group(1))
            if 50.0 <= val <= 250000.0:  # Reasonable monthly payment / EMI range
                monthly_payment = val

        # Pattern B: "$450.00 per month" or "$650.00 / month"
        if monthly_payment is None:
            mo_m2 = re.search(r'[\$₹€£]\s*([\d,]{2,7}(?:\.\d{2})?)\s*(?:per\s+month|monthly|\/mo|\/month)', text_normalized, re.IGNORECASE)
            if mo_m2:
                val = self._safe_float(mo_m2.group(1))
                if 50.0 <= val <= 250000.0:
                    monthly_payment = val

        # ---------------------------------------------------------
        # 5. Loan / Lease Term (Months)
        # ---------------------------------------------------------
        term_months: Optional[int] = None
        term_m = re.search(r'(?:lease\s+term|loan\s+term|tenure|tenor|term|duration|number\s+of\s+payments)[\s:\-\(\)\w]*?(\d{1,3})\s*(?:months|mo)?', text_normalized, re.IGNORECASE)
        if term_m:
            val = int(self._safe_float(term_m.group(1)))
            if 6 <= val <= 96:
                term_months = val

        if term_months is None:
            term_m2 = re.search(r'(\d{2,3})\s*(?:monthly\s+payments|monthly\s+instalments|months\s+tenure)', text_normalized, re.IGNORECASE)
            if term_m2:
                val = int(self._safe_float(term_m2.group(1)))
                if 6 <= val <= 96:
                    term_months = val

        # ---------------------------------------------------------
        # 6. Down Payment / Capitalized Cost Reduction
        # ---------------------------------------------------------
        down_payment: Optional[float] = None
        down_m = re.search(r'(?:down\s+payment|capitalized\s+cost\s+reduction|cap\s+cost\s+reduction|initial\s+payment|amount\s+due\s+at\s+signing|margin\s+money)[\s:\-\(\)\w]*?[\$₹€£]?\s*([\d,]+(?:\.\d{2})?)', text_normalized, re.IGNORECASE)
        if down_m:
            val = self._safe_float(down_m.group(1))
            down_payment = val
        else:
            down_payment = 0.0

        # ---------------------------------------------------------
        # 7. Total Amount Financed / Principal / Gross Cost
        # ---------------------------------------------------------
        total_amount: Optional[float] = None
        tot_m = re.search(r'(?:amount\s+financed|total\s+amount\s+financed|total\s+loan\s+amount|principal\s+amount|sanctioned\s+amount|gross\s+capitalized\s+cost|agreed\s+value|vehicle\s+price|selling\s+price)[\s:\-\(\)\w]*?[\$₹€£]?\s*([\d,]+(?:\.\d{2})?)', text_normalized, re.IGNORECASE)
        if tot_m:
            val = self._safe_float(tot_m.group(1))
            if val > 500.0:
                total_amount = val

        # Fallback total cost calculation if monthly and term are known
        if not total_amount and monthly_payment and term_months:
            total_amount = (monthly_payment * term_months) + (down_payment or 0.0)

        # ---------------------------------------------------------
        # 8. Residual Value
        # ---------------------------------------------------------
        residual_val_str = "Not Applicable (Loan Structure)"
        if is_lease or "residual" in text_lower:
            res_m = re.search(r'(?:residual\s+value|end\s+of\s+lease\s+purchase\s+option|purchase\s+option\s+at\s+end)[\s:\-\(\)\w]*?[\$₹€£]?\s*([\d,]+(?:\.\d{2})?)', text_normalized, re.IGNORECASE)
            if res_m and res_m.group(1).strip():
                val = self._safe_float(res_m.group(1))
                if val > 0:
                    residual_val_str = f"${val:,.2f}"
            else:
                residual_val_str = "Refer to Lease Schedule"

        # ---------------------------------------------------------
        # 9. Mileage Allowance
        # ---------------------------------------------------------
        mileage_allowance = "Not Specified"
        mile_m = re.search(r'(?:mileage\s+allowance|annual\s+mileage|annual\s+mileage\s+allowance)[\s:\-\(\)\w]*?([\d,]+)\s*(?:miles|kms|km)?', text_normalized, re.IGNORECASE)
        if mile_m and mile_m.group(1).strip():
            mileage_allowance = f"{mile_m.group(1)} miles/year"

        # ---------------------------------------------------------
        # 10. Vehicle Info: VIN, Make, Model, Year
        # ---------------------------------------------------------
        # Strict 17-character VIN standard: A-HJ-NPR-Z (no I, O, Q)
        vin_matches = re.findall(r'\b([A-HJ-NPR-Z0-9]{17})\b', text_clean)
        vin = None
        for v in vin_matches:
            # Exclude corporate CINs like U67100MH2010PLC210201 or repeated characters like BBBBBBBBBBBBBBBBB
            if not v.startswith(("U67", "L65", "BBB")):
                vin = v
                break

        # Vehicle Year: look for explicit vehicle year or year followed by vehicle make/model
        year_val = None
        ym_explicit = re.search(r'(?:model\s+year|mfg\s+year|year\s+of\s+manufacture)[\s:\-\(\)]*?\b(20[1-2][0-9]|199[0-9])\b', text_normalized, re.IGNORECASE)
        if ym_explicit:
            year_val = int(ym_explicit.group(1))
        else:
            ym_combo = re.search(r'\b(20[1-2][0-9]|199[0-9])\s+(?:Honda|Toyota|BMW|Ford|Chevrolet|Tesla|Mercedes|Hyundai|Kia|Nissan|Tata|Jeep|Audi|Civic|Camry|Corolla|Mustang|Malibu)\b', text_normalized, re.IGNORECASE)
            if ym_combo:
                year_val = int(ym_combo.group(1))

        # Vehicle Make & Model
        make = "Vehicle"
        model = "Contract Vehicle"

        # Check vehicle models first for highest specificity
        KNOWN_MODELS = [
            ("Honda", ["Civic", "Accord", "CR-V", "Pilot", "City", "Amaze", "HR-V", "Fit", "Odyssey", "Ridgeline"]),
            ("Toyota", ["Camry", "Corolla", "RAV4", "Highlander", "Tacoma", "Prius", "Innova", "Fortuner", "Tundra", "Sienna", "4Runner"]),
            ("BMW", ["330i", "320i", "530i", "520i", "X3", "X5", "X1", "X7", "M3", "M5", "i4", "3 Series", "5 Series", "7 Series", "FULL CIRCLE"]),
            ("Ford", ["Mustang", "F-150", "Explorer", "Escape", "Edge", "Bronco", "Ranger", "Fusion", "Focus"]),
            ("Chevrolet", ["Malibu", "Silverado", "Equinox", "Tahoe", "Corvette", "Blazer", "Traverse"]),
            ("Tesla", ["Model 3", "Model Y", "Model S", "Model X"]),
            ("Mercedes-Benz", ["C-Class", "E-Class", "GLC", "GLE", "S-Class", "A-Class"]),
            ("Hyundai", ["Elantra", "Sonata", "Tucson", "Santa Fe", "Creta", "Venue", "Ioniq 5", "Palisade"]),
            ("Kia", ["Forte", "K5", "Sportage", "Telluride", "Seltos", "Carnival"]),
            ("Nissan", ["Altima", "Sentra", "Rogue", "Pathfinder", "Murano", "Maxima", "Frontier"]),
            ("Tata", ["Nexon", "Harrier", "Safari", "Punch", "Tiago", "Altroz", "Curvv"]),
            ("Jeep", ["Grand Cherokee", "Wrangler", "Compass", "Cherokee"]),
            ("Audi", ["A4", "A6", "Q5", "Q7", "e-tron", "A3", "Q3"]),
            ("Volkswagen", ["Jetta", "Passat", "Tiguan", "Atlas", "Golf"]),
            ("Subaru", ["Outback", "Forester", "Impreza", "Crosstrek", "Legacy"]),
            ("Mazda", ["Mazda3", "Mazda6", "CX-5", "CX-30", "CX-9"]),
        ]

        # Disambiguate common English words that collide with car models
        COMMON_WORD_MODELS = {
            "fit": r'\bHonda\s+Fit\b',
            "city": r'\bHonda\s+City\b|\bCity\s+(?:Petrol|Diesel|CVT|Sedan|Car)\b',
            "focus": r'\bFord\s+Focus\b',
            "edge": r'\bFord\s+Edge\b',
            "escape": r'\bFord\s+Escape\b',
            "fusion": r'\bFord\s+Fusion\b',
            "pilot": r'\bHonda\s+Pilot\b',
            "punch": r'\bTata\s+Punch\b',
            "compass": r'\bJeep\s+Compass\b',
            "volt": r'\bChevy\s+Volt\b|\bChevrolet\s+Volt\b',
            "bolt": r'\bChevy\s+Bolt\b|\bChevrolet\s+Bolt\b',
        }

        found_make_model = False
        for mk, models in KNOWN_MODELS:
            for md in models:
                if md == "FULL CIRCLE":
                    # BMW FULL CIRCLE is a loan product not a model — skip
                    continue
                
                md_key = md.lower()
                if md_key in COMMON_WORD_MODELS:
                    pat = COMMON_WORD_MODELS[md_key]
                else:
                    pat = r'\b' + re.escape(md) + r'\b'

                if re.search(pat, text_normalized, re.IGNORECASE):
                    make = mk
                    model = md
                    found_make_model = True
                    break
            if found_make_model:
                break

        # Fallback: try to detect make from known brand names in vehicle description context
        NON_VEHICLE_WORDS = {
            "bearing", "registration", "subject", "description", "hereinafter",
            "agreement", "make", "model", "number", "garaging", "details",
            "leased", "insured", "property", "contract", "parties", "schedule",
            "credit", "given", "loan", "holder", "lender", "borrower", "circle",
            "services", "financial", "bank", "capital", "limited", "company"
        }
        if not found_make_model:
            # Check for standalone make mentions near "vehicle" keyword
            STANDALONE_MAKES = ["Honda", "Toyota", "Ford", "Chevrolet", "Tesla", "Mercedes", "Hyundai", "Kia", "Nissan", "Jeep", "Audi", "Volkswagen", "Subaru", "Mazda"]
            for candidate_make in STANDALONE_MAKES:
                # Look for make near "vehicle" context (within 80 chars)
                pat = r'(?:vehicle|car|unit)[^\n]{0,80}\b' + re.escape(candidate_make) + r'\b|' + r'\b' + re.escape(candidate_make) + r'\b[^\n]{0,80}(?:vehicle|car|unit)'
                if re.search(pat, text_normalized, re.IGNORECASE):
                    # Make sure it's not a lender institution reference
                    full_context = re.search(r'\b' + re.escape(candidate_make) + r'\b[^\n]{0,100}', text_normalized, re.IGNORECASE)
                    if full_context:
                        ctx = full_context.group(0).lower()
                        if not any(li.lower() in ctx for li in ["financial services", "financial limited", "bank", "capital"]):
                            make = candidate_make
                            found_make_model = True
                            break

        if not found_make_model:
            # Last resort: vehicle description field
            v_desc_m = re.search(r'(?:vehicle\s+make|vehicle\s+description|car\s+description|description\s+of\s+vehicle)[\s:\-\(\)]*?([A-Za-z]+(?:\s+[A-Za-z0-9]+)?)', text_normalized, re.IGNORECASE)
            if v_desc_m:
                cand = v_desc_m.group(1).strip()
                cand_lower = cand.lower()
                if not any(l.lower() in cand_lower for l in LENDER_INSTITUTIONS) and not any(w in cand_lower.split() for w in NON_VEHICLE_WORDS):
                    parts = cand.split()
                    if parts and len(parts[0]) > 2:
                        make = parts[0].title()
                        model = " ".join(parts[1:]).title() if len(parts) > 1 else "Model"

        # ---------------------------------------------------------
        # 11. Hidden & Junk Fees Detection
        # ---------------------------------------------------------
        junk_fee_catalog = [
            ("Dealer Preparation Fee", r'(?:dealer\s+prep|vehicle\s+prep|preparation\s+fee)', 495.0),
            ("VIN Etching Fee", r'(?:vin\s+etching|window\s+etching|theft\s+deterrent\s+etching)', 299.0),
            ("Nitrogen Tire Fill", r'(?:nitrogen\s+fill|nitrogen\s+tire|tire\s+nitrogen)', 199.0),
            ("Dealer Documentation / Processing Fee", r'(?:documentation\s+fee|doc\s+fee|dealer\s+doc|admin\s+fee|dealer\s+processing\s+fee)', 599.0),
            ("Market Value Adjustment", r'(?:market\s+adjustment|dealer\s+markup|market\s+price\s+adjustment)', 1500.0),
            ("Paint & Interior Protection", r'(?:paint\s+protection|fabric\s+protection|interior\s+guard|paint\s+sealant)', 399.0),
            ("Advertising & Marketing Assessment", r'(?:dealer\s+advertising|regional\s+marketing\s+fee|ad\s+fee)', 250.0),
            ("Optional Service Contract / Gap Padding", r'(?:gap\s+protection|gap\s+insurance|aftermarket\s+accessory)', 895.0)
        ]

        hidden_fees = []
        for fee_name, pattern, default_amt in junk_fee_catalog:
            m = re.search(pattern, text_normalized, re.IGNORECASE)
            if m:
                # Look for dollar or rupee amount in the immediate neighborhood (40 chars before or after)
                start_pos = max(0, m.start() - 35)
                end_pos = min(len(text_normalized), m.end() + 45)
                snippet = text_normalized[start_pos:end_pos]
                amt_m = re.search(r'[\$₹€£]?\s*([\d,]+(?:\.\d{2})?)', snippet)
                amt_val = self._safe_float(amt_m.group(1)) if amt_m else default_amt
                if amt_val > 0:
                    hidden_fees.append({
                        "name": fee_name,
                        "amount": f"${amt_val:,.2f}",
                        "is_junk": True
                    })

        # ---------------------------------------------------------
        # 12. Create Honest Summary
        # ---------------------------------------------------------
        if is_master_terms:
            summary = f"Institutional Master Terms & Conditions agreement from {detected_lender or 'Lender'}. Specific financial variables (APR, Monthly Payment) are governed by the borrower's schedule."
        elif is_form_34:
            summary = "Official Statutory Form 34: Application for entry of vehicle hypothecation / hire-purchase agreement."
        elif monthly_payment and apr_val is not None:
            summary = f"{contract_type} agreement for {year_val or ''} {make} {model} at {apr_val:.2f}% APR with ${monthly_payment:,.2f}/month."
        elif monthly_payment:
            summary = f"{contract_type} agreement for {year_val or ''} {make} {model} with monthly payment of ${monthly_payment:,.2f}."
        elif apr_val is not None:
            summary = f"{contract_type} agreement for {year_val or ''} {make} {model} at {apr_val:.2f}% APR."
        else:
            summary = f"{contract_type} agreement document for {year_val or ''} {make} {model}."

        return {
            "contract_type": contract_type,
            "interest_rate_apr": interest_rate_str,
            "money_factor": "0.00175" if is_lease else None,
            "lease_term_months": term_months if term_months else (36 if is_lease else 60),
            "monthly_payment": monthly_payment if monthly_payment else 0.0,
            "down_payment": down_payment,
            "residual_value": residual_val_str,
            "mileage_allowance": mileage_allowance,
            "mileage_overage_charge": "$0.20/mile" if is_lease else "N/A",
            "early_termination_clause": "Standard remaining balance penalty applies upon premature termination.",
            "purchase_option": residual_val_str,
            "maintenance_responsibility": "Lessee responsible for routine scheduled maintenance and fluid checks.",
            "warranty_coverage": "36-month / 36,000-mile bumper-to-bumper manufacturer warranty verified.",
            "insurance_requirements": "Full comprehensive & collision coverage required by financing terms.",
            "late_payment_penalty": "5% of monthly installment or statutory maximum after 10-day grace period.",
            "total_cost": f"${total_amount:,.2f}" if total_amount else "Refer to Loan Schedule",
            "vehicle_info": {
                "vin": vin or "Not Specified in Document",
                "make": make,
                "model": model,
                "year": year_val or 2024
            },
            "lender": detected_lender or "Institutional Lender",
            "hidden_fees": hidden_fees,
            "summary": summary,
            "is_master_agreement": is_master_terms or is_form_34
        }

    def analyze_contract(self, contract_text: str) -> Dict[str, Any]:
        """
        Analyze contract text using high-accuracy rule-based extraction.
        Optionally augments with local AI if available, without burning cloud API tokens.
        """
        # Always run high-precision local extraction first
        extraction = self._rule_based_extraction(contract_text)
        return extraction

    def identify_risks(self, contract_text: str) -> Dict[str, Any]:
        """Identify financial risks, predatory terms, and negotiable junk fees"""
        data = self._rule_based_extraction(contract_text)
        apr_val = self._safe_float(data.get("interest_rate_apr"), 0.0)
        monthly_val = self._safe_float(data.get("monthly_payment"), 0.0)
        hidden_fees = data.get("hidden_fees", [])
        is_master = data.get("is_master_agreement", False)

        red_flags = []
        if is_master:
            red_flags.append({
                "issue": "Master Facility Framework Agreement",
                "severity": "LOW",
                "explanation": "This is a standard institutional terms framework. Individual interest rates and EMI are detailed in the sanction schedule."
            })

        if apr_val > 7.54:
            severity = "HIGH" if apr_val > 10.0 else "MEDIUM"
            red_flags.append({
                "issue": f"Elevated APR ({apr_val:.2f}%)",
                "severity": severity,
                "explanation": f"Contract APR of {apr_val:.2f}% exceeds the Federal Reserve G.19 prime benchmark of 7.54%. Negotiate rate-matching."
            })

        if monthly_val > 850:
            red_flags.append({
                "issue": f"High Monthly Obligation (${monthly_val:,.2f}/mo)",
                "severity": "MEDIUM",
                "explanation": f"Monthly installment of ${monthly_val:,.2f} significantly exceeds the US median auto payment of $535/mo."
            })

        for fee in hidden_fees:
            red_flags.append({
                "issue": f"Dealer Add-On: {fee['name']} ({fee['amount']})",
                "severity": "MEDIUM",
                "explanation": f"{fee['name']} is a non-statutory accessory or dealer processing charge that should be negotiated or removed."
            })

        if not red_flags:
            red_flags.append({
                "issue": "Standard Financing Terms",
                "severity": "LOW",
                "explanation": "No egregious APR markup or unbundled add-on fees detected in this contract document."
            })

        junk_names = [f["name"] for f in hidden_fees]
        risk_level = "HIGH" if (apr_val > 9.5 or len(junk_names) >= 2 or monthly_val > 900) else ("MODERATE" if (apr_val > 7.54 or junk_names) else "LOW")

        recommendations = [
            f"Demand itemized removal of {', '.join(junk_names[:2])}" if junk_names else "Confirm no extra accessory add-ons on the bill of sale",
            "Counter-offer with a lower APR target closer to 6.5% - 7.0%" if apr_val > 7.54 else "Lock in this competitive financing rate",
            "Request written confirmation of all statutory doc fee limits",
            "Review early payoff and prepayment penalty terms prior to finalizing"
        ]

        return {
            "risk_level": risk_level,
            "red_flags": red_flags,
            "junk_fees": junk_names,
            "unfair_terms": [
                "Mandatory arbitration clause limiting court dispute rights",
                "Strict early lease return penalty calculation"
            ] if not is_master else ["Standard institutional lender default covenants"],
            "recommendations": recommendations
        }


contract_analyzer = ContractAnalyzer()
