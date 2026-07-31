"""Cardholder -> canonical name -> manager resolution.

Merges (see references/manager-mapping.md for why, in this priority order):
  1. The Manager Mapping sheet (3rd tab of the latest master/per-manager workbook)
  2. The realized fallback (Manager column already baked into the latest
     master's Amex Txn Details tab) - EXCEPT a realized "UNMAPPED" must never
     override a real answer from #1.
  3. Two rollup teams (Tameem Hourani -> Ayaan Israni, Matthew Keyes -> Kevin Ebert)
  4. Manual overrides (references/routing-overrides.md)
  5. Fuzzy matching (edit-distance <=2 on a unique surname) as a last resort

Also provides consolidate_names(), a second pass that catches spelling
variants the above can't (e.g. two independently "valid" roster spellings
like "Connor Bracket" / "Connor Brackett") - picking a winner only when an
authoritative source (card-mapping.tsv, then the Manager Mapping sheet)
actually confirms one, never by string length or processing order.
"""
import re
import unicodedata
from collections import defaultdict

import openpyxl

BUCKETS = {
    "Jay Barker", "Connor/JT", "Jesse/Scott", "Elias Kapetanopoulos",
    "Ayaan Israni", "Elyse Neumeier", "Toni Manning", "Kevin Ebert",
}

# confirmed by Zayn 2026-07-01: sub-team leads in the Manager Mapping sheet
# that are not themselves one of the 8 buckets and roll up one more hop.
ROLLUP = {
    "tameem hourani": "Ayaan Israni",
    "matthew keyes": "Kevin Ebert",
}

NICK = {
    "matt": "matthew", "mike": "michael", "mick": "mickenzi", "alex": "alexander",
    "bob": "robert", "rob": "robert", "kara": "karalyn", "mitch": "mitchell",
    "jim": "james", "tom": "thomas", "chris": "christopher", "dan": "daniel",
    "danny": "daniel", "nick": "nicholas", "will": "william", "bill": "william",
    "joe": "joseph", "tony": "anthony", "ben": "benjamin", "sam": "samuel",
    "greg": "gregory", "andy": "andrew", "steve": "stephen", "jon": "jonathan",
}

# confirmed by Zayn - manual routing corrections/aliases, take top priority
MANUAL_ROUTING_OVERRIDES = {
    "luis gallego": ("Luis Gallego Cardona", None),
    "henri hatch": ("Henri Hatch", "Jay Barker"),
    "alta abel": ("Alta Abel", "Ayaan Israni"),
    "samantha purpura": ("Samantha Purpura", "Ayaan Israni"),
    "frederick simpson": ("Frederick Simpson", "Ayaan Israni"),
    "jacy hennawy": ("Jacy Hennawy", "Elyse Neumeier"),
    "vivian wu": ("Vivian Wu", "Elyse Neumeier"),
    "dwight henderson": ("Dwight Henderson", "Jesse/Scott"),
    "elias kapetanopolous": ("Elias Kapetanopoulos", None),
    "michael button": ("Michael Button", "Elias Kapetanopoulos"),
    "marsha whitman": ("Marsha Whitman", "Elias Kapetanopoulos"),
    "brendan nolan": ("Brendan Nolan", "Elias Kapetanopoulos"),
    "gage howell": ("Gage Howell", "Elias Kapetanopoulos"),
    "john fennell": ("John Fennell", "Toni Manning"),
    "william sanderford": ("William Sanderford", "Elias Kapetanopoulos"),
    "anamaria gramada": ("Anamaria Grămadă", "Elias Kapetanopoulos"),
    "cody sanderford": ("Cody Sandford", "Elias Kapetanopoulos"),
    "sakshi sasalate": ("Sakshi Sasalate", "Elias Kapetanopoulos"),
    "samara mcvey": ("Samara McVey", "Elias Kapetanopoulos"),
    "gary passaglia": ("Gary Passaglia", "Connor/JT"),
    "daniel mooney": ("Daniel Mooney", "Connor/JT"),
}

GUARDRAIL_SURNAMES = {"hourani", "whitehead", "kolosky"}


def normkey(name, apply_nick=True):
    if not name:
        return ""
    ascii_ = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    tokens = re.findall(r"[a-zA-Z]+", ascii_.lower())
    if apply_nick:
        tokens = [NICK.get(t, t) for t in tokens]
    return " ".join(tokens)


def edit_distance(a, b):
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def load_manager_mapping_sheet(workbook_path):
    """Reads the 3rd tab ('Manager Mapping': Card Name/Lead/Department/EE ID)
    of the given workbook. Returns [{"name":..., "lead":...}, ...]."""
    wb = openpyxl.load_workbook(workbook_path, data_only=True)
    ws = wb["Manager Mapping"]
    rows = []
    for row in ws.iter_rows(min_row=3, max_row=ws.max_row, values_only=True):
        name, lead = row[1], row[2]
        if name:
            rows.append({"name": str(name).strip(), "lead": str(lead).strip() if lead else None})
    return rows


def load_realized_mapping(workbook_path):
    """Reads the actual Manager column already baked into 'Amex Txn Details'
    of the given (typically the latest) master workbook. Returns {Card
    Member: Manager}. This is ground truth for what was actually shipped,
    but per manager-mapping.md §1, an 'UNMAPPED' entry here must not be
    trusted over a real answer from the Manager Mapping sheet."""
    wb = openpyxl.load_workbook(workbook_path, data_only=True)
    ws = wb["Amex Txn Details"]
    by_member = defaultdict(set)
    for row in ws.iter_rows(min_row=3, max_row=ws.max_row, values_only=True):
        member, mgr = row[3], row[16]
        if member and mgr:
            by_member[member].add(mgr)
    out = {}
    for member, mgrs in by_member.items():
        if len(mgrs) > 1:
            raise ValueError(f"{member!r} maps to more than one manager in the realized "
                              f"data: {mgrs} - resolve by hand before trusting this source")
        out[member] = next(iter(mgrs))
    return out


