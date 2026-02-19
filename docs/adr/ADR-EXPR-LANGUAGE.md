# ADR-EXPR-LANGUAGE: Expression language for filter_rows and expr_df

## Status

Accepted. filter_rows and expr_df use a constrained expression evaluator to avoid arbitrary code execution.

## Context

filter_rows and expr_df need to evaluate expressions over DataFrame columns (e.g. `A > 0`, `a + b`, string checks). Full Python eval would be unsafe for untrusted config.

## Decision

### Engine

- **filter_rows**: `DataFrame.query(expr, engine="python")`. Python engine allows broader syntax (e.g. `&`, `|`) than numexpr. Column names are in scope.
- **expr_df**: `DataFrame.eval(expr, engine="python")` per new column. Column names are in scope.

### Safety model

- Expressions are evaluated in a limited context: only column names and operators/functions allowed by pandas query/eval. No arbitrary attribute access or imports.
- Config authors must not inject expressions from untrusted user input without validation.
- Future: a whitelist of allowed functions or a small safe-eval DSL can be added if needed (document in this ADR).

### Limits

- `.str.contains()` and similar string methods are not directly available in query(); use expr_df to add a boolean column then filter_rows on it, or document supported patterns in spec.
- Date comparison and numeric/boolean logic are supported via engine="python".

## Consequences

- filter_rows and expr_df are suitable for pipeline configs authored by trusted operators or generated under constraints.
- For user-supplied expressions, additional validation or a stricter DSL should be considered and documented here.
