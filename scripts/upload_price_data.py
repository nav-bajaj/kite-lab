#!/usr/bin/env python3
"""
Upload local price data to production Railway volume.

One-time script to sync historical price CSVs from local disk to the
production server's persistent volume via the /api/sync/upload-data endpoint.

Usage:
    python scripts/upload_price_data.py --api-url https://your-app.up.railway.app --token YOUR_JWT_TOKEN

    # Upload specific directory only
    python scripts/upload_price_data.py --api-url ... --token ... --target nse500_data
"""
import argparse
import os
import sys
import tarfile
import tempfile

import requests


TARGETS = ["nse500_data", "indices_data"]


def compress_directory(source_dir, target_name):
    """Compress a directory into a tar.gz file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False)
    tmp_path = tmp.name
    tmp.close()

    print(f"  Compressing {source_dir} ...")
    with tarfile.open(tmp_path, "w:gz") as tar:
        tar.add(source_dir, arcname=target_name)

    size_mb = os.path.getsize(tmp_path) / (1024 * 1024)
    print(f"  Archive: {size_mb:.1f} MB")
    return tmp_path


def upload_archive(api_url, token, archive_path, target):
    """Upload a tar.gz archive to the API."""
    url = f"{api_url}/api/sync/upload-data?target={target}"
    headers = {"Authorization": f"Bearer {token}"}

    filename = f"{target}.tar.gz"
    print(f"  Uploading to {url} ...")

    with open(archive_path, "rb") as f:
        response = requests.post(
            url,
            headers=headers,
            files={"file": (filename, f, "application/gzip")},
            timeout=300,
        )

    if response.status_code == 200:
        result = response.json()
        print(f"  Success: {result['files_written']} files written to {result['target_dir']}")
        return True
    else:
        print(f"  Failed ({response.status_code}): {response.text}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Upload local price data to production")
    parser.add_argument("--api-url", required=True, help="Production API URL (e.g. https://app.up.railway.app)")
    parser.add_argument("--token", required=True, help="JWT auth token")
    parser.add_argument("--target", default=None, choices=TARGETS, help="Upload specific directory only")
    parser.add_argument("--data-dir", default=None, help="Path to kite-lab root (default: auto-detect)")
    args = parser.parse_args()

    # Determine data directory
    if args.data_dir:
        data_dir = args.data_dir
    else:
        data_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    targets = [args.target] if args.target else TARGETS

    print(f"Data directory: {data_dir}")
    print(f"API: {args.api_url}")
    print(f"Targets: {', '.join(targets)}")
    print()

    for target in targets:
        source_dir = os.path.join(data_dir, target)
        if not os.path.isdir(source_dir):
            print(f"[SKIP] {target}: directory not found at {source_dir}")
            continue

        file_count = len([f for f in os.listdir(source_dir) if f.endswith(".csv")])
        print(f"[{target}] {file_count} CSV files")

        # Compress
        archive_path = compress_directory(source_dir, target)

        # Upload
        try:
            success = upload_archive(args.api_url, args.token, archive_path, target)
            if not success:
                print(f"  WARNING: Upload failed for {target}")
        finally:
            os.unlink(archive_path)

        print()

    print("Done.")


if __name__ == "__main__":
    main()
