"""Unit tests for DepExit's deterministic parts. Run: python -m pytest depexit_tests"""
import textwrap
from pathlib import Path

from depexit.analyze import DepProfile
from depexit.env import modules_in_traceback, short_paths
from depexit.gemma import extract_json
from depexit.manifest import normalize, read_manifest, spec_conflicts
from depexit.migrate import apply_code_edits, apply_requirement_changes
from depexit.scan import scan, text_references


def make_repo(tmp_path: Path) -> Path:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "a.py").write_text(textwrap.dedent("""
        import json
        import requests
        from jinja2 import Environment, select_autoescape
        from requests.utils import _private_helper
        from . import b

        def go():
            return Environment(autoescape=select_autoescape(["html"]))

        requests.Session.request = go
    """))
    (tmp_path / "pkg" / "b.py").write_text("X = 1\n")
    (tmp_path / "requirements.txt").write_text("Jinja2==2.11.3\nrequests>=2\nsix\n# PyYAML==5.1\n")
    (tmp_path / "requirements-dev.txt").write_text("pytest\nnose==1.3.7\n")
    (tmp_path / "pyproject.toml").write_text(textwrap.dedent("""
        [project]
        name = "pkg"
        requires-python = ">=3.10"
        dependencies = [
            "Jinja2>=3",
            "requests>=2",
            "six",
        ]
    """))
    (tmp_path / "Makefile").write_text("test:\n\tnosetests tests/\n")
    return tmp_path


def test_normalize():
    assert normalize("Jinja2") == normalize("jinja2") == "jinja2"
    assert normalize("python_dateutil") == "python-dateutil"


def test_manifest_and_conflicts(tmp_path):
    repo = make_repo(tmp_path)
    m = read_manifest(repo)
    keys = {d.key for d in m.declarations}
    assert {"jinja2", "requests", "six", "pytest", "nose"} <= keys
    assert m.requires_python == ">=3.10"
    assert [c.raw for c in m.commented] == ["# PyYAML==5.1"]
    conflicts = {c["package"] for c in spec_conflicts(m)}
    assert conflicts == {"jinja2"}
    groups = {d.key: d.group for d in m.declarations if d.file.endswith(".txt")}
    assert groups["nose"] == "dev" and groups["jinja2"] == "runtime"


def test_scan_finds_imports_private_api_and_monkeypatch(tmp_path):
    repo = make_repo(tmp_path)
    s = scan(repo)
    kinds = {(u.kind, u.module) for u in s.usages}
    assert ("import", "requests") in kinds
    assert ("from-import", "jinja2") in kinds
    assert ("private-api", "requests") in kinds
    assert ("monkeypatch", "requests") in kinds
    assert "json" not in s.modules()          # stdlib ignored
    assert "pkg" not in s.modules()           # local package ignored
    refs = [u for u in s.usages if u.kind == "reference" and u.module == "jinja2"]
    assert any("Environment" in u.symbol for u in refs)


def test_text_references_find_cli_usage(tmp_path):
    repo = make_repo(tmp_path)
    hits = text_references(repo, {"nose": {"nose", "nosetests"}})
    assert [(h.file, h.line) for h in hits] == [("Makefile", 2)]


def test_traceback_blames_innermost_frame_and_message_module():
    tb = (".venv/lib/python3.12/site-packages/click/core.py:12: in invoke\n"
          ".venv/lib/python3.12/site-packages/jinja2/filters.py:13: ImportError\n"
          "E ImportError: cannot import name 'soft_unicode' from 'markupsafe' "
          "(/x/site-packages/markupsafe/__init__.py)")
    assert modules_in_traceback(tb) == ["jinja2", "markupsafe"]
    assert "No module named 'imp'" in "ModuleNotFoundError: No module named 'imp'"
    assert modules_in_traceback("ModuleNotFoundError: No module named 'imp'") == ["imp"]


def test_short_paths():
    assert short_paths("from 'x' (/home/a/.venv/lib/python3.12/site-packages/x/__init__.py)") == \
        "from 'x' (site-packages/x/__init__.py)"


def test_extract_json_handles_fences_and_chatter():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! Here it is: {"a": {"b": "}"}} hope it helps') == {"a": {"b": "}"}}
    assert extract_json("no json here") is None


