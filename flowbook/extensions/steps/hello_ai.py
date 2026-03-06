"""Hello AI step: single-turn OpenAI completion demo. Requires flowbook[ai] and OPENAI_API_KEY."""

from __future__ import annotations

import os
from typing import Any

from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("hello_ai")
class HelloAIOp(BaseOp):
    """Single-turn OpenAI completion. Demo step for AI integration."""

    class Inputs(InputsBase):
        PROMPT = "prompt"
        REQUIRED = (PROMPT,)
        OPTIONAL = ()

    class Outputs(OutputsBase):
        RESPONSE = "response"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError(
                "hello_ai requires openai. Install with: pip install flowbook[ai]"
            ) from e

        prompt = inputs[self.Inputs.PROMPT]
        if not isinstance(prompt, str):
            raise TypeError(f"prompt must be str, got {type(prompt).__name__}")

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")

        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
        )
        content = resp.choices[0].message.content or ""
        return {self.Outputs.RESPONSE: content}


register = register_from_steps()
