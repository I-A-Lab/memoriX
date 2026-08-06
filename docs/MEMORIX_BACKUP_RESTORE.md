# memoriX runtime backup and restore

Runtime data is deliberately outside the source repository. Backups are ZIP archives with a versioned manifest and SHA-256 hash for every file.

## Backup

```powershell
py -3.10 .\tools\memorix\operations\memorix_runtime_backup.py `
    "$env:LOCALAPPDATA\memoriX\runtime" `
    "$env:USERPROFILE\Documents\memorix-runtime.zip" `
    --pretty
```

## Restore

OpenCode must be closed before restore.

```powershell
py -3.10 .\tools\memorix\operations\memorix_runtime_restore.py `
    "$env:USERPROFILE\Documents\memorix-runtime.zip" `
    "$env:LOCALAPPDATA\memoriX\runtime-restored" `
    --pretty
```

A non-empty destination is rejected unless `--overwrite` is explicitly supplied. Archive paths, file sizes, and hashes are checked before replacement.