def test_code_edits_exact_fuzzy_and_rejected(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("def f():\n    import toml\n    return toml.load(p)\n")
    res = apply_code_edits(tmp_path, [
        {"file": "m.py", "find": "import toml\nreturn toml.load(p)", "replace": "import tomllib\nreturn tomllib.load(p)"},
        {"file": "m.py", "find": "does not exist", "replace": "x"},
        {"file": "../escape.py", "find": "a", "replace": "b"},
    ])
    assert [r["applied"] for r in res] == [True, False, False]
    assert res[0]["reason"] == "matched ignoring indentation"
    assert f.read_text() == "def f():\n    import tomllib\n    return tomllib.load(p)\n"
    assert res[2]["reason"] == "path outside repository"


def test_requirement_changes_edit_txt_and_pyproject(tmp_path):
    repo = make_repo(tmp_path)
    p = DepProfile(key="six", name="six", declared=[
        {"file": "requirements.txt", "line": 3, "spec": "*", "group": "runtime", "raw": "six"},
        {"file": "pyproject.toml", "line": 8, "spec": "*", "group": "runtime", "raw": "six"}],
        installed_version="1.17.0", modules=["six"], console_scripts=[], relation="direct")
    log = apply_requirement_changes(repo, [{"action": "remove", "package": "six"}],
                                    p, ["requirements-dev.txt", "requirements.txt"])
    assert sorted(log[0]["files"]) == ["pyproject.toml", "requirements.txt"]
    assert "six" not in (repo / "requirements.txt").read_text()
    assert '"six"' not in (repo / "pyproject.toml").read_text()

    j = DepProfile(key="jinja2", name="Jinja2", declared=[
        {"file": "requirements.txt", "line": 1, "spec": "==2.11.3", "group": "runtime", "raw": "Jinja2==2.11.3"}],
        installed_version="2.11.3", modules=["jinja2"], console_scripts=[], relation="direct")
    apply_requirement_changes(repo, [{"action": "set", "package": "jinja2", "requirement": "Jinja2>=3.1.4"}],
                              j, ["requirements.txt"])
    assert (repo / "requirements.txt").read_text().startswith("Jinja2>=3.1.4\n")
    assert '"Jinja2>=3.1.4",' in (repo / "pyproject.toml").read_text()

    c = DepProfile(key="certifi", name="certifi", declared=[], installed_version="2026.1.1",
                   modules=["certifi"], console_scripts=[], relation="undeclared")
    apply_requirement_changes(repo, [{"action": "add", "requirement": "certifi>=2024.2.2"}],
                              c, ["requirements-dev.txt", "requirements.txt"])
    assert "certifi>=2024.2.2" in (repo / "requirements.txt").read_text()
    assert "certifi" not in (repo / "requirements-dev.txt").read_text()
    assert '"certifi>=2024.2.2",' in (repo / "pyproject.toml").read_text()


def test_ssl_context_falls_back_to_a_ca_bundle_when_store_is_empty(monkeypatch):
    """Simulates python.org macOS builds that ship without root certificates."""
    import ssl
    from depexit import net
    real = ssl.create_default_context

    def fake(cafile=None, **kw):
        if cafile is None:
            return ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)   # empty trust store
        return real(cafile=cafile)
    monkeypatch.setattr(ssl, "create_default_context", fake)
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    net.ssl_context.cache_clear()
    try:
        ctx = net.ssl_context()
        assert ctx.verify_mode == ssl.CERT_REQUIRED           # verification never disabled
        assert ctx.cert_store_stats()["x509_ca"] > 0          # a real bundle was loaded
    finally:
        net.ssl_context.cache_clear()


def test_truncated_reply_is_rejected_not_mined_for_nested_objects():
    """Regression: a Gemma reply cut off mid-object once yielded its inner 'replacement' dict as the plan."""
    from depexit.gemma import extract_json, plan_problems
    truncated = '```json\n{\n  "decision": "upgrade",\n  "replacement": {\n    "package": "requests",\n    "version_spec": "==2.34.2"\n  },\n  "'
    assert extract_json(truncated) is None
    assert extract_json('noise {"bad": } then {"ok": 2}') == {"ok": 2}
    assert plan_problems({"package": "requests"})            # malformed plans are caught
    assert plan_problems({"decision": "upgrade", "rationale": "r", "requirement_changes": [], "code_edits": []}) == \
        ["plan changes nothing: no requirement_changes and no code_edits"]
    assert plan_problems({"decision": "keep", "rationale": "r", "requirement_changes": [], "code_edits": []}) == []
