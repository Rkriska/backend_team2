"""
LLM service — calls OpenAI-compatible API (Qwen 3 or any model).
Returns structured JSON: classification, reason, recommendation, evidence.
"""
import json
import httpx
from app.config import settings

SYSTEM_PROMPT = """Kamu adalah auditor dokumen pengadaan pemerintah Indonesia yang berpengalaman.
Tugasmu adalah mengevaluasi apakah dokumen TOR (Terms of Reference) memenuhi kriteria yang ditetapkan.
Berikan jawaban yang objektif, berdasarkan bukti dari dokumen yang disediakan.
Selalu jawab dalam format JSON yang valid."""

USER_TEMPLATE = """Evaluasi apakah dokumen TOR memenuhi kriteria berikut:
**Kriteria:** {checklist_description}

**Konteks dari Dokumen TOR:**
{tor_passages}

**Konteks dari Dokumen Acuan/Referensi:**
{reference_passages}

Berikan jawaban HANYA dalam format JSON berikut (tidak ada teks lain di luar JSON):
{{
  "classification": "LOLOS" | "TIDAK_LOLOS" | "PERLU_REVISI",
  "reason": "alasan evaluasi dalam 2-3 kalimat",
  "recommendation": "rekomendasi perbaikan jika diperlukan, atau 'Tidak ada perbaikan diperlukan' jika LOLOS",
  "evidence": [
    {{"source": "nama_dokumen_atau_pasal", "content": "kutipan teks yang relevan (maks 200 karakter)"}}
  ]
}}"""


async def call_llm(
    checklist_description: str,
    tor_passages: list[dict],
    reference_passages: list[dict],
    checklist_item_key: str = "",
) -> dict:
    """
    Call LLM and return parsed JSON result.
    Returns dict with keys: classification, reason, recommendation, evidence
    """
    tor_text = "\n\n".join(
        f"[TOR - Chunk {i+1}]\n{p['payload'].get('content', p.get('content', ''))}"
        for i, p in enumerate(tor_passages)
    )
    ref_text = "\n\n".join(
        f"[Acuan - {p['payload'].get('source_type', 'REF')}]\n{p['payload'].get('content', p.get('content', ''))}"
        for i, p in enumerate(reference_passages)
    ) if reference_passages else "Tidak ada dokumen acuan tersedia."

    user_msg = USER_TEMPLATE.format(
        checklist_description=checklist_description,
        tor_passages=tor_text or "Tidak ada konteks TOR ditemukan.",
        reference_passages=ref_text,
    )

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
    }

    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.LLM_API_URL}/chat/completions",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    raw_content = data["choices"][0]["message"]["content"]

    # Parse JSON from response
    try:
        # Handle markdown code blocks
        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_content:
            raw_content = raw_content.split("```")[1].split("```")[0].strip()
        result = json.loads(raw_content)
    except json.JSONDecodeError:
        # Fallback if LLM returns non-JSON
        result = {
            "classification": "PERLU_REVISI",
            "reason": "Gagal memparse respons LLM",
            "recommendation": raw_content[:500],
            "evidence": [],
        }

    return {
        "classification": result.get("classification", "PERLU_REVISI"),
        "reason": result.get("reason", ""),
        "recommendation": result.get("recommendation", ""),
        "evidence": result.get("evidence", []),
        "raw_prompt": user_msg,
        "raw_response": data["choices"][0]["message"]["content"],
    }
