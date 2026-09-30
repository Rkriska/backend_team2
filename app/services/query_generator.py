"""
Query generator: convert checklist item descriptions into search queries for Qdrant.
"""

QUERY_EXPANSIONS = {
    "TOR_001": "latar belakang dasar hukum regulasi pendahuluan kegiatan",
    "TOR_002": "tujuan sasaran maksud kegiatan target capaian",
    "TOR_003": "ruang lingkup pekerjaan cakupan wilayah batasan",
    "TOR_004": "metodologi metode pelaksanaan pendekatan teknis cara kerja",
    "TOR_005": "jadwal pelaksanaan timeline waktu rencana kegiatan",
    "TOR_006": "keluaran output deliverable hasil produk laporan",
    "TOR_007": "anggaran biaya pagu estimasi rencana keuangan",
    "TOR_008": "kualifikasi tenaga ahli personil sumber daya kompetensi",
}


def generate_query(item_key: str, description: str) -> str:
    """Generate a search query for a checklist item."""
    if item_key in QUERY_EXPANSIONS:
        return QUERY_EXPANSIONS[item_key]
    # fallback: use the description as-is
    return description
