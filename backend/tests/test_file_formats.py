import pytest

from app.services.file_formats import read_ecu_binary


def test_reads_raw_binary_file():
    ecu = read_ecu_binary("sample.bin", b"\x01\x02\x03\x04")

    assert ecu.file_format == "binary"
    assert ecu.content == b"\x01\x02\x03\x04"
    assert ecu.warnings == []


def test_reads_intel_hex_file():
    raw_hex = b":0400000001020304F2\n:00000001FF\n"

    ecu = read_ecu_binary("sample.hex", raw_hex)

    assert ecu.file_format == "intel_hex"
    assert ecu.content == b"\x01\x02\x03\x04"


def test_reads_motorola_s_record_file():
    raw_srec = b"S107000001020304F1\nS9030000FC\n"

    ecu = read_ecu_binary("sample.s19", raw_srec)

    assert ecu.file_format == "motorola_srec"
    assert ecu.content == b"\x01\x02\x03\x04"


def test_rejects_empty_ecu_file():
    with pytest.raises(ValueError, match="empty"):
        read_ecu_binary("empty.bin", b"")


def test_rejects_invalid_intel_hex_record():
    with pytest.raises(ValueError, match="Intel HEX"):
        read_ecu_binary("broken.hex", b"not an intel hex file")


def test_marks_proprietary_winols_files_with_warning():
    ecu = read_ecu_binary("project.ols", b"\x01\x02\x03")

    assert ecu.file_format == "binary"
    assert ecu.content == b"\x01\x02\x03"
    assert any("proprietary WinOLS" in warning for warning in ecu.warnings)
