from __future__ import annotations


def decode_map_file_content(raw_bytes: bytes) -> str:
    """Decodeaza fisiere text de map pack si respinge intrarile clar binare."""
    if not raw_bytes:
        raise ValueError("The uploaded file is empty.")

    if raw_bytes.count(b"\x00") > max(8, len(raw_bytes) // 20):
        raise ValueError(
            "The file appears to be binary. Export the map as TXT/CSV from WinOLS and try again."
        )

    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            decoded = raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
        if decoded.strip():
            return decoded

    raise ValueError("The file could not be decoded as text.")
