#!/usr/bin/env python3
"""
Integration test wrapper for Tier-3 Fast-SAR Jet-Hybrid (`fast_sar_jet_finlab02/` / `FIN-LAB-02`)
and Northern-Flank Low-Cost 100% Non-Chinese COTS Gap-Closure Enablers (`[P12-HEATED]`, `#8`, `#9`).
"""

import os
import sys
import unittest

FINLAB02_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "fast_sar_jet_finlab02",
)
if FINLAB02_DIR not in sys.path:
    sys.path.insert(0, FINLAB02_DIR)

from tests.test_sar_jet_suite import TestArcticFastSarJetSuite  # noqa: E402,F401

if __name__ == "__main__":
    unittest.main()
