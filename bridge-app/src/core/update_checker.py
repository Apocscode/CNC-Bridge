"""
CNC Bridge — Auto-Update Checker

Checks the GitHub Releases API on startup to notify users
if a newer version of CNC Bridge is available for download.
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CURRENT_VERSION = "2.0.0"
GITHUB_REPO = "Apocscode/CNC-Bridge"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


@dataclass
class UpdateInfo:
    """Information about an available update."""
    version: str
    download_url: str
    release_url: str
    release_notes: str
    published: str


def check_for_updates(timeout: float = 5.0) -> Optional[UpdateInfo]:
    """
    Check GitHub for a newer release.
    Returns UpdateInfo if a newer version exists, None otherwise.
    Non-blocking with timeout — safe to call on startup.
    """
    try:
        req = urllib.request.Request(
            RELEASES_URL,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": f"CNC-Bridge/{CURRENT_VERSION}",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        tag = data.get("tag_name", "").lstrip("vV")
        if not tag:
            return None

        if _compare_versions(tag, CURRENT_VERSION) > 0:
            # Find the first browser_download_url
            download_url = ""
            for asset in data.get("assets", []):
                if asset.get("browser_download_url", ""):
                    download_url = asset["browser_download_url"]
                    break

            return UpdateInfo(
                version=tag,
                download_url=download_url,
                release_url=data.get("html_url", ""),
                release_notes=data.get("body", "")[:500],
                published=data.get("published_at", "")[:10],
            )

        return None

    except urllib.error.URLError as e:
        logger.debug(f"Update check failed (network): {e}")
        return None
    except Exception as e:
        logger.debug(f"Update check failed: {e}")
        return None


def _compare_versions(a: str, b: str) -> int:
    """
    Compare version strings (e.g., '1.2.0' vs '1.1.0').
    Returns: >0 if a > b, 0 if equal, <0 if a < b.
    """
    try:
        parts_a = [int(x) for x in a.split('.')]
        parts_b = [int(x) for x in b.split('.')]

        # Pad shorter with zeros
        while len(parts_a) < len(parts_b):
            parts_a.append(0)
        while len(parts_b) < len(parts_a):
            parts_b.append(0)

        for va, vb in zip(parts_a, parts_b):
            if va > vb:
                return 1
            elif va < vb:
                return -1
        return 0
    except (ValueError, AttributeError):
        return 0
