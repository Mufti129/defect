#!/usr/bin/env python3
"""
AUTOMATED TEST CLIENT FOR PGI ENTERPRISE REST API
=================================================
Validates /health, /pricing, and /inspect endpoints.
"""

import sys
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

BASE_URL = "http://127.0.0.1:8504"

def test_health():
    print("[1/3] Testing GET /api/v1/health...")
    req = urllib.request.Request(f"{BASE_URL}/api/v1/health")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"      Status: {resp.status}")
        print(f"      Response: {data}")
        assert data.get("status") == "UP"
        print("      PASS ✅")

def test_pricing():
    print("\n[2/3] Testing GET /api/v1/pricing...")
    url = f"{BASE_URL}/api/v1/pricing?brand=Apple&model=iPhone%2013&capacity=128GB&grade=B&health_score=92.5"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"      Status: {resp.status}")
        pricing = data["valuation"]["pricing"]
        print(f"      Baseline Price  : Rp {pricing['baseline_market_price']:,}")
        print(f"      Market Value    : Rp {pricing['fair_market_value']:,}")
        print(f"      Max Loan Ceiling: Rp {pricing['recommended_loan']:,}")
        assert data.get("success") is True
        print("      PASS ✅")

def test_inspect():
    print("\n[3/3] Testing POST /api/v1/inspect with sample phone views...")
    # Find a real demo sample
    demo_p = Path("streamlit_inspection_app/demo_samples/grade_B")
    if not demo_p.exists():
        demo_p = Path("demo_samples/grade_B")
    
    first_unit = sorted([d for d in demo_p.iterdir() if d.is_dir() and not d.name.startswith(".")])[0]
    views = {}
    for s in ["back", "left", "right", "top", "bottom"]:
        p = first_unit / f"{s}.jpg"
        if p.exists():
            views[s] = str(p.resolve())
            
    payload = {
        "unit_id": f"TEST-{first_unit.name}",
        "model_version": "v6",
        "conf_threshold": 0.20,
        "views": views,
        "device_info": {
            "brand": "Apple",
            "model": "iPhone 13",
            "capacity": "128GB",
            "health_score": 90.0
        }
    }
    
    req_body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/inspect",
        data=req_body,
        headers={"Content-Type": "application/json"}
    )
    
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        dt = time.time() - t0
        print(f"      Status: {resp.status} (Took {dt:.2f}s)")
        print(f"      Assigned Grade   : {data.get('final_grade')} (Confidence: {data.get('grade_confidence')})")
        print(f"      Total DPI        : {data.get('total_dpi')}")
        print(f"      Total Defects    : {data.get('total_defects_count')}")
        val_loan = data.get('valuation', {}).get('pricing', {}).get('recommended_loan', 0)
        print(f"      Valuation Loan Rp: Rp {val_loan:,}")
        assert data.get("success") is True
        print("      PASS ✅")

if __name__ == "__main__":
    try:
        test_health()
        test_pricing()
        test_inspect()
        print("\n" + "=" * 70)
        print(" 🎉 ALL API SERVICE TESTS PASSED SUCCESSFULLY!")
        print("=" * 70)
    except Exception as e:
        print(f"\n[FAIL] API Test Failed: {e}")
        sys.exit(1)