def load_card_mapping(tsv_path):
    """last4 -> Card Name, from references/card-mapping.tsv. Only for Amex
    Plat/Plat 2, whose transaction memo carries no cardholder name at all."""
    card_map = {}
    with open(tsv_path) as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            while len(parts) < 2:
                parts.append("")
            last4, name = parts[0].strip(), parts[1].strip()
            if last4 and name:
                card_map[last4] = name
    return card_map


class Resolver:
    def __init__(self, manager_mapping_rows, realized_mapping, card_mapping=None):
        self.card_mapping = card_mapping or {}
        self.canon_by_norm = {}
        for r in manager_mapping_rows:
            nk = normkey(r["name"])
            lead_key = normkey(r["lead"], apply_nick=False) if r["lead"] else ""
            final_mgr = ROLLUP.get(lead_key, r["lead"])
            display = r["name"].title() if r["name"].isupper() else r["name"]
            self.canon_by_norm[nk] = (display, final_mgr)
        for member, mgr in realized_mapping.items():
            if mgr == "UNMAPPED":
                continue  # never let a non-answer clobber a real one
            self.canon_by_norm[normkey(member)] = (member, mgr)

        self.surname_index = defaultdict(list)
        for nk, (canon, mgr) in self.canon_by_norm.items():
            toks = nk.split()
            if len(toks) >= 2:
                self.surname_index[toks[-1]].append((toks[0], canon, mgr))

    def resolve(self, raw_name):
        """-> (canonical_name, manager, method). manager is None if unresolved."""
        if not raw_name:
            return None, None, "no-name"
        nk = normkey(raw_name)
        if nk in MANUAL_ROUTING_OVERRIDES:
            canon, mgr = MANUAL_ROUTING_OVERRIDES[nk]
            if mgr:
                return canon, mgr, "manual-override"
            nk = normkey(canon)  # spelling-only alias, fall through to roster lookup
        if nk in self.canon_by_norm:
            canon, mgr = self.canon_by_norm[nk]
            return canon, mgr, "exact"
        toks = nk.split()
        if len(toks) >= 2:
            surname, first = toks[-1], toks[0]
            candidates = self.surname_index.get(surname, [])
            if not candidates:
                close = [s for s in self.surname_index if edit_distance(s, surname) <= 2]
                candidates = [c for s in close for c in self.surname_index[s]]
            uniq = {c[1]: c for c in candidates}
            if len(uniq) == 1:
                cand_first, canon, mgr = next(iter(uniq.values()))
                if edit_distance(first, cand_first) <= 2 or edit_distance(nk, normkey(canon)) <= 2:
                    return canon, mgr, "fuzzy"
        return raw_name, None, "unmapped"

    def resolve_amex_by_last4(self, last4):
        """Amex Plat/Plat 2 fallback: last4 -> card_mapping name -> resolve()."""
        name = self.card_mapping.get(last4)
        if not name:
            return None, None, "unmapped"
        return self.resolve(name)


def consolidate_names(rows, card_mapping_names, manager_mapping_names):
    """Second pass: cluster remaining spelling variants within the same
    manager bucket. Only merges when an authoritative source confirms the
    winning spelling - never by string length or processing order. Mutates
    each row's "card_member" in place. Returns the rename log for review."""
    by_mgr_names = defaultdict(set)
    for row in rows:
        if row.get("manager") and row["manager"] != "UNMAPPED" and row.get("card_member"):
            by_mgr_names[row["manager"]].add(row["card_member"])

    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for mgr, names in by_mgr_names.items():
        names = sorted(names)
        for n in names:
            find(n)
        for i in range(len(names)):
            ti = normkey(names[i]).split()
            if len(ti) < 2:
                continue
            for j in range(i + 1, len(names)):
                tj = normkey(names[j]).split()
                if len(tj) < 2:
                    continue
                first_i, last_i = ti[0], ti[-1]
                first_j, last_j = tj[0], tj[-1]
                if last_i == last_j and first_i == first_j:
                    continue
                if (edit_distance(first_i, first_j) <= 1 and edit_distance(last_i, last_j) <= 2
                        and not (last_i in GUARDRAIL_SURNAMES and first_i != first_j)):
                    union(names[i], names[j])

    clusters = defaultdict(list)
    for names in by_mgr_names.values():
        for n in names:
            clusters[find(n)].append(n)

    def pick_representative(members):
        for m in members:
            if m in card_mapping_names:
                return m, "card-mapping"
        for m in members:
            if m in manager_mapping_names:
                return m, "manager-mapping-sheet"
        return None, "ambiguous"

    rename_map, rename_log, flagged = {}, [], []
    for members in clusters.values():
        if len(members) <= 1:
            continue
        rep, source = pick_representative(members)
        if rep is None:
            flagged.append(members)
            continue
        for m in members:
            if m != rep:
                rename_map[m] = rep
                rename_log.append((m, rep, source))

    for row in rows:
        if row.get("card_member") in rename_map:
            row["card_member"] = rename_map[row["card_member"]]

    return rename_log, flagged
