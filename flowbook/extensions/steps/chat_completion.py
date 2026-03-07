"""Chat completion step: single-turn OpenAI completion. Requires flowbook[ai] and OPENAI_API_KEY."""

from __future__ import annotations

import os
from typing import Any

from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("chat_completion")
class ChatCompletionOp(BaseOp):
    """Single-turn OpenAI chat completion. Uses OPENAI_API_KEY."""

    class Inputs(BaseInputs):
        prompt: str
        messages: list[dict[str, Any]] | None = None
        system_prompt: str | None = None

    class Outputs(BaseOutputs):
        response: str

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError(
                "chat_completion requires openai. Install with: pip install flowbook[ai]"
            ) from e

        inp = self.Inputs.model_validate(inputs)

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")

        client = OpenAI(api_key=api_key)
        messages = []
        if inp.system_prompt and inp.system_prompt.strip():
            messages.append({"role": "system", "content": inp.system_prompt.strip()})
        if inp.messages:
            for m in inp.messages:
                if isinstance(m, dict) and m.get("role") and m.get("content") is not None:
                    messages.append({"role": m["role"], "content": str(m["content"])})
        messages.append({"role": "user", "content": inp.prompt})
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=512,
        )
        content = resp.choices[0].message.content or ""
        return self.Outputs(response=content).model_dump(mode="python")


register = register_from_steps()
