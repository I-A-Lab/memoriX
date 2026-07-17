# memoriX — Architecture cible et état actuel

## Objectif

memoriX fournit une mémoire longue durée contrôlée à OpenCode et à ses agents, sans remplacer leur architecture d'orchestration.

La mémoire Python est accessible uniquement par une frontière contrôlée :

```text
OpenCode et agents
        |
        | outils natifs et hooks optionnels
        v
Service memoriX TypeScript
        |
        | MCP JSON-RPC sur stdio
        v
Serveur MCP Python
        |
        v
MemoriXGateway
        |
        +-- short-term memory
        +-- cold archive append-only
        +-- Project Archive append-only et snapshots versionnés
        +-- pending candidates
        +-- validation ou rejet
        +-- Titan active hot site
        +-- consolidation
        +-- nightly protégé
        +-- observations adaptatives
```

OpenCode ne lit et ne modifie jamais directement les fichiers du runtime Python.

## Outils natifs OpenCode

- `memory_store` propose une candidate en attente de validation ;
- `memory_retrieve` recherche uniquement dans les mémoires Titan actives ;
- `memory_candidates_list` liste les candidates par statut ;
- `memory_candidate_validate` valide une candidate et écrit dans Titan ;
- `memory_candidate_reject` rejette une candidate sans écriture Titan ;
- `memory_consolidate` transforme les événements short-term en candidates pending ;
- `memory_nightly_run` lance le nightly protégé après confirmation ;
- `memory_status` retourne l'état de l'architecture et du stockage;
- `project_archive_record` ajoute une entrée structurée après confirmation;
- `project_archive_list` lit les entrées du projet;
- `project_snapshot_rebuild` ajoute une nouvelle version de snapshot après confirmation;
- `project_snapshot_get` lit le dernier snapshot.

## Contrat de récupération

La récupération conversationnelle normale est strictement hot-site only :

```text
memory_retrieve
    -> Titan active hot site
    -> aucun fallback automatique vers le cold site
```

La recherche cold est une opération distincte et explicite :

```text
memorix_search_cold_history
    -> cold archive
    -> audit ou diagnostic uniquement
```

Il n'existe aucune réhydratation automatique du cold site vers Titan.

## Cycle d'une information

1. Un événement est écrit dans la short-term memory.
2. Le même événement est archivé directement dans le cold site.
3. Une candidate peut être proposée explicitement ou créée par consolidation.
4. Une candidate pending reste invisible à `memory_retrieve`.
5. Une validation transforme la candidate en mémoire Titan active.
6. Une candidate rejetée ne crée aucune mémoire Titan.
7. Le soft-forget désactive une mémoire active sans supprimer l'historique cold.

## Hooks OpenCode

Les hooks peuvent enregistrer les messages et les résultats d'outils lorsque leur capture est activée.

Tous les outils mémoire et Project Archive sont des exclusions obligatoires des hooks afin d'éviter qu'une opération mémoire enregistre son propre résultat.

## Project Archive

Le Project Archive est une branche cold explicite, distincte de l'historique brut :

```text
runtime/cold_site/project_archive/
├── project_entries.jsonl
└── project_snapshots.jsonl
```

Les entrées et snapshots sont append-only. Les snapshots sont reconstruits de manière déterministe à partir des entrées du projet et leur version augmente sans écrasement silencieux. Le Project Archive n'est jamais interrogé automatiquement par `memory_retrieve`, ne réhydrate jamais Titan et n'est pas modifié par le nightly.

## Adaptive Memory

Les composants adaptatifs disponibles comprennent :

- memory pressure et historique de pression ;
- Topic Blocks dynamiques ;
- routage logique des mémoires ;
- recommandations de capacité ;
- plans de soft pruning ;
- décisions du contrôleur adaptatif ;
- benchmark synthétique isolé.

Ces fonctions restent en observation ou dry-run. Elles ne modifient ni le hot site ni le cold site automatiquement.

## Live Probe

Le Live Probe inspecte un runtime en lecture seule. Il ne charge pas Titan, n'instancie pas la gateway, n'appelle pas le retrieval et ne crée aucun fichier.

## État fonctionnel validé

- enregistrement short-term et cold : fonctionnel ;
- candidates pending : fonctionnel ;
- validation vers Titan : fonctionnelle ;
- rejet sans écriture Titan : fonctionnel ;
- retrieval hot-only : fonctionnel ;
- consolidation sans validation automatique : fonctionnelle ;
- statut OpenCode : fonctionnel ;
- Live Probe read-only : fonctionnel ;
- intégration MCP et OpenCode : fonctionnelle;
- Project Archive Gateway, MCP et OpenCode : fonctionnel;
- permissions natives des mutations : fonctionnelles;
- exclusions obligatoires des hooks : fonctionnelles;
- runtime par défaut hors dépôt : fonctionnel;
- runner nightly protégé, verrou et journal opérationnel : fonctionnels;
- outil natif OpenCode `memory_nightly_run` : fonctionnel;
- tâche Windows quotidienne installable et vérifiée : fonctionnelle.

## Travaux encore nécessaires

- observations adaptatives alimentées par le runtime réel ;
- transactions générales, migrations et reprise après crash ;
- validation finale de concurrence, corruption, saturation et compatibilité multiplateforme.

L'architecture d'agents d'Antoine reste la couche d'orchestration principale.

## Capacity control plane

The capacity control plane combines read-only runtime inspection, admission
control, dry-run pruning plans, a mutation lock, append-only operational logs,
MCP tools, and native OpenCode tools. Status and plan operations are read-only;
pruning is permission-gated and performs logical hot-site deactivation only.

## Memory pressure plane

The pressure plane sits between persisted hot-site metadata and future adaptive routing. It provides explainable read-only assessments and bounded aggregate reports.
