# Test Suite & Quality Verification

This directory contains the production test suite for the Car Lease/Loan Negotiator.

## Active Test Files

- `check_dom_ids.py`: Validates that all JavaScript `getElementById` targets in `frontend/app.js` match valid HTML IDs in `frontend/index.html`.
- `test_api_upload.py`: Pytest suite verifying `/health`, `/upload`, `/contract/{id}`, and `/analyze/{id}` endpoints.
- `test_vin_decoder.py`: Pytest suite for valid/invalid VIN decoding and NHTSA fallback.
- `test_negotiation.py`: Pytest suite verifying the domain negotiation engine and APR query handling.
- `test_16_contracts.py`: Real-world benchmark running analysis across all 16 sample contracts.
- `comprehensive_e2e_verification.py`: Full end-to-end integration test validating health, benchmarks, VIN decoding, chatbot domain guardrails, and admin telemetry logging.

## Running Tests

```bash
# 1. Run all Pytest tests
python -m pytest tests/test_api_upload.py tests/test_vin_decoder.py tests/test_negotiation.py -v

# 2. Check DOM ID integrity
python tests/check_dom_ids.py

# 3. Run real-world contract benchmark (16 contracts)
python tests/test_16_contracts.py

# 4. Run end-to-end verification
python tests/comprehensive_e2e_verification.py
```
