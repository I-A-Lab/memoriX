<p align="center">
  <picture>
    <source srcset="packages/console/app/src/asset/logo-ornate-dark.svg" media="(prefers-color-scheme: dark)">
    <source srcset="packages/console/app/src/asset/logo-ornate-light.svg" media="(prefers-color-scheme: light)">
    <img src="packages/console/app/src/asset/logo-ornate-light.svg" alt="memoriX logo">
  </picture>
</p>
<p align="center">The open source AI coding agent powered by advanced long-term memory.</p>
<p align="center">
  <a href="README.md">English</a> |
  <a href="README.fr.md">Français</a>
</p>

---

## Qu'est-ce que memoriX ?

**memoriX** est un agent de codage IA open source de nouvelle génération. Il ne se contente pas de générer du code : il dispose d'un système de mémoire à long terme avancé (via une intégration MCP et Titan) lui permettant d'orchestrer un cycle de développement logiciel (SDLC) complet, de retenir le contexte de manière durable, de gérer la pression de la mémoire, et d'apprendre des sessions précédentes.

### Fonctionnalités Clés

- **Orchestration SDLC Multi-Agents** : memoriX intègre un workflow complexe avec des agents spécialisés (`sdlc`, `dev_branch`, `test_branch`, `sdlc-orchestrator`) qui valident les besoins, créent des plans, implémentent le code et génèrent des tests de manière isolée et sécurisée.
- **Mémoire à Long Terme (Titan)** : Intégration d'une mémoire persistante, incluant des scores de rétention adaptatifs, une consolidation contrôlée, des blocs de sujets dynamiques, et des diagnostics de pression de la mémoire.
- **Recherche et cycle de vie des politiques de mémoire** : Modélisation, évaluation et validation de différentes politiques de rétention avant leur application.
- **Observabilité et Diagnostics** : Outils intégrés pour évaluer la capacité et la saturation de la mémoire jusqu'à des millions d'éléments sans impacter les performances de l'espace de travail actif.

---

## Installation

```bash
# YOLO
curl -fsSL https://memorix.ai/install | bash

# Package managers
npm i -g memorix@latest        # or bun/pnpm/yarn
scoop install memorix          # Windows
choco install memorix          # Windows
brew install memorix           # macOS and Linux
```

> [!TIP]
> Si vous utilisiez d'anciennes versions de l'outil, veillez à les désinstaller avant d'installer memoriX.

### Desktop App (BETA)

memoriX est également disponible en tant qu'application de bureau.

| Platform              | Download                           |
| --------------------- | ---------------------------------- |
| macOS (Apple Silicon) | `memorix-desktop-mac-arm64.dmg`   |
| macOS (Intel)         | `memorix-desktop-mac-x64.dmg`     |
| Windows               | `memorix-desktop-windows-x64.exe` |
| Linux                 | `.deb`, `.rpm`, or `.AppImage`     |

```bash
# macOS (Homebrew)
brew install --cask memorix-desktop
# Windows (Scoop)
scoop bucket add extras; scoop install extras/memorix-desktop
```

---

## Les Agents memoriX

memoriX intègre un workflow exclusif basé sur une orchestration SDLC (Software Development Life Cycle). Ses agents spécialisés sont conçus pour structurer la création logicielle via une mémoire partagée persistante.

- **sdlc** — Clarifie les exigences, produit les PRD/SRS et les plans, demande des approbations explicites, délègue l'implémentation et les tests, et gère la validation.
- **dev_branch** — Implémente le code de l'application à partir de contrats immuables approuvés.
- **test_branch** — Crée des tests automatisés ciblés indépendamment de l'implémentation.
- **sdlc-orchestrator** — Évalue les résultats des tests et gère les cycles de correction délimités.

Les outils natifs de mémoire sont enregistrés dans le registre partagé et accessibles à `sdlc`, `dev_branch`, et `test_branch` selon leurs permissions.

---

## Architecture de la Mémoire (memoriX Integration)

Le cœur de memoriX est son système de mémoire externe. Il inclut :

- **Diagnostics de pression de la mémoire** : État de la pression en lecture seule et inspection via Python, MCP et des outils natifs. (Voir `docs/MEMORIX_MEMORY_PRESSURE.md`)
- **Scoring adaptatif de rétention** : memoriX classe les mémoires du hot-site en utilisant des scores déterministes et explicables (dry-run). (Voir `docs/MEMORIX_RETENTION_SCORING.md`)
- **Routage adaptatif** : Construction de plans d'admission et d'élagage explicables basés sur les signaux de capacité et de rétention.
- **Capacité et saturation** : Inspection de capacité du hot-site, élagage "soft", et validation synthétique jusqu'à 6 millions d'éléments actifs.
- **Recherche de politique de mémoire** : Comparaison des politiques de rétention et de routage sans appliquer la politique. (Voir `docs/MEMORIX_POLICY_SEARCH.md`)
- **Blocs de sujets dynamiques** : Structuration de la mémoire. (Voir `docs/MEMORIX_TOPIC_BLOCKS.md`)
- **Consolidation contrôlée** : Plans de consolidation approuvés manuellement, planification, récupération et intégration MCP.
- **Observabilité** : Diagnostics délimités, snapshots, alertes, et évaluation continue sans impacter le moteur Titan.

Consultez la documentation spécifique :
- [Architecture](docs/MEMORIX_FINAL_ARCHITECTURE.md)
- [Operations](docs/MEMORIX_OPERATIONS.md)
- [Nightly operations](docs/MEMORIX_NIGHTLY_OPERATIONS.md)
- [Validation report](docs/MEMORIX_VALIDATION_REPORT.md)

---

## Scripts & Lancement

Le projet dispose d'un lanceur PowerShell pour démarrer l'application avec toute la configuration memoriX prête à l'emploi (serveur MCP inclus, runtime validé) :

```bash
# Lancement de memoriX (Windows)
.\scripts\start_opencode_with_memorix.ps1
```

*(Note : le script PowerShell effectue des validations de sécurité sur le runtime pour garantir que la mémoire est bien séparée du dépôt du code).*

---

## Contribuer

Si vous souhaitez contribuer à memoriX, veuillez lire notre [guide de contribution](./CONTRIBUTING.md) avant de soumettre une pull request.

**Rejoignez notre communauté :** [Discord](https://discord.gg/memorix) | [X.com](https://x.com/memorix)
