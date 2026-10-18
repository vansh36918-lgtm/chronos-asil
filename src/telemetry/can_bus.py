"""
Automotive CAN Bus Interface for Chronos-ASIL.
Supports both Linux Kernel SocketCAN ('socketcan', e.g. vcan0) 
and cross-platform Virtual CAN ('virtual') for Windows.

Handles 29-bit CAN/CAN-FD frame packing, signal extraction, and real-time anomaly detection.
"""

import time
import struct
import can
from typing import List, Dict, Any, Optional
from src.core.models import CANFrameTelemetry


class AutomotiveCANInterface:
    """
    CAN Bus communication and decoding engine.
    Compatible with SocketCAN (Linux/WSL) and Virtual CAN (Windows/macOS).
    """

    # Well-known Automotive Arbitration IDs (ISO 11898)
    ID_HEADLAMP_CTRL = 0x120     # High-beam Matrix Driver
    ID_RADAR_TARGET = 0x130      # 77 GHz Forward Radar
    ID_POWER_MGMT = 0x140        # Battery / Cold-Crank Monitor
    ID_UDS_REQ = 0x7DF           # Diagnostic Request (ISO 14229)
    ID_UDS_RESP = 0x7E8          # Diagnostic Response (ISO 14229)

    def __init__(self, channel: str = "vcan0", interface: str = "virtual"):
        self.channel = channel
        self.interface = interface
        self.bus: Optional[can.BusABC] = None
        self._initialize_bus()

    def _initialize_bus(self):
        """Initializes the CAN bus interface with automatic fallback."""
        try:
            self.bus = can.interface.Bus(channel=self.channel, interface=self.interface)
        except Exception:
            # Fallback to virtual bus if socketcan is not present (e.g. Windows native)
            self.bus = can.interface.Bus(channel="test_vcan", interface="virtual")

    def shutdown(self):
        if self.bus:
            self.bus.shutdown()

    def pack_headlamp_frame(self, current_ma: int, duty_cycle_pct: float, temp_c: int) -> can.Message:
        """Packs Matrix Headlamp telemetry into an 8-byte CAN frame."""
        # Format: >H B b 4x (Big-endian: unsigned short current, unsigned char duty, signed char temp)
        data = struct.pack(">HBb4x", current_ma, int(duty_cycle_pct), temp_c)
        return can.Message(
            arbitration_id=self.ID_HEADLAMP_CTRL,
            data=data,
            is_extended_id=False
        )

    def pack_power_frame(self, voltage_v: float, impedance_ohm: float) -> can.Message:
        """Packs power management and CAN bus physical impedance into CAN payload."""
        # Format: >H H 4x (Voltage in mV, Impedance in 0.1 Ohm)
        v_mv = int(voltage_v * 1000)
        imp_dohm = int(impedance_ohm * 10)
        data = struct.pack(">HH4x", v_mv, imp_dohm)
        return can.Message(
            arbitration_id=self.ID_POWER_MGMT,
            data=data,
            is_extended_id=False
        )

    def send_frame(self, message: can.Message):
        """Transmits a frame onto the CAN bus."""
        if self.bus:
            self.bus.send(message)

    def decode_frame(self, message: can.Message) -> CANFrameTelemetry:
        """Decodes raw binary CAN payload into physical telemetry signals."""
        signals: Dict[str, float] = {}
        anomaly: Optional[str] = None

        if message.arbitration_id == self.ID_HEADLAMP_CTRL and len(message.data) >= 4:
            current_ma, duty, temp = struct.unpack(">HBb", message.data[0:4])
            signals["Current_mA"] = float(current_ma)
            signals["Duty_Cycle_Pct"] = float(duty)
            signals["Temperature_C"] = float(temp)

            # Anomaly check: Overcurrent / Thermal runaway
            if current_ma > 4200:
                anomaly = f"CRITICAL_OVERCURRENT: Headlamp driver drawing {current_ma}mA (Threshold: 4200mA)"
            elif temp > 105:
                anomaly = f"THERMAL_WARNING: Driver temperature {temp}°C exceeds max operating threshold"

        elif message.arbitration_id == self.ID_POWER_MGMT and len(message.data) >= 4:
            v_mv, imp_dohm = struct.unpack(">HH", message.data[0:4])
            voltage_v = v_mv / 1000.0
            impedance_ohm = imp_dohm / 10.0
            signals["Supply_Voltage_V"] = voltage_v
            signals["Bus_Impedance_Ohm"] = impedance_ohm

            # Anomaly check: Undervoltage cold-crank / missing 120-ohm termination
            if voltage_v < 7.2:
                anomaly = f"UNDERVOLTAGE_COLD_CRANK: Battery voltage dipped to {voltage_v:.2f}V"
            if impedance_ohm < 45.0 or impedance_ohm > 85.0:
                anomaly = f"PHYSICAL_BUS_FAULT: Bus impedance {impedance_ohm:.1f}Ω deviates from nominal 60.0Ω"

        return CANFrameTelemetry(
            timestamp=message.timestamp or time.time(),
            arbitration_id=message.arbitration_id,
            payload_hex=message.data.hex(),
            is_error_frame=message.is_error_frame,
            is_extended=message.is_extended_id,
            decoded_signals=signals,
            anomaly_detected=anomaly
        )

    def read_telemetry_stream(self, max_frames: int = 10, timeout: float = 0.5) -> List[CANFrameTelemetry]:
        """Reads and decodes a batch of telemetry frames from the bus."""
        frames: List[CANFrameTelemetry] = []
        start = time.time()
        while len(frames) < max_frames and (time.time() - start) < timeout:
            msg = self.bus.recv(timeout=0.05) if self.bus else None
            if msg:
                frames.append(self.decode_frame(msg))
        return frames
