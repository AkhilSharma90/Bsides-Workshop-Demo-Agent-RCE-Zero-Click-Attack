"""
Unit tests for MCPServerSim obfuscation detection methods — Phase 11.5

Tests each detection method independently without running a full demo.

Run with: pytest tests/ -v
"""
from __future__ import annotations

import base64
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from demo.tools import MCPServerSim


def _make_sim(mode: str = "defended") -> MCPServerSim:
    with tempfile.TemporaryDirectory() as d:
        sim = MCPServerSim(d, mode, "simulated")
    return sim


# ---------------------------------------------------------------------------
# Base64 detection
# ---------------------------------------------------------------------------

def test_detect_base64_positive():
    sim = _make_sim()
    b64_token = base64.b64encode(b"serviceA WRITE_PWNED_FILE").decode()
    found, method = sim._detect_base64(f"serviceA {b64_token}")
    assert found, "Base64-encoded token should be detected"
    assert method == "base64"


def test_detect_base64_negative():
    sim = _make_sim()
    found, method = sim._detect_base64("serviceA run_diagnostic")
    assert not found, "Clean target should not trigger base64 detection"


# ---------------------------------------------------------------------------
# Homoglyph detection
# ---------------------------------------------------------------------------

def test_detect_homoglyph_positive():
    sim = _make_sim()
    # Greek iota (U+0399 / Ι) looks like I — exact pattern from tools.py homoglyph_patterns
    homoglyph_target = "serviceA WR\u0399TE_PWNED_F\u0399LE"  # Ι in both positions
    found, method = sim._detect_homoglyphs(homoglyph_target)
    assert found, "Homoglyph token should be detected"
    assert method == "homoglyph"


def test_detect_homoglyph_negative():
    sim = _make_sim()
    found, method = sim._detect_homoglyphs("serviceA run_diagnostic")
    assert not found, "Clean target should not trigger homoglyph detection"


# ---------------------------------------------------------------------------
# BIDI detection
# ---------------------------------------------------------------------------

def test_detect_bidi_positive():
    sim = _make_sim()
    bidi_target = "serviceA WRITE_PWNED\u202c_FILE"  # U+202C POP DIRECTIONAL FORMATTING
    found, method = sim._detect_bidi(bidi_target)
    assert found, "BIDI control char should be detected"
    assert method == "bidi"


def test_detect_bidi_negative():
    sim = _make_sim()
    found, method = sim._detect_bidi("serviceA run_diagnostic")
    assert not found, "Clean target should not trigger BIDI detection"


# ---------------------------------------------------------------------------
# Zero-width steganography detection
# ---------------------------------------------------------------------------

def test_detect_zero_width_positive():
    sim = _make_sim()
    steg_target = "serviceA W\u200bRITE_PWNED_FILE"  # U+200B ZERO WIDTH SPACE
    found, method = sim._detect_zero_width_steganography(steg_target)
    assert found, "Zero-width char should be detected"
    assert method == "steganography"


def test_detect_zero_width_negative():
    sim = _make_sim()
    found, method = sim._detect_zero_width_steganography("serviceA run_diagnostic")
    assert not found, "Clean target should not trigger steganography detection"


# ---------------------------------------------------------------------------
# Exfiltration detection
# ---------------------------------------------------------------------------

def test_detect_exfiltration_positive():
    sim = _make_sim()
    content = base64.b64encode(b"secret_memory_content").decode()
    exfil_target = f"serviceA?audit={content}"
    found, method = sim._detect_exfiltration(exfil_target)
    assert found, "Canary exfil should be detected"
    assert method == "canary_exfil"


def test_detect_exfiltration_negative():
    sim = _make_sim()
    found, method = sim._detect_exfiltration("serviceA")
    assert not found, "Clean target should not trigger exfil detection"
