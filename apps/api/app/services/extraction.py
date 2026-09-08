import json
from pathlib import Path

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.extraction import Extraction

_PROMPT = (Path(__file__).resolve().parent.parent / "prompts" / "extract_order.txt").read_text()


class ExtractionError(Exception):
    pass


async def _call_ollama(system: str, user: str) -> str:
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            f"{settings.ollama_url}/api/chat",
            json={
                "model": settings.ollama_model,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
    resp.raise_for_status()
    return str(resp.json()["message"]["content"])


async def extract_order(message: str) -> Extraction:
    last_err: Exception | None = None
    for attempt in range(2):
        system = _PROMPT
        if attempt == 1:
            system += "\n\nPENTING: keluaran sebelumnya tidak valid. Balas HANYA JSON sesuai skema."
        raw = await _call_ollama(system, f'Pesan: "{message}"\nJSON:')
        try:
            return Extraction.model_validate_json(raw)
        except (ValidationError, json.JSONDecodeError, ValueError) as e:
            last_err = e
    raise ExtractionError(f"gagal ekstraksi setelah 2 percobaan: {last_err}")
