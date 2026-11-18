"""One definition of raw data, shared by audit_workspace.py, inventory.py and safe_move.py.

A path is raw data when it lies inside
  - a location declared with --raw. A declaration is resolved once to the real folder
    inside the project (`./x`, `x/../y` and symlinked aliases name their target; a path
    outside the project is an error). `audit_workspace.py open --raw X` records it in
    _audit/raw_paths.txt, and every later scan and move reads that file, so the
    declaration is made once;
  - a folder named raw, raw_data, rawdata or data_raw, at any depth; or
  - a folder named source_data, original(s), inputdata, input_data, extracts or
    external, at the top level or inside a data folder (data/, inputs/, sources/, ...).
"""

from __future__ import annotations

import os
from pathlib import Path

RAW_NAMES = {"raw", "raw_data", "rawdata", "data_raw"}
CONTEXT_RAW_NAMES = {"source_data", "original", "originals", "inputdata", "input_data",
                     "extracts", "external"}
ALL_RAW_NAMES = RAW_NAMES | CONTEXT_RAW_NAMES
DATA_ISH = {"data", "inputs", "input", "sources", "dataset", "datasets"}
DECLARED = "_audit/raw_paths.txt"


def norm(p: str) -> str:
    return p.strip().replace("\\", "/").strip("/")


def canonical(root, location: str) -> str:
    """The real, project-relative path a raw declaration names. ValueError outside the project."""
    root_real = os.path.realpath(root)
    loc = location.strip()
    if not norm(loc):
        raise ValueError(f"raw-data location {location!r} is empty or names a filesystem root")
    real = os.path.realpath(loc if os.path.isabs(loc) else os.path.join(root_real, loc))
    if real == root_real or not real.startswith(root_real + os.sep):
        raise ValueError(f"raw-data location {location!r} is not a path inside the project")
    return Path(real).relative_to(root_real).as_posix()


def declared(root, extra=()) -> list[str]:
    """Raw locations given on the command line plus those recorded when the workspace opened,
    each resolved to its real path inside the project. ValueError when a declaration is
    invalid, or when an open workspace has lost its record of them."""
    names = list(extra)
    ws = Path(root) / "_audit"
    f = Path(root) / DECLARED
    if f.is_file():
        names += [line for line in f.read_text(encoding="utf-8").splitlines()
                  if line.strip() and not line.lstrip().startswith("#")]
    elif (ws / "MANIFEST.tsv").is_file():
        raise ValueError(f"{DECLARED} is missing, so the raw-data locations declared at open are "
                         "unknown. Restore it (_audit/README.md lists them) before continuing.")
    return sorted({canonical(root, x) for x in names})


def raw_root(rel: str, locations=()) -> str | None:
    """The raw folder or declared location containing the file `rel`, or None."""
    rel = norm(rel)
    parts = rel.split("/")
    low = rel.lower()
    for r in locations:
        r = norm(r)
        if r and (low == r.lower() or low.startswith(r.lower() + "/")):
            return "/".join(parts[:len(r.split("/"))])
    dirs = [p.lower() for p in parts[:-1]]
    for i, p in enumerate(dirs):
        if p in RAW_NAMES or (p in CONTEXT_RAW_NAMES
                              and (i == 0 or any(d in DATA_ISH for d in dirs[:i]))):
            return "/".join(parts[:i + 1])
    return None


def is_raw(rel: str, locations=()) -> bool:
    return raw_root(rel, locations) is not None


def is_raw_folder(rel: str, locations=()) -> bool:
    """`rel` is raw, or names a folder that is itself a raw folder."""
    return raw_root(norm(rel) + "/_", locations) is not None
