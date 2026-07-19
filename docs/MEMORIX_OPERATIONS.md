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
- `memory_status`;
- `project_archive_record` — mutation avec confirmation;
- `project_archive_list` — lecture seule;
- `project_snapshot_rebuild` — mutation avec confirmation;
- `project_snapshot_get` — lecture seule.

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

## Project Archive

Le Project Archive est un stockage cold explicite et append-only :

```text
<runtime>/cold_site/project_archive/
├── project_entries.jsonl
└── project_snapshots.jsonl
```

Outils MCP :

- `memorix_project_entry_record`;
- `memorix_project_entries_list`;
- `memorix_project_snapshot_rebuild`;
- `memorix_project_snapshot_get`.

Les entrées structurées sont immuables. Chaque reconstruction ajoute une nouvelle version de snapshot. Aucune de ces opérations n'écrit dans Titan et aucune donnée Project Archive n'est utilisée comme fallback de retrieval.

Permissions OpenCode :

- `project_archive_record` : `ask`;
- `project_snapshot_rebuild` : `ask`;
- `project_archive_list` : lecture seule;
- `project_snapshot_get` : lecture seule.

Les quatre outils sont obligatoirement exclus des hooks.

## Nightly protégé

Le nightly utilise un runner unique avec verrou, historique append-only et état terminal :

```text
<runtime>/operations/nightly/
├── latest.json
├── runs.jsonl
└── nightly.lock
```

Commandes principales :

```powershell
$RuntimeRoot = Join-Path $env:LOCALAPPDATA "memoriX\runtime"

& ".\scripts\run_memorix_nightly.ps1" `
    -RuntimeRoot $RuntimeRoot `
    -KeepShortTerm `
    -Trigger "manual"

& ".\scripts\install_memorix_nightly_task.ps1" `
    -TaskName "memoriX Nightly Consolidation" `
    -RuntimeRoot $RuntimeRoot `
    -DailyAt "02:00"
```

L'outil OpenCode `memory_nightly_run` demande une permission native avant exécution. Il est exclu des hooks et utilise `clear_short_term_after_success=true` par défaut.

La procédure complète d'installation, de vérification et de dépannage est décrite dans [MEMORIX_NIGHTLY_OPERATIONS.md](MEMORIX_NIGHTLY_OPERATIONS.md).

## Capacity operations

Use `memory_capacity_status` for inspection,
`memory_capacity_plan` for a dry-run plan, and
`memory_capacity_prune` for explicitly approved soft deactivation. Capacity
logs are stored outside Git under `<runtime>/operations/capacity/`. Detailed
procedures are in `MEMORIX_CAPACITY_OPERATIONS.md`.

## Memory pressure operations

Use `memorix_memory_pressure.py` for local diagnosis, or the read-only MCP/OpenCode pressure tools. Synthetic counts up to 6,000,000 do not allocate equivalent objects.

## Retention-ranking operations

Use `scripts/memorix_retention_ranking.py` for local diagnostics and the MCP/OpenCode retention-ranking tools for integrated inspection. All operations are read-only. The synthetic benchmark is `scripts/memorix_retention_ranking_benchmark.py`.
