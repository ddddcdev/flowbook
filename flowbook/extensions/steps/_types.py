"""Shared step types. pd.DataFrame needs WithJsonSchema for Pydantic JSON schema generation."""

from __future__ import annotations

from typing import Annotated

import pandas as pd
from pydantic import WithJsonSchema

DataFrame = Annotated[
    pd.DataFrame,
    WithJsonSchema({"type": "object", "title": "DataFrame", "description": "pandas DataFrame"}),
]
