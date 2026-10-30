import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.services.negotiation_engine import negotiation_engine

def test_negotiation():
    # Mock Data
    context = {
        "monthly_payment": 485.0,
        "interest_rate_apr": "6.5%",
        "lease_term_months": 36,
        "total_amount": 25000,
        "hidden_fees": []
    }
    
    # Test 1: User query on interest
    print("Testing Total Interest Query...")
    resp = negotiation_engine.chat_negotiate("How much total interest will I pay?", context)
    assert "Total Interest" in resp or "interest" in resp.lower()
    print("✓ Interest calculation query passed")
    
    # Test 2: Negotiation strategy advice
    print("Testing Negotiation Advice...")
    resp = negotiation_engine.chat_negotiate("How do I negotiate this rate?", context)
    assert len(resp) > 50
    print("✓ Negotiation advice passed")
    
    print("\nAll Negotiation Engine Tests Passed!")

if __name__ == "__main__":
    test_negotiation()
