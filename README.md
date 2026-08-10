<p align="center">
  <picture>
    <source srcset="packages/console/app/src/asset/logo-ornate-dark.svg" media="(prefers-color-scheme: dark)">
    <source srcset="packages/console/app/src/asset/logo-ornate-light.svg" media="(prefers-color-scheme: light)">
    <img src="packages/console/app/src/asset/logo-ornate-light.svg" alt="memoriX logo">
  </picture>
</p>
<p align="center">L'agent de codage IA open source propulsé par une mémoire à long terme avancée.</p>

---

## Qu'est-ce que memoriX ?

**memoriX** est un agent de codage IA de nouvelle génération, conçu pour les développeurs exigeants. Il ne se contente pas de générer du code ponctuel : grâce à son système de mémoire à long terme avancé (intégrant le moteur Titan et le protocole MCP), il est capable de retenir le contexte de vos projets de manière durable.

memoriX orchestre un cycle de développement logiciel (SDLC) complet et multi-agents. Il comprend le contexte global, gère la charge cognitive (pression de la mémoire) et apprend des sessions précédentes pour ne jamais répéter les mêmes erreurs.

### Fonctionnalités Clés

- 🧠 **Mémoire à Long Terme (Titan)** : Persistance intelligente du contexte, avec un système de scoring adaptatif, une consolidation des données et la création de blocs thématiques dynamiques.
- 🤖 **Orchestration SDLC Multi-Agents** : Des agents spécialisés isolés (`sdlc`, `dev_branch`, `test_branch`, `sdlc-orchestrator`) qui travaillent de concert pour valider les besoins, implémenter le code et générer des tests.
- 📊 **Observabilité et Diagnostics** : Évaluation en temps réel de la capacité de mémoire et de la saturation du système, sans impacter les performances de vos développements.
- ⚙️ **Routage Adaptatif** : Des plans d'élagage et de routage clairs garantissant que l'IA dispose toujours des éléments les plus pertinents pour accomplir sa tâche.

---

## 🛠️ Installation et Lancement (Depuis les sources)

Pour exécuter memoriX depuis son code source (recommandé pour ce dépôt) :

### Prérequis
- [Bun](https://bun.sh/) v1.3+ (Gestionnaire de paquets et runtime)
- [Python](https://www.python.org/) 3.10+ (Pour le backend mémoire Titan)
- Environnement PowerShell (recommandé sur Windows)

### 1. Cloner le dépôt

```bash
git clone https://github.com/anomalyco/opencode.git memorix
cd memorix
```

### 2. Installer les dépendances

Le projet utilise **Bun** pour gérer efficacement l'architecture monorepo :

```bash
bun install
```

### 3. Lancer l'application memoriX

Le projet dispose d'un lanceur PowerShell dédié qui initialise le runtime Python, démarre le serveur MCP et lance l'environnement memoriX avec sa configuration complète prête à l'emploi :

```powershell
.\scripts\start_opencode_with_memorix.ps1
```

*(Note : ce script effectue automatiquement les validations de sécurité sur l'environnement pour garantir que la mémoire est bien séparée de votre code source).*

---

## 🚀 Utilisation Rapide (Versions pré-compilées)

Si vous souhaitez utiliser memoriX globalement sur votre système, sans passer par les sources :

```bash
# Installation YOLO (Linux / macOS)
curl -fsSL https://memorix.ai/install | bash

# Via les gestionnaires de paquets
npm i -g memorix@latest        # ou bun / pnpm / yarn
brew install memorix           # macOS (Homebrew)
scoop install memorix          # Windows (Scoop)
```

> [!TIP]
> Si vous utilisiez d'anciennes versions de l'outil, veillez à les désinstaller avant d'installer memoriX pour éviter tout conflit.

---

## 🏗️ Architecture de la Mémoire

Le cœur de memoriX repose sur une séparation claire entre l'interface utilisateur et son système de mémoire externe. 

L'intégration de la mémoire comprend :
- **Hot-Site (Court Terme)** : Pour le contexte immédiat de session.
- **Cold-Site (Long Terme)** : Consolidation, archivage et routage adaptatif (via MCP).
- **Politiques de Mémoire** : Scoring de rétention déterministe pour gérer les millions d'éléments actifs sans surcharger le contexte du LLM.

Pour plus d'informations techniques, consultez les dossiers :
- [Architecture Finale](docs/MEMORIX_FINAL_ARCHITECTURE.md)
- [Opérations](docs/MEMORIX_OPERATIONS.md)

---

## 🤝 Contribuer

Les contributions sont les bienvenues ! Veuillez consulter notre [Guide de Contribution](./CONTRIBUTING.md) pour prendre connaissance des bonnes pratiques avant de soumettre une Pull Request.

**Rejoignez la communauté :** 
[Discord](https://discord.gg/memorix) | [X.com / Twitter](https://x.com/memorix)
