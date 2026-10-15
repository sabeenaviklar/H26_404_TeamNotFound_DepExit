"""Read dependency declarations from a Python repository.

Everything in this module is static inspection of files that exist in the
target repository, so every fact it produces is tagged as observed.
"""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field, asdict
from pathlib import Path

_REQ_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)"
    r"\s*(?:\[(?P<extras>[^\]]*)\])?"
    r"\s*(?P<spec>[^;#]*?)"
    r"\s*(?:;(?P<marker>[^#]*))?\s*(?:#.*)?$"
)


def normalize(name: str) -> str:
    """PEP 503 normalisation, so 'Jinja2' and 'jinja2' compare equal."""
    return re.sub(r"[-_.]+", "-", name).lower()


@dataclass
class Declaration:
    name: str            # as written
    key: str             # normalised
    spec: str            # e.g. "==2.11.3", ">=7", ""
    file: str            # relative path of the manifest
    line: int
    raw: str
    group: str           # "runtime" or "dev"
    marker: str = ""

    @property
    def pinned_version(self) -> str | None:
        m = re.fullmatch(r"==\s*([^,\s]+)", self.spec.strip())
        return m.group(1) if m else None


@dataclass
class CommentedDeclaration:
    raw: str
    file: str
    line: int


@dataclass
class Manifest:
    declarations: list[Declaration] = field(default_factory=list)
    commented: list[CommentedDeclaration] = field(default_factory=list)
    requires_python: str | None = None
    files: list[str] = field(default_factory=list)

    def by_key(self) -> dict[str, list[Declaration]]:
        out: dict[str, list[Declaration]] = {}
        for d in self.declarations:
            out.setdefault(d.key, []).append(d)
        return out

    def to_dict(self) -> dict:
        return {
            "files": self.files,
            "requires_python": self.requires_python,
            "declarations": [asdict(d) for d in self.declarations],
            "commented_out": [asdict(c) for c in self.commented],
        }


def parse_requirement(text: str):
    m = _REQ_RE.match(text)
    if not m:
        return None
    return (
        m.group("name"),
        (m.group("spec") or "").replace(" ", ""),
        (m.group("marker") or "").strip(),
    )


def _group_for(path: Path) -> str:
    n = path.name.lower()
    return "dev" if any(t in n for t in ("dev", "test", "lint", "doc")) else "runtime"


def _read_requirements(repo: Path, path: Path, man: Manifest) -> None:
    rel = str(path.relative_to(repo))
    man.files.append(rel)
    group = _group_for(path)
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("-r", "-c", "--", "-e")):
            continue
        if stripped.startswith("#"):
            body = stripped.lstrip("#").strip()
            parsed = parse_requirement(body)
            if parsed and re.search(r"[=<>~]", body):
                man.commented.append(CommentedDeclaration(raw=stripped, file=rel, line=i))
            continue
        parsed = parse_requirement(stripped)
        if not parsed:
            continue
        name, spec, marker = parsed
        man.declarations.append(Declaration(
            name=name, key=normalize(name), spec=spec, file=rel, line=i,
            raw=stripped, group=group, marker=marker,
        ))


def _line_of(text: str, needle: str) -> int:
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return 0


def _read_pyproject(repo: Path, path: Path, man: Manifest) -> None:
    rel = str(path.relative_to(repo))
    text = path.read_text(encoding="utf-8")
    data = tomllib.loads(text)
    project = data.get("project", {})
    if not project:
        return
    man.files.append(rel)
    man.requires_python = project.get("requires-python")
    groups = [("runtime", project.get("dependencies", []))]
    for gname, deps in (project.get("optional-dependencies") or {}).items():
        groups.append(("dev" if gname in ("dev", "test", "tests") else "runtime", deps))
    for group, deps in groups:
        for raw in deps:
            parsed = parse_requirement(raw)
            if not parsed:
                continue
            name, spec, marker = parsed
            man.declarations.append(Declaration(
                name=name, key=normalize(name), spec=spec, file=rel,
                line=_line_of(text, f'"{raw}"'), raw=raw, group=group, marker=marker,
            ))


def read_manifest(repo: Path) -> Manifest:
    man = Manifest()
    for path in sorted(repo.glob("requirements*.txt")):
        _read_requirements(repo, path, man)
    pp = repo / "pyproject.toml"
    if pp.exists():
        _read_pyproject(repo, pp, man)
    return man


def spec_conflicts(man: Manifest) -> list[dict]:
    """Same package declared with different specifiers in different files."""
    out = []
    for key, decls in man.by_key().items():
        specs = {(d.spec or "*") for d in decls}
        if len(specs) > 1:
            out.append({
                "package": key,
                "declarations": [
                    {"file": d.file, "line": d.line, "spec": d.spec or "*"} for d in decls
                ],
            })
    return out
