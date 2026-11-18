#!/usr/bin/env python3
"""Self-test for the audit scripts: build a messy fixture project in a temporary
folder, run every tool end to end, and check the behaviors the skill relies on.

  python3 selftest.py          # prints PASS/FAIL per check, exits 1 on any failure
"""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# A home-directory path for the fixtures, built at runtime so that shipped files hold no literal one.
HOME_FIXTURE = "/" + "Users" + "/x"

HERE = Path(__file__).resolve().parent
PY = sys.executable
results: list[tuple[bool, str]] = []


def check(ok: bool, what: str) -> None:
    results.append((bool(ok), what))


def run(*args, cwd=None, env=None) -> subprocess.CompletedProcess:
    full_env = dict(os.environ, **env) if env else None
    return subprocess.run([PY, *map(str, args)], cwd=cwd, capture_output=True, text=True, env=full_env)


def write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def build(root: Path) -> None:
    write(root, "README.md", "# Demo\nRun: `Rscript analysis/pipeline.R`\n")
    write(root, "PROJECT_HANDOFF.md", "handoff\n")
    write(root, "data/raw/cohort.csv",
          "id,age,sex,bmi_kg_m2,smoker,unused_var,status\n1,54,F,27.1,1,a,1\n2,61,M,31.0,0,b,0\n")
    shutil.copy(root / "data/raw/cohort.csv", root / "data/cohort_copy.csv")
    write(root, "analysis/pipeline.R",
          'source("analysis/scripts/prep.R")\nsource(here::here("analysis", "scripts", "models.R"))\n')
    write(root, "analysis/scripts/prep.R",
          'd <- read.csv(here::here("data", "raw", "cohort.csv"))\n'
          'd$bmi <- d$bmi_kg_m2\nwrite.csv(d, "data/processed/analytic.csv")\n')
    write(root, "analysis/scripts/models.R",
          'set.seed(1)\nd <- read.csv("data/processed/analytic.csv")\n'
          'fit <- glm(status ~ age + sex + smoker + bmi, data = d)\n'
          'for (o in c("death", "mi")) write.csv(1, paste0("results/tables/model_", o, ".csv"))\n'
          'x <- sprintf("%s.rds", o)\n')
    write(root, "analysis_v2.R", 'setwd("' + HOME_FIXTURE + '/p")\nidx <- sample(1:3)\n'
                                  'write.csv(1, "results/table1.csv")\n')
    write(root, "scripts/fetch.py",
          'from pathlib import Path\nROOT = Path(__file__).resolve().parents[1]\n'
          'RAW = ROOT / "data" / "raw"\nimport csv\n'
          'def save(rows, seed: int = 7):\n    open(RAW / "cohort.csv", "w").write("x")\n')
    write(root, "_GPT/explore.R", 'setwd("' + HOME_FIXTURE + '")\n')
    write(root, "results/tables/model_death.csv", "term,estimate\nage,0.04173\nsmoker,0.6931\n")
    write(root, "results/tables/model_mi.csv", "term,estimate\nage,0.02\n")
    write(root, "results/table1.csv", "characteristic,overall\nN,1247\nAge mean,61.37\n")
    write(root, "results/orphan.csv", "a\n1\n")
    write(root, ".DS_Store", "")
    write(root, "manuscript/manuscript.md",
          "# Title\n\n## Abstract\n\n**Results**  Among 1,247 patients (mean age 61.4 years), each year "
          "of age raised the odds by 4.3%. Women were 116/312 (37.9%) of the sample.\n\n"
          "**Conclusions**  Age was associated with death. These findings should be interpreted "
          "with caution, and causal inference cannot be established.\n\n"
          "## Results\n\nThe estimate was 1.87 and may possibly reflect limited power.\n\n"
          "## Discussion\n\nAge appeared to be associated with death.\n\n"
          "This study has several limitations. First, the sample was small.\n")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="sia_selftest_"))
    root, out = tmp / "proj", tmp / "out"
    root.mkdir()
    out.mkdir()
    try:
        build(root)
        # inventory scan
        r = run(HERE / "inventory.py", "scan", "--root", root, "--label", "before", "--out-dir", out)
        check(r.returncode == 0, "inventory scan runs")
        rows = {x["path"]: x for x in csv.DictReader(open(out / "manifest_before.csv"))}
        fl = lambda p: rows[p]["flags"]  # noqa: E731
        check("entrypoint" in fl("analysis/pipeline.R"), "README-named pipeline is an entry point")
        check("legacy_name:v2" in fl("analysis_v2.R") and "setwd_or_chdir" in fl("analysis_v2.R"),
              "versioned name and setwd flagged")
        check("random_without_seed" in fl("analysis_v2.R"), "unseeded randomness flagged")
        check("random_without_seed" not in fl("scripts/fetch.py"), "seed given as a default is seen")
        check("writes_raw" in fl("scripts/fetch.py"), "code writing into data/raw flagged")
        check("dynamic_name" in fl("results/tables/model_death.csv"), "runtime-built output name traced")
        check("untraceable_output" in fl("results/orphan.csv"), "orphan output flagged")
        check(rows["_GPT/explore.R"]["category"] == "agent_workspace"
              and "setwd_or_chdir" not in fl("_GPT/explore.R"), "agent workspace treated as inactive")
        check("duplicate_of:data/raw/cohort.csv" in fl("data/cohort_copy.csv"), "copy of raw data found")
        check(not any(f.startswith("ungenerated:s.rds") for f in fl("analysis/scripts/models.R").split(";")),
              "format-string names ignored")

        # safe_move: bad plan rejected, good plan applied, verify passes
        (out / "bad.csv").write_text("action,src,dst,reason\n"
                                     "delete_junk,results/orphan.csv,,not junk\n"
                                     "archive,data/raw/cohort.csv,,raw\n")
        r = run(HERE / "safe_move.py", "--root", root, "--plan", out / "bad.csv", "--log", out / "moves.csv")
        check(r.returncode == 2 and not (out / "moves.csv").exists(), "unsafe plan rejected, nothing logged")
        (out / "plan.csv").write_text(
            "action,src,dst,reason\n"
            "mkdir,,archive/superseded,\n"
            "archive,analysis_v2.R,archive/superseded/,superseded\n"
            "archive,_GPT,archive/agent_workspaces/_GPT,agent scratch\n"
            "archive,data/cohort_copy.csv,,copy of raw\n"
            "move,results/table1.csv,results/tables/baseline.csv,content name\n"
            "move,scripts/fetch.py,analysis/scripts/fetch.py,one code tree\n"
            "delete_junk,.DS_Store,,junk\n")
        r = run(HERE / "safe_move.py", "--root", root, "--plan", out / "plan.csv", "--log", out / "moves.csv")
        check(r.returncode == 0 and "locates files relative to itself" in r.stdout,
              "dry run passes and warns about self-locating script")
        shutil.copytree(root / "results", tmp / "baseline_results")
        r = run(HERE / "safe_move.py", "--root", root, "--plan", out / "plan.csv", "--log", out / "moves.csv",
                "--apply")
        check(r.returncode == 0 and (root / "archive/superseded/analysis_v2.R").exists(),
              "plan applied; archive into folder works")
        run(HERE / "inventory.py", "scan", "--root", root, "--label", "after", "--out-dir", out)
        r = run(HERE / "inventory.py", "verify", "--before", out / "manifest_before.csv",
                "--after", out / "manifest_after.csv", "--moves", out / "moves.csv")
        check(r.returncode == 0 and "PASS" in r.stdout, "reconciliation passes after logged moves")
        (root / "results/orphan.csv").unlink()
        run(HERE / "inventory.py", "scan", "--root", root, "--label", "tampered", "--out-dir", out)
        r = run(HERE / "inventory.py", "verify", "--before", out / "manifest_before.csv",
                "--after", out / "manifest_tampered.csv", "--moves", out / "moves.csv")
        check(r.returncode == 1 and "missing and not logged" in r.stdout, "unlogged deletion fails")

        # compare_outputs
        r = run(HERE / "compare_outputs.py", tmp / "baseline_results", root / "results",
                "--moves", out / "moves.csv")
        check(r.returncode == 1 and "DIFFERENT" in r.stdout and "orphan.csv" in r.stdout,
              "missing output reported as DIFFERENT")
        (root / "results/tables/model_death.csv").write_text("term,extra,estimate\nsmoker,x,0.70\nage,y,0.04173\n")
        r = run(HERE / "compare_outputs.py", tmp / "baseline_results", root / "results",
                "--moves", out / "moves.csv")
        check("columns only in after: extra" in r.stdout and "smoker, estimate" in r.stdout
              and "1 cells differ" in r.stdout, "tables aligned by header and key")

        # trace_numbers
        r = run(HERE / "trace_numbers.py", "--doc", root / "manuscript/manuscript.md",
                "--outputs", tmp / "baseline_results", "--out-csv", out / "trace.csv")
        trace = {(x["number"], x["status"]) for x in csv.DictReader(open(out / "trace.csv"))}
        check(("1.87", "unmatched") in trace, "invented number unmatched")
        check(("1,247", "found") in trace and ("61.4", "found") in trace,
              "reported numbers found (as candidate sources)")
        check(("4.3%", "derived") in trace, "percent change derived from a ratio")
        check(("37.9%", "mismatch") in trace, "n/N (x%) arithmetic error caught")

        # hedge_lint
        r = run(HERE / "hedge_lint.py", root / "manuscript/manuscript.md", "--json")
        check("Abstract conclusion ends on a qualifier" in r.stdout
              and "Caveats in results" in r.stdout, "hedges and misplaced caveats found")

        # column_usage
        r = run(HERE / "column_usage.py", "--root", root, "--data", "data/raw",
                "--out-csv", out / "cols.csv")
        cols = {x["column"]: x["used"] for x in csv.DictReader(open(out / "cols.csv"))}
        check(cols.get("unused_var") == "no" and cols.get("age") == "yes", "unused variable found")
        check(cols.get("bmi_kg_m2") == "yes", "unit-suffixed column matched to its short name")

        # ---- regressions for defects found in independent review (2026-09-26) ----
        reg = tmp / "reg"
        # comparator: duplicate explicit keys must not hide a changed value
        write(reg, "c1/a/t.csv", "term,est\nage,1.25\n")
        write(reg, "c1/b/t.csv", "term,est\nage,9.99\nage,1.25\n")
        r = run(HERE / "compare_outputs.py", reg / "c1/a", reg / "c1/b", "--key", "term")
        check(r.returncode == 1 and "not unique" in r.stdout, "duplicate keys cannot hide a change")
        # comparator: headerless table gaining a column is a difference
        write(reg, "c2/a/t.csv", "1,2\n")
        write(reg, "c2/b/t.csv", "1,2,999\n")
        r = run(HERE / "compare_outputs.py", reg / "c2/a", reg / "c2/b")
        check(r.returncode == 1, "headerless extra column is a difference")
        # comparator: figures whose bytes differ are 'not checked', so the verdict is PARTIAL
        (reg / "c3/a").mkdir(parents=True)
        (reg / "c3/b").mkdir(parents=True)
        (reg / "c3/a/fig.png").write_bytes(b"\x89PNG-a")
        (reg / "c3/b/fig.png").write_bytes(b"\x89PNG-b")
        r = run(HERE / "compare_outputs.py", reg / "c3/a", reg / "c3/b")
        check(r.returncode == 2 and "PARTIAL" in r.stdout, "unverifiable binaries give PARTIAL, not a pass")

        def plan(dirname: str, rows: str) -> Path:
            f = reg / dirname / "plan.csv"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("action,src,dst,reason\n" + rows)
            return f
        # safe_move: a folder containing raw data is raw data
        write(reg, "s1/data/raw/r.csv", "x\n")
        r = run(HERE / "safe_move.py", "--root", reg / "s1",
                "--plan", plan("s1_plan", "archive,data,,parent of raw\n"), "--log", reg / "s1.log")
        check(r.returncode == 2 and "raw data is protected" in r.stdout + r.stderr,
              "moving a parent of raw data needs the flag")
        # safe_move: a symlinked folder cannot lead outside the root
        (reg / "s2/proj").mkdir(parents=True)
        (reg / "s2/outside").mkdir(parents=True)
        (reg / "s2/proj/linkdir").symlink_to(reg / "s2/outside")
        write(reg, "s2/proj/f.csv", "y\n")
        r = run(HERE / "safe_move.py", "--root", reg / "s2/proj",
                "--plan", plan("s2_plan", "move,f.csv,linkdir/f.csv,escape\n"), "--log", reg / "s2.log")
        check(r.returncode == 2 and "outside the project root" in r.stdout + r.stderr,
              "symlinked folder cannot lead a move outside the root")
        # safe_move: junk folders must hold only junk; notebook checkpoints are archived, not deleted
        write(reg, "s3/__pycache__/results.csv", "important\n")
        write(reg, "s3/.ipynb_checkpoints/nb-checkpoint.ipynb", "{}\n")
        r = run(HERE / "safe_move.py", "--root", reg / "s3",
                "--plan", plan("s3_plan", "delete_junk,__pycache__,,junk\ndelete_junk,.ipynb_checkpoints,,junk\n"),
                "--log", reg / "s3.log")
        out = r.stdout + r.stderr
        check(r.returncode == 2 and "other than bytecode" in out and "checkpoints" in out,
              "junk deletion refuses real files and notebook checkpoints")
        # safe_move: a failed step reports INCOMPLETE and exits non-zero
        write(reg, "s4/a.csv", "z\n")
        write(reg, "s4/b", "a file where a folder is expected\n")
        r = run(HERE / "safe_move.py", "--root", reg / "s4",
                "--plan", plan("s4_plan", "move,a.csv,b/c.csv,test\n"), "--log", reg / "s4.log", "--apply")
        check(r.returncode == 1 and "INCOMPLETE" in r.stderr, "failed move is reported as INCOMPLETE")
        # safe_move: the plan cannot move the move log
        write(reg, "s5/docs/audit/notes.md", "n\n")
        r = run(HERE / "safe_move.py", "--root", reg / "s5",
                "--plan", plan("s5_plan", "move,docs,documentation,rename\n"),
                "--log", reg / "s5/docs/audit/file_moves.csv")
        check(r.returncode == 2 and "move log" in r.stdout + r.stderr, "plan cannot move the move log")

        # inventory verify: missing raw hashes -> UNVERIFIED; archive changes -> FAIL; edits listed
        v = reg / "v"
        write(v, "data/raw/r.csv", "1,2\n")
        write(v, "archive/old.R", "x <- 1\n")
        write(v, "analysis/a.R", "y <- 1\n")
        run(HERE / "inventory.py", "scan", "--root", v, "--label", "nohash", "--out-dir", reg / "vo",
            "--hash", "none")
        run(HERE / "inventory.py", "scan", "--root", v, "--label", "b", "--out-dir", reg / "vo")
        r = run(HERE / "inventory.py", "verify", "--before", reg / "vo/manifest_nohash.csv",
                "--after", reg / "vo/manifest_b.csv")
        check(r.returncode == 3 and "UNVERIFIED" in r.stdout, "missing raw hashes give UNVERIFIED, not PASS")
        (v / "analysis/a.R").write_text("y <- 2\n")
        run(HERE / "inventory.py", "scan", "--root", v, "--label", "c", "--out-dir", reg / "vo")
        r = run(HERE / "inventory.py", "verify", "--before", reg / "vo/manifest_b.csv",
                "--after", reg / "vo/manifest_c.csv", "--out-md", reg / "vo/v1.md")
        check(r.returncode == 0 and "analysis/a.R" in (reg / "vo/v1.md").read_text(),
              "edited code passes but is listed for confirmation")
        (v / "archive/old.R").write_text("x <- 9\n")
        run(HERE / "inventory.py", "scan", "--root", v, "--label", "d", "--out-dir", reg / "vo")
        r = run(HERE / "inventory.py", "verify", "--before", reg / "vo/manifest_b.csv",
                "--after", reg / "vo/manifest_d.csv")
        check(r.returncode == 1 and "archived file changed" in r.stdout, "a changed archived file fails")

        # ---- second independent review (Codex, 2026-09-26): adversarial cases ----
        adv = tmp / "adv"

        def fixture(name: str) -> Path:
            d = adv / name
            (d / "proj").mkdir(parents=True)
            (d / "outside").mkdir()
            return d

        def sm(d: Path, rows: str, *extra) -> subprocess.CompletedProcess:
            (d / "plan.csv").write_text("action,src,dst,reason\n" + rows)
            return run(HERE / "safe_move.py", "--root", d / "proj", "--plan", d / "plan.csv",
                       "--log", d / "proj/docs/audit/file_moves.csv", *extra)

        d = fixture("mkdir_escape")
        (d / "proj/link").symlink_to(d / "outside")
        r = sm(d, "mkdir,,link/escaped,\n", "--apply")
        check(r.returncode == 2 and not (d / "outside/escaped").exists(), "mkdir cannot escape through a symlink")
        d = fixture("delete_escape")
        (d / "proj/link").symlink_to(d / "outside")
        (d / "outside/.DS_Store").write_text("x")
        r = sm(d, "delete_junk,link/.DS_Store,,junk\n", "--apply")
        check(r.returncode == 2 and (d / "outside/.DS_Store").exists(), "delete cannot escape through a symlink")
        d = fixture("cache_raw")
        write(d, "proj/.pytest_cache/data/raw/patient.csv", "1\n")
        write(d, "proj/.pytest_cache/manuscript.md", "text\n")
        r = sm(d, "delete_junk,.pytest_cache,,cache\n", "--apply")
        check(r.returncode == 2 and (d / "proj/.pytest_cache/manuscript.md").exists(),
              "tool caches are archived, never deleted")
        d = fixture("move_into_pycache")
        write(d, "proj/__pycache__/m.cpython-313.pyc", "b")
        write(d, "proj/manuscript.md", "text\n")
        r = sm(d, "move,manuscript.md,__pycache__/manuscript.md,x\ndelete_junk,__pycache__,,junk\n", "--apply")
        check(r.returncode == 2 and (d / "proj/manuscript.md").exists(),
              "a folder the plan fills cannot then be deleted")
        d = fixture("raw_alias")
        write(d, "proj/data/raw/patient.csv", "1\n")
        (d / "proj/alias").symlink_to(d / "proj/data/raw")
        r = sm(d, "move,alias/patient.csv,patient.csv,x\n", "--apply")
        check(r.returncode == 2 and (d / "proj/data/raw/patient.csv").exists(),
              "a symlink alias cannot bypass raw-data protection")
        d = fixture("log_dest")
        write(d, "proj/important.csv", "data\n")
        r = sm(d, "move,important.csv,docs/audit/file_moves.csv,x\n", "--apply")
        check(r.returncode == 2 and (d / "proj/important.csv").exists(), "nothing can be moved onto the move log")
        d = fixture("planned_link")
        (d / "proj/link").symlink_to(d / "outside")
        (d / "outside/a.txt").write_text("outside\n")
        r = sm(d, "move,link,relocated_link,x\nmove,relocated_link/a.txt,a.txt,x\n", "--apply")
        check(r.returncode == 2 and (d / "outside/a.txt").exists(),
              "renaming a symlink first cannot smuggle a move outside")
        d = fixture("git_alias")
        write(d, "proj/.git/HEAD", "ref\n")
        (d / "proj/alias").symlink_to(d / "proj/.git")
        r = sm(d, "move,alias/HEAD,removed_HEAD,x\n", "--apply")
        check(r.returncode == 2 and (d / "proj/.git/HEAD").exists(), "a symlink alias cannot reach .git")

        cmpd = adv / "cmp"

        def cmp(name: str, before: str, after: str, *extra) -> subprocess.CompletedProcess:
            write(cmpd, f"{name}/a/t.csv", before)
            write(cmpd, f"{name}/b/t.csv", after)
            return run(HERE / "compare_outputs.py", cmpd / f"{name}/a", cmpd / f"{name}/b", *extra)

        r = cmp("dupkey_col", "term,est\nage,1.25\nage,2.50\n", "term,est,new\nage,1.25,99\nage,2.50,999\n",
                "--key", "term")
        check(r.returncode == 1, "duplicate keys cannot hide an added column")
        r = cmp("ragged", "term,estimate\nage,1.25\n", "term,estimate\nage,1.25,999\n")
        check(r.returncode == 1, "extra cells beyond the header are a difference")
        r = cmp("dup_header", "term,value,value,value [2]\nage,1,2,99\n", "term,value,value,value [2]\nage,1,2,999\n")
        check(r.returncode == 1, "repeated column names cannot hide a changed column")
        r = run(HERE / "compare_outputs.py", cmpd / "missing_a", cmpd / "missing_b")
        check(r.returncode == 3, "missing folders are an error, not a verified comparison")

        inv = adv / "inv"

        def inv_verify(name: str, change, *scan_extra) -> subprocess.CompletedProcess:
            proj = inv / name
            change(proj, False)
            run(HERE / "inventory.py", "scan", "--root", proj, "--label", "b", "--out-dir", inv / f"{name}_o",
                *scan_extra)
            change(proj, True)
            run(HERE / "inventory.py", "scan", "--root", proj, "--label", "a", "--out-dir", inv / f"{name}_o")
            return run(HERE / "inventory.py", "verify", "--before", inv / f"{name}_o/manifest_b.csv",
                       "--after", inv / f"{name}_o/manifest_a.csv")

        def raw_json(proj: Path, after: bool):
            write(proj, "data/raw/api.json", '{"n": 9}\n' if after else '{"n": 1}\n')
        r = inv_verify("raw_json", raw_json)
        check(r.returncode == 1 and "raw data changed" in r.stdout, "raw JSON under data/raw is protected")

        def raw_link(proj: Path, after: bool):
            write(proj, "inputs/a.csv", "n\n1\n")
            write(proj, "inputs/b.csv", "n\n9\n")
            link = proj / "data/raw/cohort.csv"
            link.parent.mkdir(parents=True, exist_ok=True)
            if link.is_symlink():
                link.unlink()
            link.symlink_to("../../inputs/b.csv" if after else "../../inputs/a.csv")
        r = inv_verify("raw_link", raw_link)
        check(r.returncode == 1, "a retargeted raw symlink is caught")

        def archive_nohash(proj: Path, after: bool):
            write(proj, "archive/old.R", "x <- 2\n" if after else "x <- 1\n")
        r = inv_verify("archive_nohash", archive_nohash, "--hash", "none")
        check(r.returncode == 3, "an archived file without identity evidence is UNVERIFIED, not PASS")

        # ---- the audit workspace ----
        AW = HERE / "audit_workspace.py"
        NOCLONE = {"AUDIT_WS_NO_CLONE": "1"}

        def manifest_rows(proj: Path) -> dict:
            with open(proj / "_audit/MANIFEST.tsv", newline="") as fh:
                return {r["path"]: r for r in csv.DictReader(fh, delimiter="\t")}

        def record(proj: Path) -> Path | None:
            return next((proj / "archive").glob("audit_*"), None)

        wsp = adv / "ws"
        write(wsp, "data/raw/cohort.csv", "id,y\n1,0\n")
        write(wsp, "analysis/run.py", "print('hi')\n")
        write(wsp, "manuscript/paper.md", "# Paper\n")
        r = run(AW, "open", "--root", wsp)
        rows_m = manifest_rows(wsp) if r.returncode == 0 else {}
        check(r.returncode == 0 and (wsp / "_audit/baseline/analysis/run.py").exists()
              and (wsp / "_audit/work/data/raw/cohort.csv").is_file()
              and not (wsp / "_audit/work/data/raw/cohort.csv").is_symlink()
              and rows_m.get("data/raw/cohort.csv", {}).get("disposition", "").startswith("raw"),
              "workspace opens: isolated working copy with raw data, manifest marks raw data")
        write(wsp, "_audit/work/data/raw/new_source/fetch.csv", "x\n")
        (wsp / "_audit/work/data/raw/cohort.csv").write_text("tampered\n")
        check(not (wsp / "data/raw/new_source").exists()
              and (wsp / "data/raw/cohort.csv").read_text() == "id,y\n1,0\n",
              "writes in work/, including a new source under raw/, stay in the workspace")
        r = run(HERE / "inventory.py", "scan", "--root", wsp, "--label", "x")
        rows_ws = list(csv.DictReader(open(wsp / "_audit/inventory/manifest_x.csv")))
        check(not any(x["path"].startswith("_audit/") for x in rows_ws), "inventory ignores the workspace")
        (wsp / "analysis/run.py").write_text("print('fixed')\n")
        r = run(AW, "close", "--root", wsp)
        check(r.returncode == 0 and (wsp / "_audit").exists() and "analysis/run.py" in r.stdout,
              "close is a dry run until confirmed")
        r = run(AW, "close", "--root", wsp, "--confirm")
        rec = record(wsp)
        check(r.returncode == 0 and not (wsp / "_audit").exists() and rec is not None
              and (rec / "prior_versions/analysis/run.py").read_text() == "print('hi')\n"
              and (rec / "MANIFEST.tsv").is_file() and (rec / "analysis_register.md").is_file()
              and (wsp / "data/raw/cohort.csv").exists(),
              "close keeps prior versions, the manifest and the register in archive/, then erases")

        wsl = adv / "ws_link"
        write(wsl, "data/raw/big.csv", "id\n1\n")
        write(wsl, "analysis/run.py", "x\n")
        r = run(AW, "open", "--root", wsl, "--copy-raw-max-mb", "0", env=NOCLONE)
        left_out = not os.path.lexists(wsl / "_audit/work/data/raw/big.csv") and "Raw data not in work" in \
            (wsl / "_audit/README.md").read_text()
        run(AW, "close", "--root", wsl, "--confirm")
        r = run(AW, "open", "--root", wsl, "--copy-raw-max-mb", "0", "--allow-links", env=NOCLONE)
        linked = (wsl / "_audit/work/data/raw/big.csv").is_symlink()
        run(AW, "close", "--root", wsl, "--confirm")
        check(left_out and linked and (wsl / "data/raw/big.csv").read_text() == "id\n1\n",
              "uncloneable large raw data is left out unless --allow-links; erasing never follows links")

        wsm = adv / "ws_moves"
        write(wsm, "analysis/a.R", "a <- 1\n")
        write(wsm, "analysis/b.R", "b <- 1\n")
        write(wsm, "old_notes.md", "notes\n")
        write(wsm, "results/big.bin", "x" * 3000)
        run(AW, "open", "--root", wsm, "--max-copy-mb", "0.001", env=NOCLONE)
        big_hashed = len(manifest_rows(wsm)["results/big.bin"]["sha256"]) == 64
        plan = wsm / "_audit/proposal/reorg_plan.csv"
        plan.write_text("action,src,dst,reason\nmove,analysis/a.R,analysis/scripts/a.R,layout\n"
                        "move,analysis/b.R,analysis/scripts/b.R,layout\narchive,old_notes.md,archive/,superseded\n")
        run(HERE / "safe_move.py", "--root", wsm, "--plan", plan, "--apply", "--no-git")
        (wsm / "analysis/scripts/b.R").write_text("b <- 2\n")
        (wsm / "results/big.bin").write_text("y" * 3000)
        r = run(AW, "close", "--root", wsm, "--confirm")
        rec = record(wsm)
        prior = sorted(q.relative_to(rec / "prior_versions").as_posix()
                       for q in (rec / "prior_versions").rglob("*") if q.is_file()) if rec else []
        check(r.returncode == 0 and prior == ["analysis/b.R"]
              and (rec / "prior_versions/analysis/b.R").read_text() == "b <- 1\n",
              "close keeps only edited files' prior versions and follows logged moves")
        check(big_hashed and "results/big.bin" in r.stdout and "NOT PRESERVED" in r.stdout,
              "close names an edited file that could not be preserved; its hash stays in the record")

        # Codex round-3 cases
        c1 = adv / "ws_manifest_name"
        write(c1, "MANIFEST.tsv", "ORIGINAL PROJECT MANIFEST\n")
        run(AW, "open", "--root", c1)
        (c1 / "MANIFEST.tsv").write_text("edited\n")
        run(AW, "close", "--root", c1, "--confirm")
        rec = record(c1)
        check(rec is not None and (rec / "prior_versions/MANIFEST.tsv").read_text() == "ORIGINAL PROJECT MANIFEST\n",
              "a project file named MANIFEST.tsv keeps its own prior version")

        c2 = adv / "ws_ext_links"
        outside = adv / "ws_ext_outside"
        write(outside, "manifest.txt", "EXTERNAL ORIGINAL\n")
        write(outside, "folder/data.csv", "x\n")
        c2.mkdir(parents=True)
        (c2 / "MANIFEST.tsv").symlink_to(outside / "manifest.txt")
        (c2 / "report.csv").symlink_to(outside / "manifest.txt")
        (c2 / "ext_folder").symlink_to(outside / "folder", target_is_directory=True)
        r = run(AW, "open", "--root", c2)
        w2 = c2 / "_audit/work"
        (w2 / "report.csv").write_text("written in work\n")
        check(r.returncode == 0 and (outside / "manifest.txt").read_text() == "EXTERNAL ORIGINAL\n"
              and not (w2 / "report.csv").is_symlink() and not os.path.lexists(w2 / "ext_folder"),
              "links to outside the project never let open or work/ write outside it")
        run(AW, "close", "--root", c2, "--confirm")

        c3 = adv / "ws_arch_link"
        out3 = adv / "ws_arch_outside"
        write(out3, "README.md", "outside readme\n")
        write(c3, "a.txt", "a\n")
        run(AW, "open", "--root", c3)
        (c3 / "a.txt").write_text("b\n")
        (c3 / "archive").symlink_to(out3, target_is_directory=True)
        r1 = run(AW, "close", "--root", c3, "--confirm")
        (c3 / "archive").unlink()
        (c3 / "archive").mkdir()
        (c3 / "archive/README.md").symlink_to(out3 / "README.md")
        r2 = run(AW, "close", "--root", c3, "--confirm")
        (c3 / "archive/README.md").unlink()
        (c3 / "audit_alias").symlink_to(c3 / "_audit", target_is_directory=True)
        r3 = run(AW, "close", "--root", c3, "--confirm")
        check(r1.returncode == 2 and r2.returncode == 2 and r3.returncode == 2
              and (c3 / "_audit").is_dir() and (out3 / "README.md").read_text() == "outside readme\n"
              and not list(out3.glob("audit_*")),
              "close refuses archive links out of the project and links to the workspace itself")
        (c3 / "audit_alias").unlink()
        run(AW, "close", "--root", c3, "--confirm")

        c4 = adv / "ws_names"
        write(c4, "report", "unrelated\n")
        write(c4, "report (now draft).txt", "valuable prior\n")
        (c4 / "current").symlink_to("v1.txt")
        write(c4, "v1.txt", "1\n")
        write(c4, "v2.txt", "2\n")
        run(AW, "open", "--root", c4)
        (c4 / "report (now draft).txt").write_text("edited\n")
        (c4 / "current").unlink()
        (c4 / "current").symlink_to("v2.txt")
        run(AW, "close", "--root", c4, "--confirm")
        rec = record(c4)
        check(rec is not None and (rec / "prior_versions/report (now draft).txt").read_text() == "valuable prior\n"
              and not (rec / "prior_versions/report").exists()
              and "v1.txt" in (rec / "LINKS.tsv").read_text(),
              "close keeps the right file whatever its name, and records changed links")

        c5 = adv / "ws_moved_out"
        out5 = adv / "ws_moved_outside"
        write(c5, "a.txt", "keep me\n")
        run(AW, "open", "--root", c5)
        p5 = c5 / "_audit/proposal/plan.csv"
        p5.write_text("action,src,dst,reason\nmove,a.txt,kept/a.txt,layout\n")
        run(HERE / "safe_move.py", "--root", c5, "--plan", p5, "--apply", "--no-git")
        write(out5, "a.txt", "keep me\n")
        shutil.rmtree(c5 / "kept")
        (c5 / "kept").symlink_to(out5, target_is_directory=True)
        run(AW, "close", "--root", c5, "--confirm")
        rec = record(c5)
        check(rec is not None and (rec / "prior_versions/a.txt").read_text() == "keep me\n",
              "a moved file now reached through a link out of the project gets its prior version kept")

        c6 = adv / "ws_declared_raw"
        write(c6, "measurements/m.csv", "1\n")
        write(c6, "cohort/raw/patient.csv", "p\n")
        run(AW, "open", "--root", c6, "--raw", "measurements")
        run(HERE / "inventory.py", "scan", "--root", c6, "--label", "before")
        (c6 / "measurements/m.csv").write_text("2\n")
        run(HERE / "inventory.py", "scan", "--root", c6, "--label", "after")
        r_inv = run(HERE / "inventory.py", "verify", "--before", c6 / "_audit/inventory/manifest_before.csv",
                    "--after", c6 / "_audit/inventory/manifest_after.csv")
        p6 = c6 / "_audit/proposal/plan.csv"
        p6.write_text("action,src,dst,reason\nmove,measurements/m.csv,m.csv,x\n")
        r_mv = run(HERE / "safe_move.py", "--root", c6, "--plan", p6)
        cats = {x["path"]: x["category"] for x in
                csv.DictReader(open(c6 / "_audit/inventory/manifest_before.csv"))}
        disp = manifest_rows(c6)["cohort/raw/patient.csv"]["disposition"]
        check(r_inv.returncode == 1 and r_mv.returncode == 2 and cats.get("measurements/m.csv") == "raw_data"
              and cats.get("cohort/raw/patient.csv") == "raw_data" and disp.startswith("raw"),
              "a raw location declared at open protects it in every later scan and move")
        (c6 / "measurements/m.csv").write_text("1\n")
        run(AW, "close", "--root", c6, "--confirm")

        c7 = adv / "ws_venv"
        write(c7, ".venv/pyvenv.cfg", "home = /usr/bin\n")
        write(c7, ".venv/marker", "original\n")
        write(c7, "run.py", "print(1)\n")
        run(AW, "open", "--root", c7)
        venv_absent = not os.path.lexists(c7 / "_audit/work/.venv")
        write(c7, "_audit/work/.venv/marker", "changed\n")
        check(venv_absent and (c7 / ".venv/marker").read_text() == "original\n",
              "Python environments are not linked into work/, so installs there cannot touch them")
        run(AW, "close", "--root", c7, "--confirm")

        # Codex round-4 cases
        c8 = adv / "ws_raw_spellings"
        write(c8, "measurements/m.csv", "1\n")
        (c8 / "alias").symlink_to(c8 / "measurements", target_is_directory=True)
        bad = run(AW, "open", "--root", c8, "--raw", "../elsewhere")
        bad_root = run(AW, "open", "--root", c8, "--raw", "/")
        r8 = run(AW, "open", "--root", c8, "--raw", "./alias/")
        declared_txt = (c8 / "_audit/raw_paths.txt").read_text() if r8.returncode == 0 else ""
        run(HERE / "inventory.py", "scan", "--root", c8, "--label", "before")
        cats8 = {x["path"]: x["category"] for x in
                 csv.DictReader(open(c8 / "_audit/inventory/manifest_before.csv"))}
        p8 = c8 / "_audit/proposal/plan.csv"
        p8.write_text("action,src,dst,reason\nmove,alias/m.csv,m.csv,x\nmove,measurements/m.csv,n.csv,x\n")
        mv8 = run(HERE / "safe_move.py", "--root", c8, "--plan", p8)
        check(bad.returncode == 2 and bad_root.returncode == 2 and r8.returncode == 0
              and "measurements" in declared_txt
              and cats8.get("measurements/m.csv") == "raw_data" and mv8.returncode == 2,
              "raw declarations resolve ./, trailing slashes and aliases; outside paths are refused")
        (c8 / "_audit/raw_paths.txt").unlink()
        lost = run(HERE / "inventory.py", "scan", "--root", c8, "--label", "again")
        lost_close = run(AW, "close", "--root", c8, "--confirm")
        check(lost.returncode == 2 and "raw_paths.txt is missing" in lost.stderr
              and lost_close.returncode == 2 and (c8 / "_audit").is_dir(),
              "a lost raw-declaration record stops later scans and close instead of dropping protection")
        write(c8, "_audit/raw_paths.txt", "measurements\n")
        run(AW, "close", "--root", c8, "--confirm")

        c9 = adv / "ws_envs"
        cache = adv / "ws_envs_cache"
        write(cache, "pkg/state.txt", "cache\n")
        write(c9, "renv/activate.R", "# activate\n")
        (c9 / "renv/library").mkdir(parents=True)
        (c9 / "renv/library/pkg").symlink_to(cache / "pkg", target_is_directory=True)
        write(c9, "node_modules/x/index.js", "1\n")
        write(c9, "run.R", "1\n")
        run(AW, "open", "--root", c9)
        w9 = c9 / "_audit/work"
        check((w9 / "renv/activate.R").is_file() and not os.path.lexists(w9 / "renv/library")
              and not os.path.lexists(w9 / "node_modules"),
              "environments are not mirrored: renv setup files only, no library, no node_modules")
        run(AW, "close", "--root", c9, "--confirm")

        c10 = adv / "ws_allow_links"
        write(adv, "ws_allow_links_sibling.txt", "sibling\n")
        c10.mkdir(parents=True)
        (c10 / "ext.txt").symlink_to("../ws_allow_links_sibling.txt")
        run(AW, "open", "--root", c10, "--allow-links")
        tgt = os.readlink(c10 / "_audit/work/ext.txt") if os.path.islink(c10 / "_audit/work/ext.txt") else ""
        check(os.path.isabs(tgt) and Path(tgt).resolve() == (adv / "ws_allow_links_sibling.txt").resolve(),
              "--allow-links keeps an outside link pointing at its real target, not into the workspace")
        run(AW, "close", "--root", c10, "--confirm")

        c11 = adv / "ws_tamper"
        out11 = adv / "ws_tamper_outside.txt"
        out11.write_text("EXTERNAL ORIGINAL\n")
        write(c11, "a.txt", "original\n")
        run(AW, "open", "--root", c11)
        (c11 / "a.txt").write_text("edited\n")
        (c11 / "_audit/baseline/a.txt").unlink()
        (c11 / "_audit/baseline/a.txt").symlink_to(c11 / "_audit/work/a.txt")
        t1 = run(AW, "close", "--root", c11, "--confirm")
        no_partial = not list((c11 / "archive").glob("audit_*")) if (c11 / "archive").exists() else True
        (c11 / "_audit/baseline/a.txt").unlink()
        (c11 / "_audit/baseline/a.txt").write_text("original\n")
        with open(c11 / "_audit/MANIFEST.tsv", "a") as fh:
            fh.write("../../ws_tamper_outside.txt\t9\t" + "0" * 64 + "\tcopied\n")
        t2 = run(AW, "close", "--root", c11, "--confirm")
        check(t1.returncode == 1 and no_partial and t2.returncode == 2 and (c11 / "_audit").is_dir()
              and out11.read_text() == "EXTERNAL ORIGINAL\n",
              "close refuses a tampered baseline or manifest and erases nothing")

        c12 = adv / "ws_hardlink"
        out12 = adv / "ws_hardlink_outside.md"
        write(c12, "archive/README.md", "# Archive\n")
        os.link(c12 / "archive/README.md", out12)
        write(c12, "a.txt", "1\n")
        run(AW, "open", "--root", c12)
        (c12 / "a.txt").write_text("2\n")
        h = run(AW, "close", "--root", c12, "--confirm")
        check(h.returncode == 0 and out12.read_text() == "# Archive\n"
              and "audit_" in (c12 / "archive/README.md").read_text(),
              "close never writes through a hard-linked archive README")
        write(c12, "archive/file_moves.csv", "timestamp\n")
        os.link(c12 / "archive/file_moves.csv", adv / "ws_hardlink_log.csv")
        p12 = c12 / "plan.csv"
        p12.write_text("action,src,dst,reason\nmove,a.txt,b.txt,x\n")
        hm = run(HERE / "safe_move.py", "--root", c12, "--plan", p12, "--apply", "--no-git")
        check(hm.returncode == 2 and (c12 / "a.txt").exists(),
              "safe_move refuses a move log that is linked elsewhere")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    width = max(len(w) for _, w in results)
    for ok, what in results:
        print(f"{'PASS' if ok else 'FAIL'}  {what}")
    failed = sum(1 for ok, _ in results if not ok)
    print(f"\n{len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
