import glob
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.pdf_extractor import pdf_extractor
from backend.services.contract_analyzer import contract_analyzer
from backend.logic.fairness_scorer import fairness_scorer

pdf_paths = sorted(glob.glob('samples/*.pdf') + glob.glob('tests/fixtures/pdfs/*.pdf'))

print(f"Testing {len(pdf_paths)} contracts with current analyzer:")
print("-" * 110)
for p in pdf_paths:
    with open(p, 'rb') as f:
        content = f.read()
    txt = pdf_extractor.extract_text(content) or ""
    res = contract_analyzer._rule_based_extraction(txt)
    score = fairness_scorer.calculate_score(res)
    veh = res.get('vehicle_info', {})
    car = f"{veh.get('year')} {veh.get('make')} {veh.get('model')}"
    fname = os.path.basename(p)
    mo = res.get('monthly_payment')
    apr = res.get('interest_rate_apr')
    term = res.get('lease_term_months')
    sc = score.get('overall_score', 0)
    print(f"{fname:<33} | {car:<24} | Score: {sc:<3} | Mo: ${mo:<7} | APR: {apr:<6} | Term: {term}")
