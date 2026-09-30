"""
Rule Engine for Screening 1 — Format Check.
Hardcoded rules for Checklist I (TOR) and Checklist III (RAB).
Returns pass/fail per checklist item using regex/keyword matching on extracted text.
"""
import re


# ─── TOR Format Rules (Checklist I) ──────────────────────────────────────────

TOR_RULES = [
    {
        "item_key": "TOR_001",
        "description": "Dokumen TOR memiliki latar belakang / dasar hukum",
        "category": "FORMAT",
        "checklist_number": 1,
        "patterns": [
            r"latar\s+belakang",
            r"dasar\s+hukum",
            r"pendahuluan",
        ],
    },
    {
        "item_key": "TOR_002",
        "description": "Dokumen TOR memiliki tujuan dan sasaran kegiatan",
        "category": "FORMAT",
        "checklist_number": 1,
        "patterns": [
            r"tujuan",
            r"sasaran",
            r"maksud\s+dan\s+tujuan",
        ],
    },
    {
        "item_key": "TOR_003",
        "description": "Dokumen TOR memiliki ruang lingkup pekerjaan",
        "category": "FORMAT",
        "checklist_number": 1,
        "patterns": [
            r"ruang\s+lingkup",
            r"lingkup\s+pekerjaan",
            r"lingkup\s+kegiatan",
        ],
    },
    {
        "item_key": "TOR_004",
        "description": "Dokumen TOR memiliki metodologi / metode pelaksanaan",
        "category": "FORMAT",
        "checklist_number": 1,
        "patterns": [
            r"metodologi",
            r"metode\s+pelaksanaan",
            r"metode\s+kerja",
            r"pendekatan",
        ],
    },
    {
        "item_key": "TOR_005",
        "description": "Dokumen TOR memiliki jadwal / timeline pelaksanaan",
        "category": "FORMAT",
        "checklist_number": 1,
        "patterns": [
            r"jadwal",
            r"timeline",
            r"rencana\s+waktu",
            r"time\s+schedule",
        ],
    },
    {
        "item_key": "TOR_006",
        "description": "Dokumen TOR memiliki keluaran / output yang diharapkan",
        "category": "FORMAT",
        "checklist_number": 1,
        "patterns": [
            r"keluaran",
            r"output",
            r"hasil\s+yang\s+diharapkan",
            r"deliverable",
        ],
    },
    {
        "item_key": "TOR_007",
        "description": "Dokumen TOR menyebutkan anggaran / estimasi biaya",
        "category": "FORMAT",
        "checklist_number": 1,
        "patterns": [
            r"anggaran",
            r"biaya",
            r"pagu",
            r"estimasi\s+biaya",
            r"rencana\s+anggaran",
        ],
    },
    {
        "item_key": "TOR_008",
        "description": "Dokumen TOR menyebutkan kualifikasi tenaga ahli",
        "category": "FORMAT",
        "checklist_number": 1,
        "patterns": [
            r"kualifikasi",
            r"tenaga\s+ahli",
            r"personil",
            r"sumber\s+daya\s+manusia",
        ],
    },
]

# ─── RAB Format Rules (Checklist III) ────────────────────────────────────────

RAB_RULES = [
    {
        "item_key": "RAB_001",
        "description": "Dokumen RAB memiliki nama/identitas pekerjaan",
        "category": "FORMAT",
        "checklist_number": 3,
        "patterns": [
            r"nama\s+pekerjaan",
            r"judul\s+pekerjaan",
            r"rencana\s+anggaran\s+biaya",
        ],
    },
    {
        "item_key": "RAB_002",
        "description": "Dokumen RAB memiliki daftar item/komponen biaya",
        "category": "FORMAT",
        "checklist_number": 3,
        "patterns": [
            r"no\.\s*uraian",
            r"uraian\s+pekerjaan",
            r"komponen\s+biaya",
            r"item\s+pekerjaan",
        ],
    },
    {
        "item_key": "RAB_003",
        "description": "Dokumen RAB memiliki kolom volume/satuan",
        "category": "FORMAT",
        "checklist_number": 3,
        "patterns": [
            r"volume",
            r"satuan",
            r"unit",
        ],
    },
    {
        "item_key": "RAB_004",
        "description": "Dokumen RAB memiliki harga satuan",
        "category": "FORMAT",
        "checklist_number": 3,
        "patterns": [
            r"harga\s+satuan",
            r"unit\s+price",
            r"biaya\s+satuan",
        ],
    },
    {
        "item_key": "RAB_005",
        "description": "Dokumen RAB memiliki total / jumlah biaya",
        "category": "FORMAT",
        "checklist_number": 3,
        "patterns": [
            r"total\s+biaya",
            r"jumlah\s+biaya",
            r"grand\s+total",
            r"total\s+anggaran",
        ],
    },
    {
        "item_key": "RAB_006",
        "description": "Dokumen RAB tidak mengandung nilai negatif",
        "category": "FORMAT",
        "checklist_number": 3,
        "negative_check": True,
        "negative_patterns": [r"-\s*(?:Rp\.?)?\s*[\d\.,]+"],
    },
]


def check_format(extracted_text: str, doc_type: str) -> list[dict]:
    """
    Run format rules against extracted text.
    Returns list of {item_key, description, passed, notes}
    """
    text_lower = extracted_text.lower()
    results = []

    rules = TOR_RULES if doc_type == "TOR" else RAB_RULES

    for rule in rules:
        if rule.get("negative_check"):
            # Must NOT match
            found = any(
                re.search(p, extracted_text, re.IGNORECASE)
                for p in rule.get("negative_patterns", [])
            )
            passed = not found
            notes = "Ditemukan nilai negatif dalam RAB" if not passed else "Tidak ada nilai negatif"
        else:
            # Must match at least one pattern
            found_pattern = None
            for pattern in rule.get("patterns", []):
                if re.search(pattern, text_lower, re.IGNORECASE):
                    found_pattern = pattern
                    break
            passed = found_pattern is not None
            notes = f"Pattern '{found_pattern}' ditemukan" if passed else f"Tidak ditemukan: {rule['patterns']}"

        results.append({
            "item_key": rule["item_key"],
            "description": rule["description"],
            "checklist_number": rule["checklist_number"],
            "passed": passed,
            "notes": notes,
        })

    return results


def get_all_rules() -> list[dict]:
    """Return all rules for seeding checklist_items table."""
    return TOR_RULES + RAB_RULES + SUBSTANCE_RULES

SUBSTANCE_RULES = [
 {"item_key":"SUB_001","description":"TOR menjelaskan kesesuaian tujuan, ruang lingkup, metodologi dan keluaran kegiatan","category":"SUBSTANSI","checklist_number":2},
 {"item_key":"SUB_002","description":"TOR memiliki jadwal dan anggaran yang wajar serta dapat dipertanggungjawabkan","category":"SUBSTANSI","checklist_number":2},
]
