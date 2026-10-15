"""Static usage scan: where and how each third-party module is used.

Walks the repository's Python files with ``ast`` and records import sites,
every later reference to the imported names, private-API access, and
monkeypatching of third-party objects. Non-Python files (Makefile,
Dockerfile, CI configs) are text-searched for module and CLI names.
"""
from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "venv", "env", "build", "dist", "__pycache__",
             ".tox", ".nox", "node_modules", ".mypy_cache", ".pytest_cache", ".depexit"}
TEXT_FILES = ("Makefile", "Dockerfile", "tox.ini", "setup.cfg", "noxfile.py",
              ".pre-commit-config.yaml")
TEXT_GLOBS = (".github/workflows/*.yml", ".github/workflows/*.yaml", "*.cfg", "*.ini")

STDLIB = set(sys.stdlib_module_names)


@dataclass
class Usage:
    file: str
    line: int
    kind: str          # import | from-import | reference | private-api | monkeypatch | text
    module: str        # top-level module, e.g. "jinja2"
    symbol: str        # what was touched, e.g. "jinja2.Environment"
    code: str          # the source line


@dataclass
class ScanResult:
    python_files: list[str] = field(default_factory=list)
    usages: list[Usage] = field(default_factory=list)
    local_modules: set[str] = field(default_factory=set)
    parse_errors: list[dict] = field(default_factory=list)

    def modules(self) -> set[str]:
        return {u.module for u in self.usages if u.kind in ("import", "from-import")}

    def for_modules(self, mods) -> list[Usage]:
        mods = set(mods)
        return [u for u in self.usages if u.module in mods]

    def to_dict(self) -> dict:
        return {
            "python_files": self.python_files,
            "local_modules": sorted(self.local_modules),
            "parse_errors": self.parse_errors,
            "usages": [asdict(u) for u in self.usages],
        }


def iter_files(repo: Path, pattern: str):
    for p in sorted(repo.rglob(pattern)):
        if any(part in SKIP_DIRS for part in p.relative_to(repo).parts):
            continue
        yield p


def _local_modules(repo: Path, files) -> set[str]:
    mods = set()
    for p in files:
        rel = p.relative_to(repo)
        mods.add(rel.parts[0].removesuffix(".py"))
    for p in repo.iterdir():
        if p.is_dir() and (p / "__init__.py").exists():
            mods.add(p.name)
    return mods


class _Visitor(ast.NodeVisitor):
    def __init__(self, rel: str, lines: list[str], local: set[str]):
        self.rel, self.lines, self.local = rel, lines, local
        self.bindings: dict[str, str] = {}   # local name -> dotted target
        self.out: list[Usage] = []

    def _code(self, node) -> str:
        return self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""

    def _external(self, dotted: str) -> bool:
        top = dotted.split(".")[0]
        return bool(top) and top not in STDLIB and top not in self.local and top != "__future__"

    def _add(self, node, kind, dotted):
        self.out.append(Usage(self.rel, node.lineno, kind, dotted.split(".")[0], dotted, self._code(node)))

    def visit_Import(self, node):
        for a in node.names:
            if self._external(a.name):
                self.bindings[a.asname or a.name.split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
                self._add(node, "import", a.name)

    def visit_ImportFrom(self, node):
        if node.level or not node.module or not self._external(node.module):
            return
        names = []
        for a in node.names:
            dotted = f"{node.module}.{a.name}"
            self.bindings[a.asname or a.name] = dotted
            names.append(a.name)
            if a.name.startswith("_") and not a.name.startswith("__"):
                self._add(node, "private-api", dotted)
        sym = names[0] if len(names) == 1 else "{" + ",".join(names) + "}"
        self._add(node, "from-import", f"{node.module}.{sym}")

    def _resolve(self, node) -> str | None:
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name) and node.id in self.bindings:
            return ".".join([self.bindings[node.id], *reversed(parts)])
        return None

    def visit_Assign(self, node):
        for t in node.targets:
            if isinstance(t, ast.Attribute):
                dotted = self._resolve(t)
                if dotted:
                    self._add(node, "monkeypatch", dotted)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        dotted = self._resolve(node)
        if dotted:
            self._add(node, "reference", dotted)
            if any(p.startswith("_") and not p.startswith("__") for p in dotted.split(".")[1:]):
                self._add(node, "private-api", dotted)
            return  # do not double count the inner chain
        self.generic_visit(node)

    def visit_Name(self, node):
        if node.id in self.bindings and isinstance(node.ctx, ast.Load):
            self._add(node, "reference", self.bindings[node.id])


def scan(repo: Path) -> ScanResult:
    res = ScanResult()
    files = list(iter_files(repo, "*.py"))
    res.local_modules = _local_modules(repo, files)
    for p in files:
        rel = str(p.relative_to(repo))
        res.python_files.append(rel)
        src = p.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src, filename=rel)
        except SyntaxError as e:
            res.parse_errors.append({"file": rel, "error": str(e)})
            continue
        v = _Visitor(rel, src.splitlines(), res.local_modules)
        v.visit(tree)
        # de-duplicate (same line, kind, symbol)
        seen = set()
        for u in v.out:
            k = (u.line, u.kind, u.symbol)
            if k not in seen:
                seen.add(k)
                res.usages.append(u)
    return res


def text_references(repo: Path, needles: dict[str, set[str]]) -> list[Usage]:
    """Search build/CI files for module names or CLI commands.

    needles maps a module name to the words that identify it
    (the module itself plus any console scripts its distribution ships).
    """
    paths = [repo / n for n in TEXT_FILES if (repo / n).exists()]
    for g in TEXT_GLOBS:
        paths.extend(p for p in iter_files(repo, g) if p not in paths)
    out = []
    for p in paths:
        rel = str(p.relative_to(repo))
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for mod, words in needles.items():
                for w in words:
                    if re.search(rf"(?<![\w-]){re.escape(w)}(?![\w-])", line):
                        out.append(Usage(rel, i, "text", mod, w, line.strip()))
                        break
    return out


def file_context(repo: Path, rel: str, line: int, radius: int = 3) -> str:
    lines = (repo / rel).read_text(encoding="utf-8", errors="replace").splitlines()
    lo, hi = max(0, line - 1 - radius), min(len(lines), line + radius)
    return "\n".join(f"{n + 1:>4}| {lines[n]}" for n in range(lo, hi))
