"""Automated tests validating is.sh suite execution, tutorial/howto predicates, Diataxis, STE, and Mermaid."""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest
from urllib.parse import unquote

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
REQUIRED_QUADRANTS = ("01-tutorials", "02-how-to-guides", "03-reference", "04-explanation")

FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\n]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ASCII_BOX_RE = re.compile(r"[┌┐└┘├┤┬┴┼═║╔╗╚╝]|^\s*\+[-+]+\+\s*$", re.M)
MERMAID_TYPES = ("graph ", "flowchart ", "sequenceDiagram", "classDiagram", "stateDiagram", "erDiagram")


def _posix_bash() -> str | None:
    if os.name != "posix":
        return None
    return shutil.which("bash")


def _github_anchor_slug(heading_text: str) -> str:
    cleaned = re.sub(r"`([^`]+)`", r"\1", heading_text.strip().lower())
    out: list[str] = []
    for ch in cleaned:
        if ch.isalnum() or ch == "_":
            out.append(ch)
        elif ch in (" ", "-"):
            out.append("-")
    return "".join(out)


def _split_fenced_blocks(text: str) -> tuple[list[tuple[int, str]], list[tuple[int, str, str]], bool]:
    non_code: list[tuple[int, str]] = []
    blocks: list[tuple[int, str, str]] = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    fence_lang = ""
    fence_start = 0
    buf: list[str] = []

    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        m = FENCE_RE.match(line)
        if not in_fence:
            if m:
                marker = m.group(1)
                in_fence = True
                fence_char = marker[0]
                fence_len = len(marker)
                fence_lang = stripped[fence_len:].strip().split()[0].lower() if stripped[fence_len:].strip() else ""
                fence_start = lineno
                buf = []
                continue
            non_code.append((lineno, line))
        else:
            if stripped.startswith(fence_char * fence_len) and stripped[fence_len:].strip() == "":
                blocks.append((fence_start, fence_lang, "\n".join(buf)))
                in_fence = False
                buf = []
            else:
                buf.append(line)

    return non_code, blocks, in_fence


class TestIsShExecutionAndMetadata(unittest.TestCase):
    """Validate package metadata, bash -n syntax, existing 116-test harness, and tutorial predicates."""

    def test_package_metadata_and_script_presence(self) -> None:
        pkg = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(pkg["name"], "is.sh")
        self.assertEqual(pkg["version"], "1.1.2")
        self.assertTrue((REPO_ROOT / pkg["bin"]["is"]).is_file())
        self.assertTrue((REPO_ROOT / "tests" / "tests.sh").is_file())
        self.assertTrue((REPO_ROOT / "tests" / "assert.sh").is_file())

    def test_bash_syntax_existing_suite_and_tutorial_predicates(self) -> None:
        bash_bin = _posix_bash()
        if bash_bin is None:
            self.skipTest("POSIX bash required to run bash -n, tests/tests.sh, and live is.sh checks.")

        for rel in ("is.sh", "tests/assert.sh", "tests/tests.sh"):
            chk = subprocess.run([bash_bin, "-n", str(REPO_ROOT / rel)], capture_output=True, text=True, check=False)
            self.assertEqual(chk.returncode, 0, f"bash -n failed for {rel}: {chk.stderr}")

        # Run full upstream+fork 116-test suite
        suite = subprocess.run([bash_bin, str(REPO_ROOT / "tests" / "tests.sh")], capture_output=True, text=True, check=False)
        self.assertEqual(suite.returncode, 0, f"{suite.stdout}\n{suite.stderr}")
        self.assertIn("all 116 tests passed", suite.stdout)

        # Execute real sourced and CLI tutorial & how-to snippets inside a temp directory
        with tempfile.TemporaryDirectory() as tmp:
            sample = pathlib.Path(tmp) / "sample.txt"
            sample.write_text("hello", encoding="utf-8")
            os.chmod(sample, 0o640)
            script = f"""
            set -e
            source "{REPO_ROOT / 'is.sh'}"
            is equal 42 42.0
            is gt 10.5 2
            is matching '^[a-z]+$' "hello"
            is not a number "abc"
            is number "42"
            is not lt "42" "10"
            "{REPO_ROOT / 'is.sh'}" a file "{sample}"
            "{REPO_ROOT / 'is.sh'}" fsize "{sample}" 5
            "{REPO_ROOT / 'is.sh'}" forights "{sample}" 640
            "{REPO_ROOT / 'is.sh'}" user "$(whoami)"
            """
            res = subprocess.run([bash_bin, "-c", script], capture_output=True, text=True, check=False)
            self.assertEqual(res.returncode, 0, f"{res.stdout}\n{res.stderr}")


