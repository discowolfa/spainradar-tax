import json
from typing import Any

from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL
from utils.text_utils import sanitize_text


class Analyzer:
    def __init__(self, logger: Any = None) -> None:
        self.logger = logger
        self.client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        self.model = OPENAI_MODEL

    def _parse_json_response(self, content: str) -> dict:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise
            return json.loads(content[start : end + 1])

    def analyze(self, text: str) -> str:
        if self.logger:
            self.logger.debug("Analyzing text from source")

        clean_text = sanitize_text(text)
        if not clean_text:
            return ""

        if not self.client:
            if self.logger:
                self.logger.warning("OPENAI_API_KEY is not set; using raw sanitized text")
            return clean_text

        prompt = (
            "You are an editor for a Russian-language Telegram channel about taxes, "
            "law, finance, and official news in Spain. Translate the news item into "
            "clear Russian and add a short practical analysis. Return only JSON with "
            'keys "translation", "analysis", and "importance". '
            "Keep it factual; do not invent details.\n\n"
            f"News item:\n{clean_text}"
        )

        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
            )
            content = sanitize_text(response.output_text)
            data = self._parse_json_response(content)
        except Exception:
            if self.logger:
                self.logger.exception("OpenAI analysis failed; using raw sanitized text")
            return clean_text

        translation = sanitize_text(str(data.get("translation", "")))
        analysis = sanitize_text(str(data.get("analysis", "")))
        importance = sanitize_text(str(data.get("importance", "")))

        parts = []
        if translation:
            parts.append(f"Перевод: {translation}")
        if analysis:
            parts.append(f"Анализ: {analysis}")
        if importance:
            parts.append(f"Почему важно: {importance}")

        return "\n\n".join(parts) or clean_text
