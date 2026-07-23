# Consolidation validation

The workflow keeps plans and sessions in `runtime/consolidation`. Execution records orchestration state only; it does not load Titan or access the cold site. Recovery clears interrupted local sessions without deleting history.
