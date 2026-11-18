#!/usr/bin/env python3
"""Find hedging and scattered caveats in a manuscript.

Measures where qualifying language sits, section by section, and lists the
sentences worth a second look:
  - caveats outside the Limitations section (abstract, introduction, results,
    the Discussion opener, the conclusion)
  - an abstract conclusion that ends on a limitation
  - stacked hedges (two or more softeners in one sentence)
  - throat-clearing ("it is important to note"; discourse markers such as
    "Notably," and "Importantly," are acceptable and not flagged) and self-diminishing phrasing
    ("we were able to", "sought to explore")
  - an over-long Limitations section

The headline metrics are the number of caveat sentences outside Limitations
and placement: the share of caveat material (every Limitations sentence plus
caveat sentences elsewhere) that sits inside Limitations. A confident paper states findings plainly and keeps
its caveats in one short, specific Limitations section.

Advisory only. A flag is a prompt to reread the sentence, not a verdict:
"may" in a Methods definition or an accurate "associated with" is fine.
Complements publication-artifact-refiner's publication_text_lint.py, which
covers process leakage, hype and filler.

Example
  python3 hedge_lint.py _audit/proposal/manuscript.md --out-md _audit/runs/hedge_lint.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from doctext import extract_blocks, sentences  # noqa: E402


def rx(*parts: str) -> re.Pattern:
    return re.compile("|".join(parts), re.I)


HEDGE = rx(
    r"(?<![\w-])(may|might|could)(?![\w-])(?!\s+not\s+be\s+(?:determined|obtained))",
    r"(?<![\w-])(possibly|potentially|perhaps|presumably|apparently|arguably|conceivably|plausibly)(?![\w-])",
    r"(?<![\w-])(a|an|the) possible (effect|role|association|link|mechanism|explanation|benefit|harm)(?![\w-])",
    r"(?<![\w-])(appears?|appeared|seems?|seemed)\s+to(?![\w-])",
    r"(?<![\w-])suggest(s|ed|ing|ive|ion)?(?![\w-])",
    r"(?<![\w-])(likely|unlikely)(?![\w-])",
    r"(?<![\w-])(tends?|tended)\s+to(?![\w-])",
    r"(?<![\w-])(somewhat|partially|partly|in part|to some (extent|degree))(?![\w-])",
    r"(?<![\w-])(comparatively|fairly|relatively|seemingly|reasonably)(?![\w-])",
    r"(?<![\w-])rather\b(?!\s+than)",
    r"(?<![\w-])it (is|remains) possible(?![\w-])",
    r"(?<![\w-])(compatible|in keeping) with(?![\w-])",
    r"(?<![\w-])not necessarily(?![\w-])",
    r"(?<![\w-])trend(ed|s|ing)? (toward|towards)(?![\w-])",
    r"(?<![\w-])(preliminary|exploratory|hypothesis[- ]generating)(?![\w-])",
)
CAVEAT = rx(
    r"\b(cannot|can ?not|could not|does not|do not|did not|(is|are|was|were) unable to)\s+"
    r"(be\s+)?(establish|determine|prove|exclude|rule out|infer|confirm|capture|account for|"
    r"address|distinguish|generali[sz]e|imply|estimate|quantify|measure|detect|evaluate|"
    r"attribute|isolate|separate|disentangle|verify)\w*",
    r"\bcannot be (estimated|quantified|measured|determined|established|excluded|ruled out|"
    r"verified|assessed)\b",
    r"\bnot designed to\b|\blimited to\b|\bunder-?report\w*|\bincomplete (data|reporting|capture)\b",
    r"\b(subject to|prone to|vulnerable to)\s+(\w+\s+){0,2}(bias|error|misclassification|confounding)\b",
    r"\b(interpret\w*|viewed|considered|taken)\s+(with\s+)?(caution|cautiously|carefully)\b",
    r"\bcaution\s+(is|was|should be)\s+(warranted|needed|advised|exercised)\b",
    r"\blimitations?\b",
    r"\b(limited|constrained) by\b",
    r"\b(residual|unmeasured|unobserved|uncontrolled)\s+confound\w*",
    r"\bcausal (inference|interpretation|conclusion|claim|relationship)s?\b|\bcausality\b|\bcausation\b",
    r"\bgenerali[sz]ab\w*|\bexternal validity\b|\btransportab\w*",
    r"\b(retrospective|observational|cross-sectional|single[- ]cent(er|re)|ecological)\s+(nature|design)\b",
    r"\b(small|limited)\s+(sample|number of|cohort)\b|\bunderpowered\b|\black of (statistical )?power\b"
    r"|\blimited (statistical )?power\b",
    r"\b(should|must|needs? to)\s+be\s+(confirmed|validated|replicated|verified|tested|explored)\b",
    r"\b(further|future|additional|larger|prospective|more)\s+(research|studies|work|investigation|"
    r"validation|trials?)\s+(is|are|will be)?\s*(needed|warranted|required|necessary)\b",
    r"\bwarrant\w*\s+further\b",
    r"\bremains?\s+(unclear|uncertain|unknown|to be (determined|established))\b",
    r"\bmay not (be )?(generali[sz]|apply|reflect|represent|extend)\w*",
    r"\b(selection|information|recall|survivorship|immortal[- ]time|ascertainment|detection)\s+bias\b",
    r"\breverse causation\b|\bmisclassification\b",
)
THROAT = rx(
    r"\bit (is|should be|was) (important|worth|critical|essential|necessary) to "
    r"(note|emphasi[sz]e|recogni[sz]e|mention|acknowledge|highlight)\b",
    r"\bit should be (noted|emphasi[sz]ed|acknowledged|mentioned|recogni[sz]ed)\b",
    r"\bworth (noting|mentioning)\b",
    r"\bto (the best of )?our knowledge\b",
    r"\bwe (acknowledge|recogni[sz]e|note) that\b",
)
SELF_DIMINISH = rx(
    r"\b(were|was) able to\b",
    r"\battempt(ed|s)? to\b",
    r"\b(aimed|sought|tried|intended) to (explore|examine|investigate|describe|assess)\b",
    r"\bdescriptive (only|in nature)\b",
    r"\bmerely\b",
)
LIMITATION_OPENER = re.compile(
    r"^(this|our|the|the present|the current)\s+(study|analysis|analyses|work|investigation|report|design|data)\s+"
    r"(has|had|is subject to|carries)\s+(several |some |a number of |important |notable |"
    r"certain |both )?(strengths and )?limitations"
    r"|^(several |some |important |notable |our study's |the study's )?limitations\b"
    r"|^(strengths and limitations|this study has (both )?strengths)", re.I)
CLOSER = re.compile(r"^(in conclusion|in summary|taken together|overall,|to conclude)", re.I)

FAMILIES = {"hedge": HEDGE, "caveat": CAVEAT, "throat": THROAT, "self_diminish": SELF_DIMINISH}
REPORT_ORDER = ["key_points", "abstract", "abstract_conclusion", "introduction", "methods",
                "results", "discussion", "limitations", "conclusion", "body", "supplement"]
NO_CAVEAT_ZONES = {"key_points", "abstract", "introduction", "results", "conclusion"}


def mark(sentence: str) -> str:
    out = sentence
    for pat in (CAVEAT, HEDGE, THROAT, SELF_DIMINISH):
        out = pat.sub(lambda m: f"**{m.group(0)}**", out)
    return re.sub(r"\*\*\*\*", "", out)


def analyze(path: Path) -> dict:
    blocks = [b for b in extract_blocks(path)
              if b["kind"] == "para" and b["canonical"] not in {"references"}]
    # Treat Discussion paragraphs from a limitations opener onward as Limitations.
    in_lim_section = None
    for b in blocks:
        first = b["text"].lstrip("*_ ")
        if b["canonical"] == "discussion":
            if in_lim_section == b["section"] and CLOSER.match(first):
                in_lim_section = None
            if LIMITATION_OPENER.match(first):
                in_lim_section = b["section"]
            if in_lim_section == b["section"]:
                b["canonical"] = "limitations"
        else:
            in_lim_section = None

    sents = []
    first_discussion_seen = False
    for b in blocks:
        is_disc_opener = False
        if b["canonical"] == "discussion" and not first_discussion_seen:
            first_discussion_seen = True
            is_disc_opener = True
        for s in sentences(b["text"]):
            hits = {name: [m.group(0) for m in pat.finditer(s)] for name, pat in FAMILIES.items()}
            sents.append({"section": b["canonical"], "label": b["section"], "text": s,
                          "hits": hits, "disc_opener": is_disc_opener, "block": b["index"]})

    stats = defaultdict(lambda: {"sentences": 0, "words": 0, "hedges": 0,
                                 "caveat_sentences": 0, "stacked": 0})
    for s in sents:
        st = stats[s["section"]]
        st["sentences"] += 1
        st["words"] += len(s["text"].split())
        st["hedges"] += len(s["hits"]["hedge"])
        if s["hits"]["caveat"]:
            st["caveat_sentences"] += 1
        if len(s["hits"]["hedge"]) + len(s["hits"]["caveat"]) >= 2:
            st["stacked"] += 1

    findings = defaultdict(list)
    for s in sents:
        sec, h = s["section"], s["hits"]
        if h["caveat"] and sec in NO_CAVEAT_ZONES:
            findings[f"Caveats in {sec.replace('_', ' ')}"].append(s)
        if (h["caveat"] or h["hedge"]) and s["disc_opener"]:
            findings["Hedges or caveats in the Discussion opener"].append(s)
        if sec == "discussion" and h["caveat"] and not s["disc_opener"]:
            findings["Caveats scattered through the Discussion (outside Limitations)"].append(s)
        if len(h["hedge"]) + len(h["caveat"]) >= 2 and sec != "limitations":
            findings["Stacked hedges (two or more in one sentence)"].append(s)
        if h["throat"]:
            findings["Throat-clearing"].append(s)
        if h["self_diminish"]:
            findings["Self-diminishing phrasing"].append(s)
    concl = [s for s in sents if s["section"] == "abstract_conclusion"]
    if concl:
        last = concl[-1]
        if last["hits"]["caveat"] or last["hits"]["hedge"]:
            findings["Abstract conclusion ends on a qualifier"].append(last)
        for s in concl:
            if s["hits"]["caveat"] and s is not last:
                findings["Caveats in abstract conclusion"].append(s)

    lim = stats.get("limitations")
    in_lim = lim["sentences"] if lim else 0          # every Limitations sentence is caveat material
    outside = sum(v["caveat_sentences"] for k, v in stats.items() if k != "limitations")
    total_cav = in_lim + outside
    return {"file": str(path), "stats": stats, "findings": findings,
            "caveat_total": total_cav, "caveat_in_limitations": in_lim,
            "caveat_outside": outside,
            "placement": (in_lim / total_cav) if total_cav else None,
            "limitations_words": lim["words"] if lim else 0,
            "limitations_sentences": lim["sentences"] if lim else 0,
            "has_limitations": bool(lim)}


def render(res: dict, max_examples: int) -> str:
    L = [f"# Hedge and caveat check: `{res['file']}`", ""]
    if res["placement"] is None:
        L.append("- No caveat sentences detected.")
    else:
        L.append(f"- **Caveat sentences outside Limitations: {res['caveat_outside']}.** "
                 f"Placement: {res['placement']:.0%} of caveat material sits in Limitations "
                 f"({res['caveat_in_limitations']} Limitations sentences, {res['caveat_outside']} "
                 "caveat sentences elsewhere). Aim for nearly all of it.")
    if res["has_limitations"]:
        flag = " (long; an experienced author's is usually one paragraph)" \
            if res["limitations_words"] > 260 else ""
        L.append(f"- Limitations: {res['limitations_sentences']} sentences, "
                 f"{res['limitations_words']} words{flag}.")
    else:
        L.append("- No Limitations section detected. Caveats that matter belong in one.")
    L += ["", "| Section | Sentences | Hedge terms | per 10 sentences | Caveat sentences | Stacked |",
          "|---|---:|---:|---:|---:|---:|"]
    for sec in REPORT_ORDER + sorted(set(res["stats"]) - set(REPORT_ORDER)):
        if sec not in res["stats"]:
            continue
        st = res["stats"][sec]
        rate = 10 * st["hedges"] / st["sentences"] if st["sentences"] else 0
        L.append(f"| {sec.replace('_', ' ')} | {st['sentences']} | {st['hedges']} | {rate:.1f} | "
                 f"{st['caveat_sentences']} | {st['stacked']} |")
    L.append("")
    order = ["Abstract conclusion ends on a qualifier", "Caveats in key points",
             "Caveats in abstract", "Caveats in abstract conclusion", "Caveats in results",
             "Caveats in introduction", "Caveats in conclusion",
             "Hedges or caveats in the Discussion opener",
             "Caveats scattered through the Discussion (outside Limitations)",
             "Stacked hedges (two or more in one sentence)", "Throat-clearing",
             "Self-diminishing phrasing"]
    for title in order + sorted(set(res["findings"]) - set(order)):
        items = res["findings"].get(title)
        if not items:
            continue
        L += [f"## {title} ({len(items)})", ""]
        for s in items[:max_examples]:
            L.append(f"- [{s['label'] or s['section']}] {mark(s['text'])}")
        if len(items) > max_examples:
            L.append(f"- ...and {len(items) - max_examples} more")
        L.append("")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out-md", default=None)
    ap.add_argument("--json", action="store_true", help="print summary metrics as JSON")
    ap.add_argument("--max-examples", type=int, default=25)
    args = ap.parse_args(argv)
    reports, summary = [], []
    for f in args.files:
        res = analyze(Path(f))
        reports.append(render(res, args.max_examples))
        summary.append({"file": f, "caveat_total": res["caveat_total"],
                        "caveat_in_limitations": res["caveat_in_limitations"],
                        "caveat_outside": res["caveat_outside"],
                        "placement": res["placement"],
                        "limitations_words": res["limitations_words"],
                        "findings": {k: len(v) for k, v in res["findings"].items()}})
    text = "\n".join(reports)
    if args.out_md:
        Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_md).write_text(text, encoding="utf-8")
        print(f"report: {args.out_md}")
    if args.json:
        print(json.dumps(summary, indent=2))
    elif not args.out_md:
        print(text)
    else:
        for s in summary:
            pl = "n/a" if s["placement"] is None else f"{s['placement']:.0%}"
            print(f"{s['file']}: {s['caveat_outside']} caveat sentences outside Limitations "
                  f"(placement {pl}); "
                  + ", ".join(f"{k}: {v}" for k, v in s["findings"].items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
