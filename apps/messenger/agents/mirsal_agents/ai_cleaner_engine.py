"""Image processing experiment using remove-ai-watermarks v0.45.1.

Script release: 2026-10-14 v4. Distinct filename prevents accidentally running old copies.

Modes:
  resize          : inspect -> scaled JPEG ON DISK -> reopen JPEG -> original size -> inspect
  sdxl            : inspect -> low-strength SDXL (GPU/CPU offload) -> inspect
  resize_then_sdxl: inspect -> disk resize round trip -> SDXL -> inspect

Original untouched. Output: <stem>_cleaned<extension>, JSON report and short terminal verdict.
Resize modes additionally keep <stem>_resize.jpg (the real enlarged JPEG).

NOTE: This does not verify invisible SynthID or predict platform labeling.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageOps, ImageStat

# ====================== SETTINGS (from config.py) ============================
# Tuning lives in mirsal_agents/config.py (Cleaner, CLEANER_* env vars): change
# env, restart the service. Same-name globals keep the battle-tested call
# sites (and the ai_cleaner.py wrapper) working unchanged.
try:
    from .config import Cleaner  # service import (package context)
except ImportError:  # direct run: python ai_cleaner_engine.py (no package context)
    from config import Cleaner  # noqa: E402 — sibling dir is sys.path[0] there

CLEANER = Cleaner()
MODE = CLEANER.mode  # "resize", "sdxl", or "resize_then_sdxl"
RESIZE_MULTIPLIER = CLEANER.resize_multiplier
JPEG_QUALITY = CLEANER.jpeg_quality
OUTPUT_FORMAT = CLEANER.output_format
SDXL_STRENGTH = CLEANER.sdxl_strength
SDXL_EFFECTIVE_STEPS = CLEANER.sdxl_effective_steps
CPU_OFFLOAD = CLEANER.cpu_offload
MAX_RESOLUTION = CLEANER.max_resolution
ALLOW_MODEL_DOWNLOADS = CLEANER.allow_model_downloads

BASE_DIR = Path(__file__).resolve().parent
PIPELINE = CLEANER.pipeline  # Never downloads/automatically selects Qwen's pipeline.
SCRIPT_VERSION = "2026-10-14-v6"


def find_cli() -> str:
    exe_folder = Path(sys.executable).parent
    for name in ("remove-ai-watermarks.exe", "remove-ai-watermarks"):
        path = exe_folder / name
        if path.is_file():
            return str(path)
    exe = shutil.which("remove-ai-watermarks")
    if not exe:
        raise RuntimeError("remove-ai-watermarks CLI missing from active venv.")
    return exe


def command_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    if ALLOW_MODEL_DOWNLOADS:
        env.pop("HF_HUB_OFFLINE", None)
        env.pop("DIFFSYNTH_SKIP_DOWNLOAD", None)
        env["DIFFSYNTH_DOWNLOAD_SOURCE"] = "HuggingFace"
    else:
        env["HF_HUB_OFFLINE"] = "1"
        env["DIFFSYNTH_SKIP_DOWNLOAD"] = "True"
    cached_classifier = BASE_DIR / "models" / "raiw-photo-classify"
    if cached_classifier.is_dir():
        env["RAIW_CLASSIFY_WEIGHTS"] = str(cached_classifier)
    return env


def extract_json(output: str) -> dict:
    output = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", output)
    dec = json.JSONDecoder()
    for pos, ch in enumerate(output):
        if ch == "{":
            try:
                parsed, _ = dec.raw_decode(output[pos:])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
    raise RuntimeError(f"Unable to parse CLI JSON:\n{output[-1800:]}")


def inspect(cli: str, image: Path, env: dict[str, str]) -> dict:
    results = {}
    for action in ("identify", "classify"):
        r = subprocess.run(
            [cli, action, str(image), "--json"],
            env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
        if r.returncode:
            raise RuntimeError(f"{action} failed:\n{(r.stderr or r.stdout)[-1800:]}")
        results[action] = extract_json(r.stdout)
    return results


def write_image(image: Image.Image, path: Path, *, jpeg_quality: int = 95) -> None:
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        image.convert("RGB").save(path, "JPEG", quality=jpeg_quality, subsampling=0)
    elif ext == ".png":
        image.save(path, "PNG")
    elif ext == ".webp":
        image.save(path, "WEBP", quality=jpeg_quality)
    else:
        raise ValueError(f"Unsupported export format: {ext}; use PNG, JPEG or WebP.")


def real_resize_roundtrip(src: Path, dest: Path) -> Path:
    """Two real disk stages, not one in-memory up/down operation."""
    intermediate = src.with_name(f"{src.stem}_resize.jpg")
    with Image.open(src) as opened:
        original = ImageOps.exif_transpose(opened)
        width, height = original.size
        # JPEG cannot store transparency. White background is intentional.
        if original.mode == "RGBA" or "transparency" in original.info:
            rgba = original.convert("RGBA")
            white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            white.alpha_composite(rgba)
            original = white.convert("RGB")
        else:
            original = original.convert("RGB")
        enlarged = original.resize(
            (round(width * RESIZE_MULTIPLIER), round(height * RESIZE_MULTIPLIER)),
            Image.Resampling.LANCZOS,
        )
        write_image(enlarged, intermediate, jpeg_quality=JPEG_QUALITY)
    print(f"\nRESIZE STEP 1: saved actual JPEG: {intermediate.name} ({enlarged.width}x{enlarged.height})")

    # Explicit reopen of the enlarged JPEG from disk.
    with Image.open(intermediate) as enlarged_from_disk:
        reduced = enlarged_from_disk.convert("RGB").resize(
            (width, height), Image.Resampling.LANCZOS
        )
        write_image(reduced, dest, jpeg_quality=JPEG_QUALITY)
    print(f"RESIZE STEP 2: reopened {intermediate.name} -> saved {dest.name} ({width}x{height})")
    return intermediate


def verify_gpu() -> dict:
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable in this venv. Use torch with CUDA enabled.")
    total = torch.cuda.get_device_properties(0).total_memory / 2**30
    free, _ = torch.cuda.mem_get_info(0)
    free_gib = free / 2**30
    info = {"device": torch.cuda.get_device_name(0), "total_gib": round(total, 2), "free_gib_before": round(free_gib, 2)}
    print(f"\nGPU: {info['device']}; VRAM free: {free_gib:.1f}/{total:.1f} GiB", flush=True)
    if free_gib < 6.0:
        raise RuntimeError("Less than 6 GiB VRAM free. Close GPU-heavy apps before SDXL.")
    return info


def run_sdxl(src: Path, dest: Path, env: dict[str, str]) -> None:
    """SDXL with optional experimental steps override, without editing packages."""
    print(f"\nSDXL: strength={SDXL_STRENGTH}, effective steps={SDXL_EFFECTIVE_STEPS}, cpu_offload={CPU_OFFLOAD}")
    if SDXL_EFFECTIVE_STEPS != 4:
        print("  EXPERIMENTAL: overriding the library's validated 4-step SDXL schedule.")
        print("  At strength=0.20 and effective=2, expect ~2 steps out of 10 requested, NOT 2 of 5.")
    # Launch this same file as a child so the override affects only the child process.
    cmd = [
        sys.executable, str(Path(__file__).resolve()), "--internal-sdxl",
        "invisible", str(src), "-o", str(dest),
        "--pipeline", PIPELINE,
        "--strength", str(SDXL_STRENGTH),
        "--controlnet-scale", "1.0",
        "--no-adaptive-polish", "--unsharp", "0", "--humanize", "0",
        "--max-resolution", str(MAX_RESOLUTION),
        "--seed", "0", "--force",
    ]
    if CPU_OFFLOAD:
        cmd.append("--cpu-offload")
    r = subprocess.run(cmd, env=env, check=False)
    if r.returncode:
        raise RuntimeError(f"SDXL failed with exit code {r.returncode}; check terminal output.")
    if not dest.is_file() or dest.stat().st_size == 0:
        raise RuntimeError(f"SDXL finished but output was not found: {dest}")


def image_quality(src: Path, dest: Path) -> dict:
    with Image.open(src) as a, Image.open(dest) as b:
        x, y = ImageOps.exif_transpose(a).convert("RGB"), ImageOps.exif_transpose(b).convert("RGB")
        if x.size != y.size:
            return {"original_size": list(x.size), "output_size": list(y.size), "psnr_db": None}
        diff = ImageChops.difference(x, y)
        stats = ImageStat.Stat(diff)
        mse = sum(z * z for z in stats.rms) / 3
        return {
            "original_size": list(x.size),
            "output_size": list(y.size),
            "psnr_db": "identical" if mse == 0 else round(10 * math.log10(65025 / mse), 2),
            "mean_absolute_difference": round(sum(stats.mean) / 3, 3),
        }


def terminal_verification(before: dict, after: dict, quality: dict, *,
                          source: Path, cleaned: Path, report_path: Path,
                          resize_file: Path | None) -> None:
    """Human-readable, short verification; the JSON remains the detailed report."""
    before_id, after_id = before["identify"], after["identify"]
    before_px, after_px = before["classify"], after["classify"]

    def provenance(info: dict) -> str:
        name = info.get("platform")
        return str(name) if name else "Unknown (no signal)"

    def pixel(info: dict) -> str:
        label = str(info.get("label") or "unknown").upper()
        detector = info.get("detector")
        return f"{label} ({detector})" if detector else label

    def provider(info: dict) -> str:
        value = info.get("provider")
        return str(value) if value else "Unattributed"

    def row(name: str, old: str, new: str) -> None:
        print(f"  {name:<19} {old:<28} ->  {new}")

    before_markers = len(before_id.get("signals") or [])
    after_markers = len(after_id.get("signals") or [])
    before_label = str(before_px.get("label") or "unknown").lower()
    after_label = str(after_px.get("label") or "unknown").lower()

    print("\n" + "=" * 69)
    print("LOCAL VERIFICATION  |  BEFORE -> AFTER")
    print("=" * 69)
    row("Provenance", provenance(before_id), provenance(after_id))
    row("Metadata signals", str(before_markers), str(after_markers))
    row("Pixel classifier", pixel(before_px), pixel(after_px))
    row("Provider guess", provider(before_px), provider(after_px))
    print("-" * 69)

    # The report identifies only supported *local* signals. Never claim
    # watermark removal or Instagram safety from an empty identify result.
    if before_markers > 0 and after_markers == 0:
        print("Metadata: detected indicators absent from output")
    elif after_markers > 0:
        print(f"Metadata: {after_markers} signal(s) remain detectable")
    else:
        print("Metadata: no supported signals in either file")

    if after_label == "ai":
        print("Pixel AI result: STILL AI")
    elif before_label != after_label:
        print(f"Pixel AI result: {before_label.upper()} -> {after_label.upper()} (model opinion)")
    else:
        print(f"Pixel AI result: {after_label.upper()} (unchanged)")

    psnr = quality.get("psnr_db")
    mae = quality.get("mean_absolute_difference")
    if psnr is not None:
        quality_text = f"PSNR {psnr} dB"
        if mae is not None:
            quality_text += f" | mean pixel difference {mae}/255"
        print(f"Image fidelity: {quality_text}")
    else:
        print("Image fidelity: dimension mismatch (PSNR unavailable)")

    print("SynthID: NOT TESTED locally | Instagram label: NOT PREDICTED")
    print(f"Saved: {cleaned.name}")
    if resize_file is not None:
        print(f"Resize intermediate: {resize_file.name}")
    print(f"Full report: {report_path.name}")
    print("=" * 69)


def internal_sdxl_cli() -> None:
    """Runs the real installed CLI after a temporary in-process step override."""
    from remove_ai_watermarks._internal import sdxl_zimage_pipeline
    if not hasattr(sdxl_zimage_pipeline, "SDXL_STEPS"):
        raise RuntimeError("Installed version no longer supports the SDXL_STEPS override.")
    sdxl_zimage_pipeline.SDXL_STEPS = int(SDXL_EFFECTIVE_STEPS)
    from remove_ai_watermarks.cli import main as cli_main
    cli_main(args=sys.argv[2:], standalone_mode=True)


def main(argv: list[str] | None = None) -> None:
    if MODE not in ("resize", "sdxl", "resize_then_sdxl"):
        raise ValueError("MODE must be 'resize', 'sdxl', or 'resize_then_sdxl'.")
    if not 0 < SDXL_STRENGTH <= 1:
        raise ValueError("SDXL_STRENGTH must be (0,1].")
    if SDXL_EFFECTIVE_STEPS not in (2, 4):
        raise ValueError("For this experiment, SDXL_EFFECTIVE_STEPS must be 2 or 4.")
    if not (1.0 < RESIZE_MULTIPLIER <= 4.0):
        raise ValueError("RESIZE_MULTIPLIER must be greater than 1.0 and at most 4.0.")
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0].startswith("-"):
        raise SystemExit("usage: python ai_cleaner_engine.py <image>  (tuning via CLEANER_* env vars, see mirsal_agents/config.py)")
    source = Path(args[0])
    if not source.is_absolute():
        source = (BASE_DIR / source).resolve()
    fmt = OUTPUT_FORMAT.lower().lstrip(".")
    if fmt == "jpeg":
        fmt = "jpg"
    if fmt not in ("jpg", "png", "webp"):
        raise ValueError("OUTPUT_FORMAT must be jpg, png, or webp.")
    cleaned = source.with_name(f"{source.stem}_cleaned.{fmt}")
    report_path = source.with_name(f"{source.stem}_cleaned_report.json")
    if cleaned == source:
        raise RuntimeError("Will not overwrite the source.")
    env, cli = command_env(), find_cli()
    print(f"\nPROCESSOR {SCRIPT_VERSION}", flush=True)
    print(f"Input: {source.name} | MODE: {MODE} | Export: {fmt.upper()} quality={JPEG_QUALITY if fmt != 'png' else 'lossless'}", flush=True)
    if MODE in ("sdxl", "resize_then_sdxl"):
        print(f"SDXL settings: effective_steps={SDXL_EFFECTIVE_STEPS} "
              f"| strength={SDXL_STRENGTH} "
              f"| CPU offload={'ON' if CPU_OFFLOAD else 'OFF'} "
              f"| max long side={MAX_RESOLUTION or 'native'}", flush=True)
        print("Face restoration still runs 8 steps per detected face; "
              "global SDXL step override does not change those.", flush=True)
    print(f"[1/3] Inspecting original: {source.name}", flush=True)
    before = inspect(cli, source, env)
    gpu = None
    resize_file = None
    print(f"[2/3] Processing mode: {MODE}", flush=True)
    if MODE == "resize":
        resize_file = real_resize_roundtrip(source, cleaned)
    elif MODE == "sdxl":
        gpu = verify_gpu()
        with tempfile.TemporaryDirectory(prefix="raiw-sdxl-output-") as tmp:
            raw_output = Path(tmp) / "sdxl_output.png"
            run_sdxl(source, raw_output, env)
            with Image.open(raw_output) as result:
                write_image(result, cleaned, jpeg_quality=JPEG_QUALITY)
    else:
        gpu = verify_gpu()
        # Use an ephemeral downscaled file for the SDXL input; leave only the
        # requested on-disk 200%-JPEG and the final clean result.
        with tempfile.TemporaryDirectory(prefix="raiw-pre-sdxl-") as tmp:
            prepared = Path(tmp) / f"prepared{source.suffix}"
            resize_file = real_resize_roundtrip(source, prepared)
            raw_output = Path(tmp) / "sdxl_output.png"
            run_sdxl(prepared, raw_output, env)
            with Image.open(raw_output) as result:
                write_image(result, cleaned, jpeg_quality=JPEG_QUALITY)
    print(f"FINAL EXPORT: {cleaned.name} ({cleaned.stat().st_size / 1024:.0f} KB)", flush=True)
    print(f"[3/3] Rechecking: {cleaned.name}", flush=True)
    after = inspect(cli, cleaned, env)
    quality = image_quality(source, cleaned)
    report = {
        "source": str(source), "processed": str(cleaned), "mode": MODE,
        "resize_intermediate_jpg": str(resize_file) if resize_file else None,
        "sdxl": {
            "enabled": "sdxl" in MODE, "pipeline": PIPELINE,
            "strength": SDXL_STRENGTH, "effective_steps": SDXL_EFFECTIVE_STEPS,
            "cpu_offload": CPU_OFFLOAD, "max_resolution": MAX_RESOLUTION,
            "download_allowed": ALLOW_MODEL_DOWNLOADS,
            "note": "Experimental 2-step override is not repository-calibrated. CPU offload is not a hard VRAM cap.",
        },
        "gpu": gpu, "quality": quality, "before": before, "after": after,
        "limitations": "Local classifiers do not detect OpenAI/Google SynthID and cannot predict Instagram labels.",
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    terminal_verification(before, after, quality, source=source, cleaned=cleaned,
                          report_path=report_path, resize_file=resize_file)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--internal-sdxl":
        internal_sdxl_cli()
    else:
        main()
