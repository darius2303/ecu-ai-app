from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EcuBinary:
    file_name: str
    content: bytes
    file_format: str
    warnings: list[str] = field(default_factory=list)


def _parse_intel_hex(raw_text: str) -> bytes:
    memory: dict[int, int] = {}
    upper_address = 0

    for line_number, line in enumerate(raw_text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        if not line.startswith(":"):
            raise ValueError(f"Linia {line_number} nu este Intel HEX valida.")

        try:
            byte_count = int(line[1:3], 16)
            address = int(line[3:7], 16)
            record_type = int(line[7:9], 16)
            data = bytes.fromhex(line[9:9 + byte_count * 2])
        except ValueError as exc:
            raise ValueError(f"Linia {line_number} are valori HEX invalide.") from exc

        if record_type == 0x00:
            absolute = upper_address + address
            for offset, value in enumerate(data):
                memory[absolute + offset] = value
        elif record_type == 0x01:
            break
        elif record_type == 0x02:
            upper_address = int.from_bytes(data, "big") << 4
        elif record_type == 0x04:
            upper_address = int.from_bytes(data, "big") << 16

    if not memory:
        raise ValueError("Fisierul Intel HEX nu contine date.")

    start = min(memory)
    end = max(memory)
    return bytes(memory.get(address, 0xFF) for address in range(start, end + 1))


def _parse_motorola_srec(raw_text: str) -> bytes:
    memory: dict[int, int] = {}
    address_lengths = {"1": 2, "2": 3, "3": 4}

    for line_number, line in enumerate(raw_text.splitlines(), start=1):
        line = line.strip()
        if not line or not line.startswith("S"):
            continue
        record_type = line[1:2]
        if record_type not in address_lengths:
            continue

        address_len = address_lengths[record_type]
        try:
            count = int(line[2:4], 16)
            address_start = 4
            address_end = address_start + address_len * 2
            address = int(line[address_start:address_end], 16)
            data_hex_len = (count - address_len - 1) * 2
            data = bytes.fromhex(line[address_end:address_end + data_hex_len])
        except ValueError as exc:
            raise ValueError(f"Linia {line_number} nu este Motorola S-record valida.") from exc

        for offset, value in enumerate(data):
            memory[address + offset] = value

    if not memory:
        raise ValueError("Fisierul Motorola S-record nu contine date.")

    start = min(memory)
    end = max(memory)
    return bytes(memory.get(address, 0xFF) for address in range(start, end + 1))


def read_ecu_binary(file_name: str, raw_bytes: bytes) -> EcuBinary:
    if not raw_bytes:
        raise ValueError("Fisierul ECU este gol.")

    suffix = Path(file_name).suffix.lower()
    warnings: list[str] = []

    if suffix in {".hex", ".paf", ".daf"}:
        text = raw_bytes.decode("ascii", errors="ignore")
        content = _parse_intel_hex(text)
        return EcuBinary(file_name, content, "intel_hex", warnings)

    if suffix in {".s19", ".s28", ".s37", ".mot", ".srec"}:
        text = raw_bytes.decode("ascii", errors="ignore")
        content = _parse_motorola_srec(text)
        return EcuBinary(file_name, content, "motorola_srec", warnings)

    if suffix in {".ols", ".olsx", ".kp"}:
        warnings.append(
            "Format proprietar WinOLS detectat. Analiza binara poate fi imprecisa fara export/definitii dedicate."
        )

    return EcuBinary(file_name, raw_bytes, "binary", warnings)
