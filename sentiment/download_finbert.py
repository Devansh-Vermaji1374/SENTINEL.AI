"""SENTINEL AI - FinBERT Model Weights Downloader.
Downloads and verifies ProsusAI/FinBERT model weights and tokenizer configurations.
Stored outside git repository tracking.
"""
from __future__ import annotations

import os
import sys
import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

EXPECTED_WEIGHTS_SHA256 = "e5897858ff819aad7629b96ce521ae5477952d03634ef5dd30ed2d76357a9f00"
FINBERT_REPO_ID = "ProsusAI/finbert"
DEFAULT_TARGET_DIR = Path("models/finbert_weights")


def verify_checksum(file_path: Path, expected_sha256: str) -> bool:
    """Compute and verify SHA256 checksum of a file."""
    if not file_path.exists():
        return False
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 1024 * 4):
            h.update(chunk)
    return h.hexdigest().lower() == expected_sha256.lower()


def download_finbert_weights(target_dir: Path = DEFAULT_TARGET_DIR, verify: bool = True) -> bool:
    """Download ProsusAI/FinBERT weights and tokenizer from Hugging Face Hub."""
    target_dir.mkdir(parents=True, exist_ok=True)
    weights_path = target_dir / "model.safetensors"

    if weights_path.exists():
        if verify:
            print(f"Checking existing model weights at {weights_path}...")
            if verify_checksum(weights_path, EXPECTED_WEIGHTS_SHA256):
                print(f"[OK] FinBERT weights already present and verified at {target_dir}")
                return True
            else:
                print(f"[WARN] Checksum mismatch for {weights_path}. Re-downloading...")
        else:
            print(f"[OK] FinBERT weights found at {target_dir}")
            return True

    print(f"Downloading ProsusAI/FinBERT from Hugging Face Hub into {target_dir}...")
    try:
        from huggingface_hub import hf_hub_download
        files_to_download = [
            "config.json",
            "model.safetensors",
            "special_tokens_map.json",
            "tokenizer_config.json",
            "vocab.txt"
        ]
        for filename in files_to_download:
            print(f"  Fetching {filename}...")
            hf_hub_download(
                repo_id=FINBERT_REPO_ID,
                filename=filename,
                local_dir=str(target_dir),
                local_dir_use_symlinks=False
            )

        if verify and weights_path.exists():
            print("Verifying downloaded weights checksum...")
            if verify_checksum(weights_path, EXPECTED_WEIGHTS_SHA256):
                print("[SUCCESS] FinBERT model verified successfully.")
                return True
            else:
                print("[ERROR] Download completed but checksum verification failed.")
                return False
        return True
    except Exception as e:
        print(f"[ERROR] Failed to download FinBERT model: {e}")
        print("Alternative: Run `python -m pip install huggingface-hub` and ensure internet connectivity.")
        return False


if __name__ == "__main__":
    success = download_finbert_weights()
    sys.exit(0 if success else 1)
