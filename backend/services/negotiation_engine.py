import re
from typing import Dict, Any
from backend.services.huggingface_service import huggingface_service

class NegotiationEngine:
    def __init__(self):
        self.hf = huggingface_service
        self.pdf_text = ""
        self.contract_data = {}

    def _safe_float(self, v, default=0.0) -> float:
        """Safely convert any value to float, handling $, %, commas"""
        if v is None:
            return default
        try:
            if isinstance(v, str):
                cleaned = v.replace('%', '').replace('$', '').replace('₹', '').replace(',', '').strip()
                return float(cleaned) if cleaned else default
            return float(v)
        except (TypeError, ValueError):
            return default
    
    def _sum_fees(self, fees: list) -> float:
        """Safely sum fee amounts"""
        total = 0.0
        for f in fees:
            amt = f.get('amount', 0)
            total += self._safe_float(amt, 0.0)
        return total

    def set_context(self, pdf_text: str, contract_data: Dict[str, Any]):
        self.pdf_text = pdf_text
        self.contract_data = contract_data

    def _is_automotive_domain(self, q: str) -> bool:
        """
        Domain Guardrail:
        Ensures users can only query regarding car parts, vehicle leases, loan contracts,
        automotive purchasing, dealer negotiations, and related topics.
        """
        q_lower = q.lower()
        
        # Core automotive concepts & parts
        automotive_keywords = [
            # Parts & mechanics
            'part', 'parts', 'engine', 'transmission', 'gearbox', 'brake', 'brakes', 
            'rotor', 'pad', 'pads', 'tire', 'tires', 'tyre', 'tyres', 'wheel', 'wheels', 
            'battery', 'alternator', 'radiator', 'suspension', 'strut', 'shock', 'absorber', 
            'exhaust', 'muffler', 'catalytic', 'converter', 'spark plug', 'filter', 'oil', 
            'coolant', 'steering', 'windshield', 'headlight', 'taillight', 'clutch', 'chassis', 
            'drivetrain', 'powertrain', 'turbo', 'supercharger', 'airbag', 'bumper', 'fender', 
            'oem', 'aftermarket', 'diagnostic', 'repair', 'mechanic', 'recall', 'powertrain',
            # Financing, contracts, terms
            'loan', 'lease', 'contract', 'apr', 'interest', 'rate', 'emi', 'monthly', 
            'payment', 'instalment', 'installment', 'down payment', 'residual', 'money factor', 
            'buyout', 'trade-in', 'equity', 'depreciation', 'finance', 'financing', 'dealer', 
            'dealership', 'salesman', 'f&i', 'fee', 'fees', 'junk fee', 'doc fee', 'markup', 
            'counter-offer', 'negotiate', 'negotiation', 'quote', 'offer', 'agreement', 'gap', 
            'warranty', 'guarantee', 'service contract', 'maintenance', 'msrp', 'invoice', 
            'fair price', 'benchmark', 'credit', 'score', 'lender', 'lien', 'title', 'registration', 
            'penalty', 'early termination', 'disposition', 'mileage', 'odometer', 'vin',
            # Vehicles & auto types
            'car', 'cars', 'vehicle', 'vehicles', 'auto', 'automotive', 'suv', 'sedan', 
            'truck', 'coupe', 'hatchback', 'van', 'hybrid', 'electric', 'ev', 'motor', 
            'honda', 'toyota', 'ford', 'chevy', 'chevrolet', 'bmw', 'mercedes', 'audi', 
            'tesla', 'hyundai', 'kia', 'nissan', 'tata', 'maruti', 'mahindra', 'volkswagen', 
            'volvo', 'lexus', 'subaru', 'mazda', 'porsche', 'jeep', 'ram', 'dodge', 'chrysler',
            # Buying & negotiation actions
            'walk away', 'otd', 'out the door', 'discount', 'rebate', 'incentive', 'sticker price', 
            'buying', 'selling', 'buy', 'sell', 'purchase', 'test drive'
        ]

        return any(k in q_lower for k in automotive_keywords)

    def chat_negotiate(self, user_message: str, contract_context: Dict[str, Any]) -> str:
        q_clean = user_message.strip()
        q_lower = q_clean.lower()

        # -------------------------------------------------------------
        # 1. STRICT DOMAIN GUARDRAILS
        # -------------------------------------------------------------
        if not self._is_automotive_domain(q_lower):
            return """I am your **AI Automotive & Financing Negotiation Counsel**. 

To provide you with institutional-grade assistance, my scope is strictly focused on:
• **Car Parts & Maintenance:** OEM vs aftermarket components, repair pricing, diagnostic fees, and parts discounts
• **Vehicle Leases & Loan Contracts:** APR audits, monthly payments, amortizations, early termination, and unfair clauses
• **Dealership Negotiations:** Eliminating junk fees, statutory doc fee caps, and out-the-door price tactics
• **Market Benchmarks & Valuations:** Federal Reserve prime rates and dealer pricing intelligence

Please ask a question related to car financing, automotive contracts, vehicle parts, or dealership negotiations!"""

        def safe_float(v):
            return self._safe_float(v, 0.0)

        monthly = safe_float(contract_context.get('monthly_payment', 0))
        rate = safe_float(contract_context.get('interest_rate_apr') or contract_context.get('interest_rate', 0))
        term = safe_float(contract_context.get('lease_term_months') or contract_context.get('loan_term_months', 0))
        total_amount = safe_float(contract_context.get('total_amount', 0))
        score = safe_float(contract_context.get('fairness_score', {}).get('overall_score', 0))
        fees = contract_context.get('hidden_fees', [])
        contract_type = contract_context.get('contract_type', 'LOAN')

        # -------------------------------------------------------------
        # 2.5 LEASE MONEY FACTOR & FINANCIAL MATH
        # -------------------------------------------------------------
        if any(w in q_lower for w in ['money factor', 'moneyfactor', 'lease factor', 'factor to apr', 'apr to factor']):
            apr_match = re.search(r'([\d]{1,2}(?:\.\d{1,3})?)\s*%', q_lower)
            if apr_match:
                input_apr = float(apr_match.group(1))
                calc_mf = input_apr / 2400.0
                return f"""### Lease Money Factor Calculation:
To convert an Annual Percentage Rate (APR) to a Lease Money Factor, use the standard automotive industry formula:
$$\\text{{Money Factor}} = \\frac{{\\text{{APR}}}}{{2400}}$$

• **Input APR:** {input_apr}%
• **Calculated Money Factor:** `{calc_mf:.5f}` (or `{calc_mf:.6f}`)

*Conversely, multiply any dealer's money factor by 2,400 to reveal the true equivalent APR: `{calc_mf:.5f} × 2400 = {input_apr}% APR`.*"""
            else:
                return """### Lease Money Factor Formula:
In automotive leasing, finance charges are expressed as a **Money Factor** (lease fee rate).
$$\\text{{Money Factor}} = \\frac{{\\text{{APR}}}}{{2400}} \\quad \\Longleftrightarrow \\quad \\text{{APR}} = \\text{{Money Factor}} \\times 2400$$

• **Tier 1 Prime Benchmark:** `0.00239` (equivalent to **5.74% APR**)
• **Average Markup:** `0.00310+` (equivalent to **7.44%+ APR**)

*When negotiating a lease, always ask the finance manager for the 'buy-rate money factor' to prevent undisclosed dealer rate markups.*"""

        # -------------------------------------------------------------
        # 2.6 DEALER FEES, DOC FEES & ACCESSORY ADD-ONS
        # -------------------------------------------------------------
        if any(term in q_lower for term in ['doc fee', 'documentation fee', 'dealer prep', 'prep fee', 'mandatory fee', 'nitrogen']):
            return """### Dealer Fees & Statutory Regulations:
1. **Mandatory Statutory Fees (Government):**
   • State Sales Tax & DMV Registration / Title fees — these are non-negotiable and paid directly to the government.
2. **Dealer Documentation Fee (Doc Fee):**
   • Regulated States: California ($85 cap), New York ($175 cap), Minnesota ($125 cap), Texas ($150 guideline), Ohio ($250 cap).
   • Unregulated States (e.g., FL, GA, NC): Dealers charge $799–$1,200+. While dealers claim it is 'store policy', you can demand a commensurate discount on the vehicle's selling price to offset it.
3. **100% Negotiable Junk Add-Ons (Demand Removal):**
   • Dealer Preparation ($495–$895) — New vehicles are prepped under manufacturer factory warranty.
   • Nitrogen Tire Fill ($99–$249) — Atmospheric air is already 78% nitrogen.
   • Window VIN Etching ($199–$499) — Third-party kits cost under $25."""
        # -------------------------------------------------------------
        car_parts_triggers = [
            'part', 'parts', 'brake', 'brakes', 'rotor', 'rotors', 'pad', 'pads', 
            'tire', 'tires', 'engine', 'transmission', 'battery', 'alternator', 
            'radiator', 'suspension', 'exhaust', 'catalytic converter', 'spark plug', 
            'oem', 'aftermarket', 'timing belt'
        ]
        if any(w in q_lower for w in car_parts_triggers) and not any(f in q_lower for f in ['apr', 'monthly', 'contract', 'rate']):
            return """### Automotive Parts & Component Advisory:
1. **OEM vs. Certified Aftermarket:**
   - **OEM (Original Equipment Manufacturer):** Engineered precisely to factory specifications. Recommended for critical powertrain components (engine sensors, transmission solenoids, electronic modules).
   - **Tier-1 Aftermarket (Bosch, Brembo, Denso, Bilstein):** Often manufactured in the exact same plants as OEM parts but sold at 30%–50% lower cost. Ideal for wear-and-tear items (brake pads, rotors, filters, suspension struts).
2. **Dealer Parts Department Negotiation Tactics:**
   - **Wholesale Price Matching:** Dealership parts counters routinely mark up retail prices by 80%–120%. Ask for *"Wholesale Trade Matrix Pricing"* or show a printout from official online dealer parts portals (e.g., HondaPartsNow, ToyotaPartsDeal). Most will match it.
   - **Labor vs. Parts Separation:** Always demand an itemized estimate separating labor hours from parts costs. Check book labor times against Mitchell 1 or ALLDATA.
3. **Lease Return Compliance:**
   - If returning a leased vehicle, replacement tires and parts must match factory load ratings and speed ratings (or OEM equivalents) to avoid lease-end disposition penalties."""

        # -------------------------------------------------------------
        # 3. MARKET BENCHMARKS QUERIES
        # -------------------------------------------------------------
        if any(w in q_lower for w in ['benchmark', 'prime', 'market rate', 'average apr', 'average rate', 'fed rate', 'g.19']):
            return """**Current US Automotive Financing Benchmarks (Federal Reserve G.19 & U.S. Treasury Data):**
• **Prime 60-Month New Vehicle APR:** 7.54%
• **Average US Auto Monthly Payment:** $535 / month
• **Tier 1 Lease Money Factor Base:** 0.00239 (equivalent to ~5.74% APR)
• **Doc Fee Statutory Benchmark:** $250 ceiling (Regulated states: CA $85, NY $175, TX $150)

*When negotiating with dealership finance managers, demand Tier 1 buy-rate matching against these federal benchmarks.*"""

        # -------------------------------------------------------------
        # 4. TOTAL INTEREST CALCULATION
        # -------------------------------------------------------------
        if any(phrase in q_lower for phrase in ['how much interest', 'total interest', 'interest will i pay', 'interest cost']):
            if monthly and term and total_amount:
                total_paid = monthly * term
                denom = 1 + (rate / 100.0) * (term / 12.0)
                principal = total_amount / denom if denom > 0 else total_amount
                total_interest = max(0.0, total_paid - principal)
                pct_str = f"{(total_interest / principal) * 100:.1f}%" if principal > 0 else "N/A"
                
                return f"""**Total Interest Over Loan Term:**
- Monthly Payment: ${monthly:,.2f}
- Term: {int(term)} months
- Total Paid: ${total_paid:,.2f}
- Estimated Principal: ${principal:,.2f}
- **Total Interest: ${total_interest:,.2f}**

This represents approximately {pct_str} of your principal amount."""
            elif monthly and term:
                total_paid = monthly * term
                return f"Total payments over {int(term)} months: ${total_paid:,.2f}. Upload a contract or provide the financed principal amount to calculate exact interest."

        # -------------------------------------------------------------
        # 5. NEGOTIATION ADVICE & STRATEGY
        # -------------------------------------------------------------
        if any(phrase in q_lower for phrase in ['how to negotiate', 'negotiation advice', 'help me negotiate', 'negotiation tips', 'how do i negotiate']):
            market_apr = 7.54
            if rate > 0 and monthly > 0:
                target_apr = max(6.5, rate - 2.0)
                junk_fees = [f for f in fees if f.get('is_junk')]
                total_junk = self._sum_fees(junk_fees)
                t_term = term if term > 0 else 60
                savings = max(0.0, ((rate - target_apr) / 100.0 * (total_amount or (monthly * t_term)) * (t_term / 12.0)))
                target_monthly = monthly * (target_apr / rate) if rate > 0 else monthly
                
                advice = f"""Okay, let's talk strategy. Your current deal has a {rate}% APR, compared to the market benchmark average of around {market_apr}%. Here's how I'd approach this:

**First, tackle that interest rate.** Walk in confident and say: "I've been shopping around, and I'm seeing rates closer to {target_apr}% for my credit profile. What can you do to match that?" Don't ask if they *can* lower it—assume they can and make them work for your business. If you can get them down to {target_apr}%, you're looking at saving around ${savings:,.2f} over the life of the loan. That's real money.

**Next, let's talk about fees.** """

                if junk_fees:
                    advice += f"I see about ${total_junk:,.2f} in fees that honestly shouldn't be there. Things like "
                    fee_names = [f.get('name', 'fee') for f in junk_fees[:2]]
                    advice += ", ".join(fee_names)
                    advice += "—those are negotiable, and dealers add them because most people don't push back. Just calmly say: 'I'm not comfortable with these add-on fees. Can we remove them?' Most of the time, they'll fold."
                else:
                    advice += "The good news is I don't see obvious junk fees here, so that's one less fight."

                advice += f"""

**Here's the secret weapon: be ready to walk.** Before you sit down, get a pre-approval from a local credit union. Then you can say: "I've got another offer at {target_apr}% with lower fees. I'd prefer to work with you, but I need you to match or beat it."

**Target Goal:** Aim for **{target_apr}% APR**, a monthly payment closer to **${target_monthly:,.2f}**, and total elimination of optional dealer add-ons."""
                return advice
            else:
                return f"""### Tactical Car Financing Negotiation Strategy:
1. **Secure Outside Pre-Approval:** Always get pre-approved by a credit union or bank before negotiating at the dealership. Prime benchmarks are currently ~**{market_apr}% APR** for auto financing.
2. **Negotiate the Vehicle Price, Not the Monthly Payment:** Dealers frequently extend loan terms (e.g., 72–84 months) to make marked-up vehicles appear affordable. Always negotiate the Out-The-Door (OTD) selling price first.
3. **Eliminate Add-On Junk Fees:** Reject unwanted accessories (nitrogen fills, VIN etching, paint sealants) and push back on doc fees exceeding statutory caps ($150–$250).
4. **Leverage Competition:** Be prepared to walk away. Dealership finance managers have monthly volume bonuses and will often shave off dealer reserve markups to secure your deal.

*Tip: Upload your vehicle contract document in **Contract Analysis** or compare two competing quotes in **Contract Comparison** to receive tailored financial math and customized counter-offer scripts!*"""

        # -------------------------------------------------------------
        # 6. CONTRACT TERM SPECIFICS
        # -------------------------------------------------------------
        is_contract_question = any(word in q_lower for word in [
            'interest', 'rate', 'apr', 'monthly', 'payment', 'emi',
            'fee', 'fees', 'charge', 'contract', 'deal', 'loan', 'lease'
        ])

        if is_contract_question:
            if any(word in q_lower for word in ['what is', 'tell me', 'show']) and any(word in q_lower for word in ['interest', 'rate', 'apr']):
                if rate > 0:
                    market_avg = 7.54
                    diff = rate - market_avg
                    advice = f"Your {rate}% APR is well above market average. Aim for 7–7.5%." if diff > 1 else ("Your APR is competitive." if diff <= 0 else "Your APR is slightly high.")
                    return f"APR in your contract is **{rate}%** for {int(term)} months.\n\n{advice}"
                else:
                    return "The current national prime financing benchmark is **7.54% APR** (Federal Reserve G.19). Upload your vehicle contract in Tab 1 to see how your specific deal compares."

            if any(word in q_lower for word in ['monthly', 'payment', 'emi']):
                if monthly > 0:
                    return f"Your monthly payment is **${monthly:,.2f}** for {int(term)} months. Total to be paid: ${monthly * term:,.2f}. Reducing interest rate is the best way to lower it."
                else:
                    return "The current US national median car payment is **$535/month**. Upload a contract in Tab 1 to analyze your exact monthly payment breakdown."

            if any(word in q_lower for word in ['fee', 'fees', 'charge', 'remove', 'negotiate fee']):
                junk_fees = [f for f in fees if f.get('is_junk')]
                if junk_fees:
                    lines = "\n".join([f"- {f.get('name', 'Fee')} (${self._safe_float(f.get('amount',0)):,.2f})" for f in junk_fees])
                    return f"**Negotiable junk fees found:**\n{lines}\n\nAsk dealer to remove these optional fees."
                elif fees:
                    return "No obvious junk fees detected in your uploaded contract."
                else:
                    return "Standard junk fees dealers attempt to tack on include VIN etching ($199–$499), Nitrogen fills ($99–$199), and paint sealants ($495–$995). All of these are 100% optional and negotiable."

            if any(word in q_lower for word in ['score', 'fair', 'good', 'bad', 'rating']):
                if score > 0:
                    return f"**Fairness Score: {score:.0f}/100**\n\nLower scores indicate room for negotiation. Scores below 60 suggest unfavorable terms."
                else:
                    return "Upload a contract in **Contract Analysis** to generate an automated 0–100 forensic fairness score evaluating APR markup, junk fees, and loan structure."

        # -------------------------------------------------------------
        # 7. GENERAL AUTOMOTIVE INQUIRIES
        # -------------------------------------------------------------
        prompt = f"""You are a car loan and lease negotiation expert.

Contract Summary:
- Contract Type: {contract_type}
- Monthly Payment: ${monthly:,.2f}
- APR: {rate}%
- Term: {term} months
- Total Amount: ${total_amount:,.2f}
- Fairness Score: {score}/100

User Question:
{user_message}

Provide a clear, specific automotive negotiation answer. Keep response under 150 words."""

        try:
            response = self.hf.generate_text(prompt)
            if response and len(response.strip()) > 20 and "Unable to generate response" not in response:
                return response
        except Exception as e:
            print(f"HuggingFace error in chat: {e}")

        return f"""### Automotive Financing Counsel:
Regarding your query on **{user_message[:60]}**:
• **Benchmark Comparison:** Compare any financing proposal against the current Federal Reserve G.19 prime auto benchmark of **7.54% APR** for loans and **0.00239 money factor** (~5.74% APR) for leases.
• **Negotiation Recommendation:** Always demand an itemized Buyer's Order / Lease Disclosure sheet showing the capitalized cost, money factor, and unbundled fees before agreeing to financing terms.
• **Counter-Offer Action:** Upload your contract document in **Contract Analysis** to receive automated fairness audits and instant counter-offer emails."""

    def generate_negotiation_script(self, contract_data: Dict[str, Any], fairness_score: Dict[str, Any]) -> str:
        """Generate a professional counter-offer email"""
        def safe_float(v):
            return self._safe_float(v, 0.0)

        monthly = safe_float(contract_data.get('monthly_payment', 0))
        rate = safe_float(contract_data.get('interest_rate_apr') or contract_data.get('interest_rate', 0))
        term = safe_float(contract_data.get('lease_term_months') or contract_data.get('loan_term_months', 0))
        total = safe_float(contract_data.get('total_amount', 0))
        fees = contract_data.get('hidden_fees', [])
        vehicle = contract_data.get('vehicle_info', {})
        score = safe_float(fairness_score.get('overall_score', 0))
        
        target_rate = max(6.5, rate - 1.5) if rate > 0 else 6.5
        target_monthly = monthly * (target_rate / rate) if rate else monthly
        junk_fees = [f for f in fees if f.get('is_junk')]
        total_junk = self._sum_fees(junk_fees)
        
        current_total_paid = monthly * term
        improved_total_paid = target_monthly * term
        savings = current_total_paid - improved_total_paid
        
        script = f"""Subject: Counter-Offer on Vehicle Financing - Request for Revised Terms

Dear [Dealer/Finance Manager Name],

Thank you for providing the financing offer for the vehicle purchase. I've carefully reviewed the terms, and while I'm very interested in moving forward, I'd like to discuss some adjustments to ensure the deal works for both of us.

**Current Offer Summary:**
• Vehicle: {vehicle.get('make', 'Vehicle')} {vehicle.get('model', '')}
• APR: {rate}%
• Monthly Payment: ${monthly:,.2f}
• Loan Term: {int(term)} months
• Total Amount Financed: ${total:,.2f}
• Deal Fairness Audit Rating: {score:.0f}/100

After researching current market rates and comparing similar financing offers, I've identified a few areas where I believe we can reach more competitive terms:

**1. Interest Rate Adjustment**
The current APR of {rate}% is above the market average of 7-7.5% for qualified buyers. I've received competing offers in the {target_rate}% range from other lenders, including local credit unions. I would like to request an APR adjustment to {target_rate}%, which would bring the monthly payment to approximately ${target_monthly:,.2f}.

This adjustment would save me approximately ${savings:,.2f} over the loan term and demonstrates a more market-aligned rate.
"""

        if junk_fees:
            script += f"""
**2. Fee Review and Removal**
I noticed the following fees totaling ${total_junk:,.2f} that appear to be optional add-ons:
"""
            for fee in junk_fees[:3]:
                fee_amt = self._safe_float(fee.get('amount', 0))
                script += f"• {fee.get('name', 'Fee')}: ${fee_amt:,.2f}\n"
            
            script += """
I respectfully request the removal of these fees, as they are not standard charges and significantly increase the total cost. Most competing offers do not include these additional fees.
"""

        script += f"""
**Why This Makes Sense:**
• I'm a qualified buyer ready to close immediately upon agreement
• The revised terms align with current market standards
• I have alternative financing options available but prefer to work with you
• Accepting these terms means securing a sale today rather than risking the deal

**My Proposed Counter-Offer:**
• APR: {target_rate}%
• Monthly Payment: ${target_monthly:,.2f}
• Loan Term: {int(term)} months
• Remove optional fees: ${total_junk:,.2f}
• **Total Savings to Me: ${savings + total_junk:,.2f}**

Please let me know if you can accommodate these adjustments. I'm available to discuss this further and finalize this soon.

Best regards,
[Your Name]
[Your Phone Number]
[Your Email]
"""
        return script

# Global instance
negotiation_engine = NegotiationEngine()
