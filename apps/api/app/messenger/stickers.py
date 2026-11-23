"""Finished sticker packs and user-photo cut-outs.

Built-in packs are files the founder supplies. This tree ships one placeholder
pack labelled Demo data. Nothing here calls a sticker Builder.

The cut-out primary is BiRefNet general (MIT), official ONNX
BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx. That file is not vendored.
A phone cannot run it: the graph plus a 1024 square pass does not fit the
256 MiB minimum WebGPU buffer. Until the official weight is present and a
runtime can load it, the photo is unchanged. The phone fallback is U²-Net-P
(Apache-2.0, official weight u2netp.pth, about 4.7 MB, not vendored). It cuts
any subject. A missing weight keeps the original photo. This module does not
generate images.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.messenger.png import apply_matte, decode_png

OFFICIAL_ONNX = "BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx"
U2NET_P = "u2netp.pth"
# Minimum WebGPU device GPUBuffer (256 MiB). The official tiny general ONNX is 213.6 MB,
# which leaves no room for the default 1024 square pass, so the browser path refuses it.
PHONE_BUFFER_CAP = 268_435_456
MAX_EDGE = 512
MAX_RASTER = 512 * 1024
MAX_SVG = 100 * 1024
MAX_STICKERS = 50
MAX_PACKS = 20
_RASTER = {".png", ".webp"}
_ALLOWED = _RASTER | {".svg"}


class PackError(ValueError):
    pass


def packs_root() -> Path:
    here = Path(__file__).resolve()
    return here.parents[3] / "messenger" / "public" / "packs"


def load_manifest(root: Path) -> dict:
    path = root / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    packs = data.get("packs") or []
    if len(packs) > MAX_PACKS:
        raise PackError("too many packs")
    return data


def _svg_is_local(text: str) -> bool:
    lowered = text.lower()
    if "<script" in lowered or "javascript:" in lowered:
        return False
    # The SVG namespace is not a network fetch.
    stripped = lowered.replace('xmlns="http://www.w3.org/2000/svg"', "").replace("xmlns='http://www.w3.org/2000/svg'", "")
    if "http://" in stripped or "https://" in stripped or 'href="//' in stripped or "href='//" in stripped:
        return False
    return True


def resolve_sticker(root: Path, pack_id: str, sticker_id: str) -> dict:
    manifest = load_manifest(root)
    pack = next((p for p in manifest["packs"] if p.get("id") == pack_id), None)
    if pack is None:
        raise PackError("unknown pack")
    stickers = pack.get("stickers") or []
    if len(stickers) > MAX_STICKERS:
        raise PackError("too many stickers")
    item = next((s for s in stickers if s.get("id") == sticker_id), None)
    if item is None:
        raise PackError("unknown sticker")
    rel = Path(item["file"])
    if rel.is_absolute() or ".." in rel.parts:
        raise PackError("path")
    file = (root / rel).resolve()
    if not file.is_relative_to(root.resolve()):
        raise PackError("path")
    suffix = file.suffix.lower()
    if suffix not in _ALLOWED:
        raise PackError("type")
    data = file.read_bytes()
    if suffix == ".svg":
        if len(data) > MAX_SVG or not _svg_is_local(data.decode("utf-8")):
            raise PackError("svg")
    elif len(data) > MAX_RASTER:
        raise PackError("size")
    return {
        "kind": "sticker",
        "packId": pack_id,
        "stickerId": sticker_id,
        "bytes": data,
        "label": pack.get("label") or "",
        "provenance": pack.get("provenance") or "demo_fixture",
    }


def cutout_any_subject(image: bytes, *, weight: Path | None = None, runner=None) -> dict:
    """Return a PNG with the photo RGB and a matte alpha, or the original bytes."""
    if runner is None:
        if weight is None or not weight.is_file() or weight.name != OFFICIAL_ONNX:
            return {"png": image, "error": "model_missing", "stored": False}
        if weight.stat().st_size >= PHONE_BUFFER_CAP:
            return {"png": image, "error": "model_missing", "stored": False}
        return {"png": image, "error": "model_missing", "stored": False}
    _w, _h, _ch, _samples = decode_png(image)
    alpha = runner(image)
    return {"png": apply_matte(image, alpha), "error": None, "stored": True}


def u2net_p_fallback(image: bytes, *, weight: Path | None = None, runner=None) -> dict:
    """Any-subject fallback. The official u2netp.pth is not vendored."""
    if runner is None:
        if weight is None or not weight.is_file() or weight.name != U2NET_P:
            return {"png": image, "error": "model_missing", "stored": False}
        return {"png": image, "error": "model_missing", "stored": False}
    decode_png(image)
    return {"png": apply_matte(image, runner(image)), "error": None, "stored": True}
