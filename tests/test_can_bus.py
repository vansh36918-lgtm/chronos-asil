"""
Unit tests for Automotive CAN bus interface and Chaos Fuzzer.
"""

from src.telemetry.can_bus import AutomotiveCANInterface
from src.telemetry.fuzzer import CANChaosFuzzer


def test_can_frame_packing_and_decoding():
    can_interface = AutomotiveCANInterface(interface="virtual")
    try:
        # Pack Headlamp frame: 3200mA, 50% duty, 45 deg C
        msg = can_interface.pack_headlamp_frame(current_ma=3200, duty_cycle_pct=50.0, temp_c=45)
        decoded = can_interface.decode_frame(msg)

        assert decoded.arbitration_id == AutomotiveCANInterface.ID_HEADLAMP_CTRL
        assert decoded.decoded_signals["Current_mA"] == 3200.0
        assert decoded.decoded_signals["Duty_Cycle_Pct"] == 50.0
        assert decoded.decoded_signals["Temperature_C"] == 45.0
        assert decoded.anomaly_detected is None
    finally:
        can_interface.shutdown()


def test_can_overcurrent_anomaly_detection():
    can_interface = AutomotiveCANInterface(interface="virtual")
    try:
        # Pack Overcurrent frame: 4500mA (Threshold is 4200mA)
        msg = can_interface.pack_headlamp_frame(current_ma=4500, duty_cycle_pct=95.0, temp_c=70)
        decoded = can_interface.decode_frame(msg)

        assert decoded.anomaly_detected is not None
        assert "CRITICAL_OVERCURRENT" in decoded.anomaly_detected
    finally:
        can_interface.shutdown()


def test_can_power_voltage_and_impedance_anomaly():
    can_interface = AutomotiveCANInterface(interface="virtual")
    try:
        # Pack Cold-crank 6.1V and missing terminator 118.0 Ohm (Threshold 45-85 Ohm)
        msg = can_interface.pack_power_frame(voltage_v=6.1, impedance_ohm=118.0)
        decoded = can_interface.decode_frame(msg)

        assert decoded.decoded_signals["Supply_Voltage_V"] == 6.1
        assert decoded.decoded_signals["Bus_Impedance_Ohm"] == 118.0
        assert decoded.anomaly_detected is not None
        assert "UNDERVOLTAGE" in decoded.anomaly_detected or "PHYSICAL_BUS_FAULT" in decoded.anomaly_detected
    finally:
        can_interface.shutdown()


def test_chaos_fuzzer_injection():
    can_interface = AutomotiveCANInterface(interface="virtual")
    try:
        fuzzer = CANChaosFuzzer(can_interface)
        res = fuzzer.inject_undervoltage_cold_crank(target_voltage=6.2)
        assert res["fault_type"] == "COLD_CRANK_VOLTAGE_COLLAPSE"
        assert res["voltage_injected_v"] == 6.2

        term_res = fuzzer.inject_termination_fault(impedance_ohm=120.0)
        assert term_res["impedance_ohm"] == 120.0
    finally:
        can_interface.shutdown()
