# memoriX — Guide d'utilisation et de validation

## Préparation

Se placer à la racine du dépôt :

```powershell
Set-Location "D:\Ecole\Vietnam Projet\memoriX"
```

Identifier l'exécutable Python 3.10 :

```powershell
$PythonExe = (
    py -3.10 -c "import sys; print(sys.executable)"
).Trim()
```

## Tests Python complets

```powershell
& $PythonExe -m unittest discover `
    -s "tests\memory" `
    -p "test_*.py" `
    -v
```

Sous Windows PowerShell 5.1, unittest peut écrire son affichage normal
sur stderr. Le code de sortie dans $LASTEXITCODE reste la validation
réelle.

## Typecheck OpenCode

```powershell
bun run --cwd "packages\opencode" typecheck
```

## Serveur MCP Python

```powershell
& $PythonExe "scripts\memorix_mcp_server.py"
```

Le serveur MCP utilise stdio et attend des requêtes JSON-RPC sur stdin.

## Benchmark adaptatif

```powershell
& $PythonExe "scripts\memorix_adaptive_design_benchmark.py"
```

Le benchmark utilise uniquement des scénarios synthétiques.

## Live Probe

```powershell
& $PythonExe "scripts\memorix_live_probe.py" "CHEMIN_DU_RUNTIME"
```

Le Live Probe inspecte le runtime en lecture seule.

## Variables OpenCode principales

```text
MEMORIX_ENABLED
MEMORIX_PYTHON_EXECUTABLE
MEMORIX_PROJECT_ROOT
MEMORIX_RUNTIME_ROOT
```

Les options exactes sont définies dans le service memoriX TypeScript.

## Règles de sécurité

- memory_retrieve utilise uniquement le hot site.
- Le cold site n'est jamais un fallback implicite.
- Une candidate pending n'est pas disponible au retrieval.
- La validation humaine reste explicite.
- Les fonctions adaptatives restent en dry-run.
- Les outils mémoire ne doivent pas déclencher leurs propres hooks.
- Un échec memoriX ne doit pas casser OpenCode.

## Commandes Git finales

```powershell
git status
git diff --check
git log -10 --oneline
```
