# memoriX — Rapport de validation après la partie 18

## Révision fonctionnelle auditée

- Branche : elwen
- Commit fonctionnel de base : 429a4554ce3fea32b1dce451dee31dabd2871b82
- Validation initiale partie 17 : 2026-07-15 14:24:26 +02:00
- Validation opérationnelle partie 18 : 2026-07-16
- Python : Python 3.10.11
- Bun : 1.3.14

## Résultats automatiques

| Contrôle | Résultat |
|---|---|
| Typecheck OpenCode | PASS |
| Tests TypeScript memoriX | PASS |
| Suite Python complète, incluant Project Archive | PASS |
| Compilation des scripts MCP, Live Probe et benchmark | PASS |
| Contrat hot-only | PASS |
| Recherche cold explicite uniquement | PASS |
| Isolation du runtime de test | PASS |
| Protection du prototype Titan d'Antoine | PASS |
| Project Archive append-only et snapshots versionnés | PASS |
| Outils MCP Project Archive | PASS |
| Client, service et outils OpenCode Project Archive | PASS |
| Permissions natives des mutations Project Archive | PASS |
| Exclusions obligatoires des hooks | PASS |
| Absence d'écriture Titan par Project Archive | PASS |
| Runner nightly protégé et verrou exclusif | PASS |
| Journal `latest.json` et historique `runs.jsonl` | PASS |
| CLI et wrapper PowerShell nightly | PASS |
| Outil natif OpenCode `memory_nightly_run` | PASS |
| Permission native avant nightly OpenCode | PASS |
| Exclusion du nightly dans les hooks | PASS |
| Tâche Windows quotidienne à 02:00 | PASS |
| Exécution immédiate via Task Scheduler | PASS |
| `LastTaskResult = 0` et statut `completed` | PASS |

## Validation manuelle OpenCode

Le scénario complet de gestion des candidates a validé :

- `memory_status` sur un runtime propre ;
- liste vide des candidates initiales ;
- création d'une candidate pending ;
- absence de retrieval avant validation ;
- validation vers le Titan hot site ;
- retrieval de la mémoire active validée ;
- création et rejet d'une seconde candidate ;
- absence de retrieval de la candidate rejetée ;
- consolidation manuelle créant une candidate pending ;
- aucune validation automatique.

État final observé pendant ce scénario :

- candidates pending : 1 ;
- candidates validated : 1 ;
- candidates rejected : 1 ;
- mémoires Titan actives : 1 ;
- événements short-term : 2 ;
- événements cold archive : 2.

## Live Probe

- statut : healthy ;
- checks failed : 0 ;
- lecture seule : true ;
- runtime modifié : false ;
- gateway instanciée : false ;
- Titan chargé : false.

## Architecture validée

1. écriture short-term et cold archive ;
2. candidates pending ;
3. validation humaine logique ;
4. rejet sans écriture Titan ;
5. Titan active hot site ;
6. retrieval hot-only ;
7. consolidation sans validation automatique ;
8. gateway Python ;
9. serveur MCP ;
10. client et service TypeScript ;
11. outils natifs OpenCode ;
12. hooks OpenCode configurables ;
13. observations adaptatives et dry-run ;
14. benchmark isolé ;
15. Live Probe read-only;
16. runtime par défaut hors dépôt;
17. permissions natives des mutations;
18. exclusions obligatoires des hooks;
19. Project Archive append-only;
20. snapshots de projet versionnés;
21. intégration Project Archive Gateway, MCP et OpenCode;
22. runner nightly protégé;
23. verrou exclusif et récupération de verrou périmé;
24. journal opérationnel append-only;
25. CLI Python et wrapper PowerShell;
26. outil natif OpenCode `memory_nightly_run`;
27. permission native du nightly;
28. exclusion du nightly dans les hooks;
29. tâche Windows quotidienne;
30. exécution Task Scheduler validée avec résultat Windows `0`.

## Validation opérationnelle du nightly

Le scénario Windows réel a validé :

- runtime `%LOCALAPPDATA%\memoriX\runtime`, hors dépôt;
- test manuel avec conservation de la mémoire court terme;
- installation de `memoriX Nightly Consolidation` à 02:00;
- action PowerShell pointant vers `run_memorix_nightly.ps1`;
- trigger memoriX `task_scheduler`;
- lancement immédiat par `Start-ScheduledTask`;
- état final Windows `Ready`;
- `LastTaskResult` égal à `0`;
- statut memoriX `completed`;
- absence de verrou résiduel;
- dépôt Git inchangé après les tests opérationnels.

## Limites restant à traiter

- adaptatif connecté au runtime réel ;
- transactions générales ;
- migrations et reprise après crash ;
- tests de concurrence, corruption, saturation et multiplateforme.

Les actions adaptatives, la validation automatique, la réhydratation cold vers hot et la suppression physique restent volontairement désactivées.

## Validation Project Archive

Le flux validé couvre :

1. création d'entrées structurées append-only;
2. filtrage par projet et type;
3. reconstruction déterministe du snapshot;
4. incrément des versions sans écrasement;
5. persistance après redémarrage de la gateway;
6. protocole MCP `tools/call`;
7. client et service TypeScript non bloquants;
8. outils natifs OpenCode;
9. confirmation des mutations;
10. lectures sans permission de mutation;
11. exclusion obligatoire des hooks;
12. absence d'écriture dans Titan.

## Part 19 capacity and saturation validation

Part 19 validates runtime capacity inspection, admission rejection before
Titan writes, pending-candidate preservation, controlled soft pruning,
operational locking and logs, MCP/OpenCode exposure, and bounded synthetic
scenarios through 6,000,000 active items. Benchmarks do not modify runtime data
or access the cold site.

## Part 20 memory-pressure validation

Part 20 adds deterministic per-memory metrics, read-only runtime inspection, CLI simulation, MCP and OpenCode exposure, bounded benchmarks, and safety documentation.

## Part 21 adaptive retention validation

Part 21 validates deterministic scoring, explainable decisions, persisted-runtime ranking, bounded simulation, MCP and OpenCode exposure, synthetic benchmarks, and the strict no-mutation/no-cold-site/no-Titan contract. Detailed evidence is in `docs/MEMORIX_RETENTION_VALIDATION.md`.

## Part 22 adaptive-routing validation

Part 22 validates deterministic decisions, runtime inspection, MCP/OpenCode contracts, and bounded simulations through 6,000,000 memories.

## Part 23 policy-search validation

Part 23 validates runtime-aware policy search, MCP, OpenCode, and bounded benchmarks.

## Part 24 policy lifecycle validation

Part 24 validates registry persistence, review, activation, rollback, MCP, OpenCode, and benchmarks.


## Part 25 topic-block validation

See `docs/MEMORIX_TOPIC_BLOCKS.md` and `docs/MEMORIX_TOPIC_BLOCKS_VALIDATION.md`.

## Part 26 - controlled consolidation

memoriX now supports reviewed consolidation plans, local session state, scheduling, recovery, MCP, and OpenCode integration.

## Part 27 - Observability

Bounded diagnostics, snapshots, alerts, drift comparison, and continuous evaluation are available without loading Titan or mutating memory policies.
## Part 28 validation

The final release suite covers read-only readiness inspection, safe runtime archive verification, atomic restore, path traversal rejection, and an isolated QuickTemp event-to-Titan acceptance workflow.
