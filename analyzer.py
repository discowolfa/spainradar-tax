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
        data = self.analyze_item("", "", text)

        parts = []
        if data.get("summary"):
            parts.append(f"Кратко: {data['summary']}")
        if data.get("analysis"):
            parts.append(f"Анализ: {data['analysis']}")
        if data.get("importance"):
            parts.append(f"Почему важно: {data['importance']}")

        return "\n\n".join(parts) or sanitize_text(text)

    def analyze_item(self, title: str, link: str, summary: str) -> dict:
        if self.logger:
            self.logger.debug("Analyzing text from source")

        clean_title = sanitize_text(title)
        clean_link = sanitize_text(link)
        clean_summary = sanitize_text(summary)
        clean_text = (
            f"Title: {clean_title}\n"
            f"Link: {clean_link}\n"
            f"Summary: {clean_summary}"
        ).strip()

        if not clean_text:
            return self._fallback_result(clean_title, clean_summary)

        if not self.client:
            if self.logger:
                self.logger.warning("OPENAI_API_KEY is not set; using raw sanitized text")
            return self._fallback_result(clean_title, clean_summary)

        prompt = (
            "You are an editor for a Russian-language Telegram channel about taxes, "
            "law, finance, and official news in Spain. Translate the news item into "
            "clear Russian and prepare a concise channel post. Return only JSON with "
            'keys "priority", "headline", "summary", "analysis", "audience", and "action". '
            'Priority must be one of "high", "medium", or "low". Use "high" for '
            "mandatory obligations, deadlines, fines, tax returns, BOE/legal changes, "
            "AEAT/Hacienda or Seguridad Social changes affecting residents, autónomos, "
            'companies, payments, inspections, or official campaigns. Use "medium" '
            "for useful clarifications, instructions, procedures, or practical updates "
            'without clear urgency. Use "low" for statistics, reports, announcements, '
            "press releases, and general background information. If deadlines, fines, "
            'mandatory forms, BOE, or changes in tax obligations are present, priority '
            'must be "high". '
            "Headline must be one short Russian sentence without emoji. Summary, "
            "analysis, audience, and action must each be 1-2 short sentences. Keep it "
            "practical for residents, autónomos, companies, or investors in Spain. "
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
            return self._fallback_result(clean_title, clean_summary)

        return {
            "priority": self._normalize_priority(str(data.get("priority", ""))),
            "headline": sanitize_text(str(data.get("headline", ""))) or clean_title,
            "summary": sanitize_text(str(data.get("summary", ""))) or clean_summary,
            "analysis": sanitize_text(str(data.get("analysis", ""))),
            "audience": sanitize_text(str(data.get("audience", ""))),
            "action": sanitize_text(str(data.get("action", ""))),
        }

    def _normalize_priority(self, priority: str) -> str:
        priority = sanitize_text(priority).lower()
        if priority in {"high", "medium", "low"}:
            return priority
        return "medium"

    def _fallback_result(self, title: str, summary: str) -> dict:
        return {
            "priority": "medium",
            "headline": title,
            "summary": summary or title,
            "analysis": "Проверьте официальный источник перед принятием решений.",
            "audience": "Резидентов Испании, autónomos, компании и инвесторов.",
            "action": "Сохраните ссылку и уточните детали у профильного специалиста при необходимости.",
        }
