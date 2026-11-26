"""Check that the tables printed in the manuscript equal the tables generated from the results.

make_tex_tables.py writes one .tex file per results table. For each generated file this script
finds the manuscript table with the same \\label and compares the data rows (the lines between
\\toprule and \\bottomrule of each of its tabulars). Revision highlighting (\\rev{...}) and whitespace are ignored, so the
check runs on the highlighted and on the clean manuscript alike.

usage: python3 -I table_check.py <tables_dir> <manuscript_tex> <out_txt>
Exit status 1 if any table differs or is missing.
"""
import re
import sys
from pathlib import Path

TABLES, TEX, OUT = (Path(a) for a in sys.argv[1:4])


def unrev(s: str) -> str:
    """Remove \\rev{...} wrappers (brace-balanced), keeping their content."""
    out, i = [], 0
    while True:
        j = s.find(r"\rev{", i)
        if j < 0:
            out.append(s[i:])
            return "".join(out)
        out.append(s[i:j])
        k, depth = j + 5, 1
        while depth:
            depth += {"{": 1, "}": -1}.get(s[k], 0)
            k += 1
        out.append(unrev(s[j + 5:k - 1]))
        i = k


def rows(block: str) -> list[str]:
    """The data rows of every tabular in the table (a table can hold several, as Table 6 does from release 4.4)."""
    out = []
    for part in unrev(block).split(r"\toprule")[1:]:
        body = re.sub(r"(?<!\\)%.*", "", part.split(r"\bottomrule", 1)[0])
        out += [r for r in (re.sub(r"\s+", " ", x).strip() for x in body.split(r"\\")) if r]
    return out


def table_at(text: str, label: str) -> str | None:
    k = text.find(r"\label{" + label + "}")
    if k < 0:
        return None
    start = text.rfind(r"\begin{table", 0, k)
    end = text.find(r"\end{table", k)
    return text[start:end]


tex = TEX.read_text()
lines, fails = [], 0
for f in sorted(TABLES.glob("tab_*.tex")):
    gen = f.read_text()
    label = re.search(r"\\label\{([^}]*)\}", gen).group(1)
    man = table_at(tex, label)
    if man is None:
        fails += 1
        lines.append(f"[FAIL] {f.name} ({label}): no table with this label in the manuscript")
        continue
    g, m = rows(gen), rows(man)
    if g == m:
        lines.append(f"[ok] {f.name} ({label}): {len(g)} rows identical")
    else:
        fails += 1
        lines.append(f"[FAIL] {f.name} ({label}): rows differ")
        for a, b in zip(g + [""] * (len(m) - len(g)), m + [""] * (len(g) - len(m))):
            if a != b:
                lines.append(f"    generated:  {a}\n    manuscript: {b}")
lines.append(f"{fails} table(s) differ" if fails else "all tables identical")
OUT.write_text("\n".join(lines) + "\n")
print("\n".join(lines))
sys.exit(1 if fails else 0)
