"""
Adversarial Chaos Fuzzer for Automotive CAN Bus & ECU Resilience Testing.
Simulates physical-layer faults, corrupted CRC, timing jitter, and bus-off events.
"""

import time
import random
import can
from typing import List, Dict, Any
from src.telemetry.can_bus import AutomotiveCANInterface


class CANChaosFuzzer:
    """
    Automated Fuzzing & Fault Injection Engine for Hardware-in-the-Loop / SIL.
    """

    def __init__(self, can_interface: AutomotiveCANInterface):
        self.can_interface = can_interface

    def inject_undervoltage_cold_crank(self, target_voltage: float = 6.2, duration_sec: float = 0.3) -> Dict[str, Any]:
        """
        Injects an acute cold-crank voltage collapse (e.g. 6.2V) into the CAN bus.
        Used to test if the ECU gate-driver safely triggers undervoltage lockout or crashes.
        """
        frame = self.can_interface.pack_power_frame(voltage_v=target_voltage, impedance_ohm=60.0)
        self.can_interface.send_frame(frame)
        return {
            "fault_type": "COLD_CRANK_VOLTAGE_COLLAPSE",
            "voltage_injected_v": target_voltage,
            "duration_sec": duration_sec,
            "status": "TRANSMITTED"
        }

    def inject_termination_fault(self, impedance_ohm: float = 120.0) -> Dict[str, Any]:
        """
        Simulates missing or damaged 120-ohm bus termination resistor,
        causing differential impedance to rise to 120Ω (or drop to 30Ω if parallel short).
        """
        frame = self.can_interface.pack_power_frame(voltage_v=12.5, impedance_ohm=impedance_ohm)
        self.can_interface.send_frame(frame)
        return {
            "fault_type": "BUS_TERMINATION_IMPEDANCE_MISMATCH",
            "impedance_ohm": impedance_ohm,
            "expected_behavior": "Differential signal reflection & bit-stuffing error frame"
        }

    def inject_bus_flood_denial_of_service(self, burst_count: int = 5) -> List[Dict[str, Any]]:
        """
        Injects a burst of dominant-bit arbitration ID 0x000 frames to simulate
        bus monopolization / Denial of Service attack on the CAN controller.
        """
        injected = []
        for _ in range(burst_count):
            flood_msg = can.Message(
                arbitration_id=0x000,
                data=b"\x00" * 8,
                is_extended_id=False
            )
            self.can_interface.send_frame(flood_msg)
            injected.append({"arb_id": "0x000", "payload": "0000000000000000"})
            time.sleep(0.01)
        return injected
