# memoriX — Guide d'utilisation et de validation

## Préparation

```powershell
Set-Location "D:\Ecole\Vietnam Projet\memoriX"

$PythonExe = (
    py -3.10 -c "import sys; print(sys.executable)"
).Trim()
```

## Règle de runtime

Les tests et validations manuelles doivent utiliser un runtime extérieur au dépôt :

```powershell
$RuntimeRoot = Join-Path `
    $env:TEMP `
    "memorix-runtime"
```

Le dossier `memory/runtime` ne doit pas être créé par les tests.

## Prévalidation du lanceur OpenCode

```powershell
& "scripts\start_opencode_with_memorix.ps1" `
    -RuntimeRoot $RuntimeRoot `
    -ValidateOnly
```

## Lancement OpenCode avec memoriX

```powershell
& "scripts\start_opencode_with_memorix.ps1" `
    -RuntimeRoot $RuntimeRoot `
    -ResetRuntime
```

## Outils OpenCode

- `memory_store` ;
- `memory_retrieve` ;
- `memory_candidates_list` ;
- `memory_candidate_validate` ;
- `memory_candidate_reject` ;
- `memory_consolidate` ;
- `memory_status`.

Une candidate pending ou rejected ne doit jamais être retournée par `memory_retrieve`.

## Typecheck OpenCode

```powershell
bun run --cwd "packages\opencode" typecheck
```

## Tests TypeScript memoriX

```powershell
bun test `
    --cwd "packages\opencode" `
    --timeout 120000 `
    "test/memorix"
```

## Tests Python

Limiter les threads numériques évite les ralentissements excessifs de Torch et de BLAS :

```powershell
$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:NUMEXPR_NUM_THREADS = "1"

$env:MEMORIX_RUNTIME_ROOT = Join-Path `
    $env:TEMP `
    "memorix-python-tests"

& $PythonExe -m unittest discover `
    -s "tests\memory" `
    -p "test_*.py"
```

Sous Windows PowerShell 5.1, `unittest` peut écrire son affichage normal sur stderr. La validation réelle repose sur `$LASTEXITCODE` et sur la ligne `OK`.

## Serveur MCP

```powershell
& $PythonExe "scripts\memorix_mcp_server.py"
```

Le serveur attend des requêtes JSON-RPC sur stdin et répond sur stdout.

## Benchmark adaptatif

```powershell
& $PythonExe `
    "scripts\memorix_adaptive_design_benchmark.py"
```

Le benchmark utilise des scénarios synthétiques et n'applique aucune action.

## Live Probe

```powershell
& $PythonExe `
    "scripts\memorix_live_probe.py" `
    $RuntimeRoot
```

Résultat attendu :

```text
status: healthy
checks_failed: 0
read_only: true
runtime_modified: false
```

## Variables principales

- `MEMORIX_ENABLED` ;
- `MEMORIX_PYTHON_EXECUTABLE` ;
- `MEMORIX_PROJECT_ROOT` ;
- `MEMORIX_RUNTIME_ROOT` ;
- `MEMORIX_TIMEOUT_MS` ;
- paramètres `MEMORIX_TITAN_*` ;
- paramètres `MEMORIX_HOOK_*`.

## Contrats de sécurité

- retrieval hot-site only ;
- cold search explicite uniquement ;
- aucune validation automatique ;
- aucune réhydratation automatique ;
- aucune suppression physique du cold site ;
- fonctions adaptatives en observation ou dry-run ;
- outils mémoire exclus des hooks ;
- panne memoriX non bloquante pour OpenCode.

## Vérifications Git

```powershell
git status --short
git diff --check
git log -10 --oneline
```
