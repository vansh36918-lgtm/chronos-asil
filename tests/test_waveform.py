"""
Unit tests for Multimodal Oscilloscope Waveform Analyzer.
"""

import os
from src.vision.waveform_analyzer import OscilloscopeWaveformAnalyzer


def test_synthetic_waveform_generation_and_nominal_analysis(tmp_path):
    analyzer = OscilloscopeWaveformAnalyzer()
    out_file = str(tmp_path / "nominal.png")

    generated_path = analyzer.generate_synthetic_waveform(out_file, fault_type=None)
    assert os.path.exists(generated_path)

    verdict = analyzer.analyze_waveform(generated_path)
    assert verdict.ringing_detected is False
    assert verdict.termination_impedance_fault is False
    assert "NOMINAL" in verdict.diagnosis


def test_synthetic_waveform_ringing_fault_detection(tmp_path):
    analyzer = OscilloscopeWaveformAnalyzer()
    out_file = str(tmp_path / "ringing_termination.png")

    generated_path = analyzer.generate_synthetic_waveform(out_file, fault_type="RINGING_MISSING_TERMINATION")
    assert os.path.exists(generated_path)

    verdict = analyzer.analyze_waveform(generated_path)
    assert verdict.ringing_detected is True
    assert verdict.termination_impedance_fault is True
    assert "CRITICAL PHYSICAL FAULT" in verdict.diagnosis
