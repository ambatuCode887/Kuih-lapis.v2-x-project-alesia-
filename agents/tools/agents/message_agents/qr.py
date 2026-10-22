"""Deterministic QR decoding and link extraction for image attachments."""

from __future__ import annotations

from urllib.parse import urlsplit

import zxingcpp
from PIL import Image, ImageOps

_MAX_IMAGE_PIXELS = 40_000_000
_MAX_PAYLOADS = 5
_MAX_PAYLOAD_CHARACTERS = 2_000
_WEB_SCHEMES = ("http", "https")


def decode_qr_payloads(image: Image.Image) -> list[str]:
    """Return unique text payloads decoded from QR codes in the image."""
    if image.width * image.height > _MAX_IMAGE_PIXELS:
        return []
    normalized = ImageOps.exif_transpose(image).convert("RGB")
    payloads: list[str] = []
    for barcode in zxingcpp.read_barcodes(
        normalized,
        formats=zxingcpp.BarcodeFormat.QRCode,
    ):
        text = barcode.text.strip() if barcode.valid else ""
        if text and text not in payloads:
            payloads.append(text[:_MAX_PAYLOAD_CHARACTERS])
    return payloads[:_MAX_PAYLOADS]


def web_link_host(payload: str) -> str | None:
    """Return the lowercase host of an http(s) payload, or None for other content."""
    candidate = payload.strip()
    if candidate.casefold().startswith("www."):
        candidate = f"https://{candidate}"
    try:
        parts = urlsplit(candidate)
    except ValueError:
        return None
    if parts.scheme.casefold() not in _WEB_SCHEMES:
        return None
    host = (parts.hostname or "").strip(".")
    return host or None


def qr_link_hosts(payloads: list[str]) -> list[str]:
    """Return unique hosts of web links found in decoded QR payloads, in order."""
    hosts: list[str] = []
    for payload in payloads:
        host = web_link_host(payload)
        if host and host not in hosts:
            hosts.append(host)
    return hosts
