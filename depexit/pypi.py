"""Package metadata from public, free sources (PyPI JSON API, GitHub REST API).

Results are cached on disk inside the work directory so repeated runs are
fast and the exact responses used for a decision are kept as evidence.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "depexit/0.1 (+https://github.com)"


def _get_json(url: str, cache: Path, headers: dict | None = None, timeout: int = 20):
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        data = {"_error": f"HTTP {e.code}"}
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return {"_error": f"network: {e}"}  # not cached, may be transient
    cache.write_text(json.dumps(data), encoding="utf-8")
    return data


def _date(s: str | None):
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _release_date(data: dict, version: str | None):
    files = (data.get("releases") or {}).get(version or "", [])
    dates = [_date(f.get("upload_time_iso_8601")) for f in files if f.get("upload_time_iso_8601")]
    return min(dates) if dates else None


def _version_key(v: str):
    parts = []
    for p in re.split(r"[.+-]", v):
        parts.append((0, int(p), "") if p.isdigit() else (1, 0, p))
    return parts


def _is_prerelease(v: str) -> bool:
    return bool(re.search(r"(a|b|rc|dev)\d*", v))


def _github_repo(info: dict) -> str | None:
    urls = list((info.get("project_urls") or {}).values()) + [info.get("home_page") or ""]
    for u in urls:
        m = re.search(r"github\.com/([\w.-]+)/([\w.-]+)", u or "")
        if m:
            return f"{m.group(1)}/{m.group(2).removesuffix('.git')}"
    return None


def package_facts(name: str, installed: str | None, cache_dir: Path) -> dict:
    now = datetime.now(timezone.utc)
    data = _get_json(f"https://pypi.org/pypi/{name}/json", cache_dir / f"pypi-{name}.json")
    if "_error" in data:
        return {"package": name, "available": False, "error": data["_error"]}
    info = data.get("info", {})
    versions = [v for v, files in (data.get("releases") or {}).items()
                if files and not all(f.get("yanked") for f in files)]
    stable = sorted((v for v in versions if not _is_prerelease(v)), key=_version_key)
    latest = info.get("version") or (stable[-1] if stable else None)
    latest_date = _release_date(data, latest)
    inst_date = _release_date(data, installed) if installed else None
    inst_files = (data.get("releases") or {}).get(installed or "", [])
    newer = [v for v in stable if installed and _version_key(v) > _version_key(installed)]
    classifiers = info.get("classifiers") or []
    facts = {
        "package": info.get("name", name),
        "available": True,
        "summary": info.get("summary") or "",
        "license": (info.get("license_expression") or info.get("license") or "")[:120],
        "latest_version": latest,
        "latest_release_date": latest_date.date().isoformat() if latest_date else None,
        "days_since_latest_release": (now - latest_date).days if latest_date else None,
        "installed_version": installed,
        "installed_release_date": inst_date.date().isoformat() if inst_date else None,
        "installed_age_days": (now - inst_date).days if inst_date else None,
        "installed_yanked": bool(inst_files) and all(f.get("yanked") for f in inst_files),
        "newer_releases_count": len(newer),
        "major_versions_behind": (int(latest.split(".")[0]) - int(installed.split(".")[0]))
        if latest and installed and latest.split(".")[0].isdigit() and installed.split(".")[0].isdigit()
        else None,
        "requires_python_latest": info.get("requires_python"),
        "inactive_classifier": any("Inactive" in c for c in classifiers),
        "python_classifiers": sorted({c.split("::")[-1].strip() for c in classifiers
                                      if c.startswith("Programming Language :: Python :: 3.")}),
        "github": _github_repo(info),
        "source_url": f"https://pypi.org/project/{name}/",
    }
    if facts["github"]:
        headers = {"Accept": "application/vnd.github+json"}
        if os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
        gh = _get_json(f"https://api.github.com/repos/{facts['github']}",
                       cache_dir / f"gh-{facts['github'].replace('/', '__')}.json", headers)
        if "_error" not in gh and "archived" in gh:
            pushed = _date(gh.get("pushed_at"))
            facts["repo_archived"] = gh.get("archived")
            facts["repo_last_push"] = pushed.date().isoformat() if pushed else None
            facts["repo_days_since_push"] = (now - pushed).days if pushed else None
        else:
            facts["repo_lookup"] = gh.get("_error") or gh.get("message", "unavailable")
    return facts


def exists(name: str, cache_dir: Path) -> tuple[bool, str | None]:
    """Hallucination guard: does a package the model proposed really exist?"""
    data = _get_json(f"https://pypi.org/pypi/{name}/json", cache_dir / f"pypi-{name}.json")
    if "_error" in data:
        return False, None
    return True, data.get("info", {}).get("version")
