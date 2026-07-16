# memoriX — Rapport de validation après la partie 17

## Révision fonctionnelle auditée

- Branche : elwen
- Commit fonctionnel de base : 429a4554ce3fea32b1dce451dee31dabd2871b82
- Date de validation : 2026-07-15 14:24:26 +02:00
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
21. intégration Project Archive Gateway, MCP et OpenCode.

## Limites restant à traiter

- nightly planifié ;
- adaptatif connecté au runtime réel ;
- transactions et verrous ;
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
