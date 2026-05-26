# Pricing Policy

Provider pricing changes often. Sponge must never hardcode public cost claims
from memory or stale documentation.

## Source Of Truth

Runtime pricing should come from a versioned local pricing file, not scattered
constants in documentation or tests. The planned file is:

```text
src/sponge/llm/pricing.toml
```

Each entry should include:

- provider
- model
- input token price
- output token price
- prompt cache write multiplier, if supported
- prompt cache read multiplier, if supported
- effective date
- source URL
- retrieval date
- notes for provider-specific semantics

## Documentation Rules

Docs may explain pricing mechanics, but must not present provider prices as
current unless generated from the versioned pricing file or manually refreshed
with a cited retrieval date.

Allowed:

- "Prompt cache read pricing differs by provider."
- "The cost estimator uses the configured pricing table and records actual usage
  when the provider reports it."
- "Example only: values in this table are illustrative."

Not allowed:

- "Provider X cache reads cost exactly 10%" unless the pricing file and source
  date are cited.
- "Model Y costs `$N` per million tokens" in docs without source and date.
- Tests that assert real provider prices directly.

## Estimation Rules

Cost estimation is a pre-call risk control, not an invoice.

- Mark pre-call values as estimated.
- Prefer provider-reported usage for final accounting.
- Record estimator error when actual cost differs from estimated cost by more
  than the configured tolerance.
- Circuit breakers may use estimates before a call, but reports must distinguish
  estimated, actual, and reconciled cost.

## Provider Capability Rules

Every provider implementation should declare capabilities that affect cost:

- tokenizer family
- supports streaming usage events
- supports prompt caching
- prompt cache TTL options
- supports server-side tool-result clearing
- supports images
- supports PDFs
- supports tool calls

When the configured provider changes, Sponge should warn if cache economics,
multimodal support, tokenization, or context-compression features change.

## Review Checklist

Before merging docs or code that mention pricing:

- Is every numeric price sourced and dated?
- Is the claim workload-scoped?
- Does it distinguish estimate from actual cost?
- Does it avoid assuming provider cache semantics are interchangeable?
- Does it avoid claiming budget ceilings as savings?