class TestDocsDiataxisSTEAndDiagrams(unittest.TestCase):
    """Validate Diataxis layout, ASD-STE100 rules, links, Mermaid, and English isolation."""

    def test_diataxis_structure_ste_and_english_isolation(self) -> None:
        self.assertTrue((DOCS_DIR / "index.md").is_file())
        for q in REQUIRED_QUADRANTS:
            qdir = DOCS_DIR / q
            self.assertTrue(qdir.is_dir())
            self.assertTrue((qdir / "index.md").is_file())
            self.assertTrue([p for p in qdir.glob("*.md") if p.name != "index.md"])

        howtos = [p for p in (DOCS_DIR / "02-how-to-guides").glob("*.md") if p.name != "index.md"]
        for md in howtos:
            non_code, _, _ = _split_fenced_blocks(md.read_text(encoding="utf-8"))
            body = "\n".join(ln for _, ln in non_code)
            self.assertRegex(body, r"(?im)^##\s+Validation")
            self.assertRegex(body, r"(?im)^##\s+Rollback")
            for lineno, line in non_code:
                s = line.strip()
                if not s or s.startswith(("#", "|", "NOTE:", ">")):
                    continue
                self.assertNotIn(";", s, f"{md.name}:{lineno}: semicolon violates STE")
                self.assertNotRegex(s, r"\b(should|would|may|might|shall)\b")
                clean = re.sub(r"`[^`]+`|\[([^\]]+)\]\([^)]+\)", r"\1", re.sub(r"^\d+\.\s+|^-\s+", "", s))
                for sent in [p.strip() for p in re.split(r"(?<=[.!?])\s+", clean) if p.strip()]:
                    words = [w for w in sent.split() if re.search(r"[A-Za-z0-9]", w)]
                    self.assertLessEqual(len(words), 20, f"{md.name}:{lineno} > 20 words: {sent}")

        for md in sorted(REPO_ROOT.rglob("*.md")):
            non_code, _, _ = _split_fenced_blocks(md.read_text(encoding="utf-8"))
            prose = "\n".join(ln for _, ln in non_code)
            self.assertNotRegex(prose, r"\b(Voici|Étape|Procédure|Vérification|dépôt)\b")

    def test_links_fences_zero_ascii_and_mermaid(self) -> None:
        errors: list[str] = []
        mermaid_count = 0
        for md in sorted(REPO_ROOT.rglob("*.md")):
            rel = md.relative_to(REPO_ROOT).as_posix()
            txt = md.read_text(encoding="utf-8")
            non_code, blocks, unclosed = _split_fenced_blocks(txt)
            if unclosed:
                errors.append(f"{rel}: unclosed fenced block")
            if ASCII_BOX_RE.search(txt):
                errors.append(f"{rel}: ASCII/Unicode box diagram found")

            slugs = {_github_anchor_slug(m.group(2)) for _, ln in non_code if (m := HEADING_RE.match(ln))}
            for lineno, line in non_code:
                for m in LINK_RE.finditer(line):
                    tgt = m.group(1).strip().split()[0]
                    if tgt.startswith(("http://", "https://", "mailto:")):
                        continue
                    if tgt.startswith("#"):
                        if tgt[1:] not in slugs:
                            errors.append(f"{rel}:{lineno}: broken anchor {tgt}")
                        continue
                    fpart, _, frag = tgt.partition("#")
                    resolved = (md.parent / unquote(fpart)).resolve()
                    if not (resolved.is_file() or resolved.is_dir()):
                        errors.append(f"{rel}:{lineno}: missing link target {tgt}")
                    elif frag and resolved.is_file():
                        t_nc, _, _ = _split_fenced_blocks(resolved.read_text(encoding="utf-8"))
                        t_slugs = {_github_anchor_slug(hm.group(2)) for _, ln in t_nc if (hm := HEADING_RE.match(ln))}
                        if frag not in t_slugs:
                            errors.append(f"{rel}:{lineno}: broken target anchor #{frag}")

            for start_line, lang, code in blocks:
                first_tok = code.strip().splitlines()[0].strip() if code.strip() else ""
                if lang == "mermaid":
                    mermaid_count += 1
                    if not any(first_tok.startswith(pfx) for pfx in MERMAID_TYPES):
                        errors.append(f"{rel}:{start_line}: invalid Mermaid header '{first_tok}'")
                    if code.count("[") != code.count("]") or code.count("{") != code.count("}"):
                        errors.append(f"{rel}:{start_line}: unbalanced Mermaid brackets")
                elif any(first_tok.startswith(pfx) for pfx in MERMAID_TYPES):
                    errors.append(f"{rel}:{start_line}: untagged Mermaid block")

            for lineno, line in enumerate(txt.splitlines(), 1):
                if line.lstrip().startswith("```mermaid") and not line.startswith("```mermaid"):
                    errors.append(f"{rel}:{lineno}: indented ```mermaid fence")

        self.assertGreaterEqual(mermaid_count, 4)
        self.assertEqual(errors, [], "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
