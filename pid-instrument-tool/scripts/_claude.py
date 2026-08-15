"""Claude Messages API 공통 헬퍼.

- 구조화 출력(output_config.format)으로 스키마를 강제해 응답 포맷을 고정한다.
- 시스템 프롬프트(규칙 문서)는 도면마다 동일하므로 prompt caching을 건다.
  도면 수십 장을 연속 판독할 때 규칙 문서 토큰을 반복해서 물지 않는다.
- 도면 이미지는 입력이 크고 출력도 길어질 수 있어 항상 스트리밍으로 호출한다.
"""
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

MODEL_DEFAULT = "claude-opus-5"
MAX_TOKENS = 32000


def _client():
    try:
        import anthropic
    except ImportError:
        sys.exit("[!] anthropic 패키지가 없습니다.  pip install -r requirements.txt")
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        sys.exit("[!] ANTHROPIC_API_KEY 환경변수를 설정하세요.\n"
                 "    export ANTHROPIC_API_KEY=sk-ant-...")
    return anthropic.Anthropic()


def image_block(path: Path | str) -> dict:
    """PNG 파일을 이미지 콘텐츠 블록으로 만든다."""
    p = Path(path)
    data = base64.standard_b64encode(p.read_bytes()).decode()
    suffix = p.suffix.lower()
    media = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
             ".webp": "image/webp", ".gif": "image/gif"}.get(suffix, "image/png")
    return {"type": "image", "source": {"type": "base64", "media_type": media, "data": data}}


def call_structured(system: str, content: list[dict], schema: dict, *,
                    model: str = MODEL_DEFAULT, effort: str = "high",
                    max_tokens: int = MAX_TOKENS, progress: bool = True) -> dict:
    """구조화 출력으로 한 번 호출하고 파싱된 dict를 돌려준다."""
    client = _client()
    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": content}],
    )

    with client.messages.stream(**kwargs) as stream:
        if progress:
            n = 0
            for _ in stream.text_stream:
                n += 1
                if n % 40 == 0:
                    print(f"\r    …생성 중 {n}청크", end="", file=sys.stderr, flush=True)
            if n:
                print("\r" + " " * 30 + "\r", end="", file=sys.stderr)
        message = stream.get_final_message()

    if message.stop_reason == "refusal":
        raise RuntimeError(f"모델이 요청을 거절했습니다: {getattr(message, 'stop_details', None)}")
    if message.stop_reason == "max_tokens":
        raise RuntimeError("max_tokens에 도달해 응답이 잘렸습니다. --max-tokens를 올리거나 "
                           "도면을 나눠서 실행하세요.")

    text = next((b.text for b in message.content if b.type == "text"), "")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"응답을 JSON으로 해석하지 못했습니다: {e}\n{text[:800]}") from e

    u = message.usage
    cached = getattr(u, "cache_read_input_tokens", 0) or 0
    print(f"    토큰 입력 {u.input_tokens + cached:,} (캐시 {cached:,}) / 출력 {u.output_tokens:,}",
          file=sys.stderr)
    return data
