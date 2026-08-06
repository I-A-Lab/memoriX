# QuickTemp demonstration guide

## Preflight

```powershell
py -3.10 .\tools\memorix\validation\memorix_release_readiness.py --pretty
py -3.10 .\tools\memorix\validation\memorix_demo_smoke.py --pretty
opencode
```

## OpenCode prompts

1. `Create a very small Python project named QuickTemp that converts Celsius to Fahrenheit and Fahrenheit to Celsius. Always round to one decimal place.`
2. `Show the recent memoriX events related to QuickTemp.`
3. `Show the cold-site archive entries related to QuickTemp.`
4. `Consolidate the recent QuickTemp memory events.`
5. `List pending memory candidates related to QuickTemp.`
6. `Validate the pending QuickTemp candidate.`
7. `Retrieve the validated QuickTemp memory from the Titan hot site.`
8. `Add Kelvin conversion while keeping the existing QuickTemp conventions.`

Expected lifecycle: event to short term and cold history, candidate pending, human validation, Titan hot-site retrieval, then reuse during the Kelvin change.
