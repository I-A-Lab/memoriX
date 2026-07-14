# memoriX — Architecture finale

## Objectif

memoriX fournit une mémoire longue durée contrôlée pour OpenCode et ses agents. La mémoire Python est exposée à OpenCode par un serveur MCP, sans remplacer l’architecture d’agents existante.

## Architecture générale

```text
OpenCode / agents
        |
        | outils et hooks contrôlés
        v
Service memoriX TypeScript
        |
        | MCP stdio
        v
Serveur MCP Python
        |
        v
MemoriXGateway
        |
        +-- Short-term memory
        +-- Cold archive append-only
        +-- Candidates pending
        +-- Validation humaine
        +-- Titan hot site
        +-- Consolidation
        +-- Adaptive-memory observations
```

## Contrat de récupération

La récupération conversationnelle normale est strictement **hot-site only** :

```text
memory_retrieve
    -> Titan hot site
    -> aucun fallback automatiyue vers le cold site
```

La recherche dans l’historique cold est une opération explicite et distincte :

```text
cold audit search
    -> cold site
    -> diagnostic ou audit explicite uniquement
```

## Cycle d’une information

1. Un événement est enregistré en short-term et dans l’archive cold.
2. Une candidate mémoire peut être proposée.
3. La candidate reste invisible au retrieval tant qu’elle n’est pas validée.
4. Une validation humaine explicite transforme la candidate en mémoire Titan.
5. La mémoire validée devient disponible dans le retrieval hot-only.
6. Le soft-forget désactive logiquement une mémoire sans effacer l’historique cold.

## Topic Blocks

Les Topic Blocks sont dynamiques et issus du contenu observé. Ils enrichissent les métadonnées des mémoires validées, sans créer de partition physique de Titan et sans modifier le retrieval.

## Adaptive Memory

Les composants adaptatifs comprennent :

- memory pressure ;
- historique de pression ;
- Topic Blocks dynamiques ;
- recommandations de capacité ;
- plans de soft pruning ;
- contrôleur adaptatif global.

Les décisions adaptatives restent actuellement observation-only, dry-run, non appliquées, hot-site only, sans modification du cold site et sans changement du contrat de retrieval.

## Dynamic Capacity

La capacité dynamique produit des recommandations KEEP, WATCH ou EXPAND à partir de l’usage ratio, du momentum, de l’entropy, de la surprise et de la pressure persistence. Aucune capacité Titan n’est automatiquement modifiée.

## Soft Pruning

Le soft pruning produit des recommandations KEEP, WEAKEN ou DEACTIVATE. Elles ne provoquent aucune suppression physique, aucune mutation automatique du hot site et aucune modification du cold archive.

## Benchmark

Le benchmark isolé compare la baseline, pressure, Topic Blocks, dynamic capacity et adaptive controller sur des scénarios synthétiques. Il n’applique aucune action.

## Live Probe

Le Live Probe inspecte un runtime en lecture seule. Il n’instancie pas la gateway, ne charge pas Titan, n’appelle pas le retrieval et ne crée aucun fichier dans le runtime inspecté.

## Intégration OpenCode

L’intégration OpenCode est progressive :

- client MCP TypeScript isolé ;
- service memoriX non bloquant ;
- façades `memory_store` et `memory_retrieve` ;
- hooks activables individuellement ;
- comportement désactivé par défaut lorsqu’il n’est pas configuré.

L’architecture d’agents d’Antoine reste la couche d’orchestration principale.
