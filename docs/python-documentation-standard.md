# Python documentation standard — signalforge-nsemine

Adopted selectively from
[SignalForge's Python documentation standard](https://github.com/harishkamathuk/signalforge/blob/develop/docs/python-documentation-standard.md).

## Public API contracts
Write Google-style docstrings for **new or materially changed** public modules,
functions, classes and methods. Explain where relevant:

- Arguments, return shapes and what `None` signifies.
- Whether output is raw NSE JSON or processed data.
- Whether operations are synchronous or asynchronous.
- Timestamp units and timezone interpretation where the API handles market data.
- Exceptions, side effects, caching and external-service limitations.

Use `Args:`, `Returns:`, `Raises:` and `Notes:` only when useful.
Private helpers need a docstring when an important invariant would otherwise be unclear.

## Rationale comments
Explain **why** a non-obvious transport, session, retry, identity or timestamp
behaviour exists—not merely what the next statement does. Retain original upstream
contracts unless a change is separately assessed and covered by tests.

Do not rewrite unrelated legacy docstrings merely to satisfy a new style preference.
