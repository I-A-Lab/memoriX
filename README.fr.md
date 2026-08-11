<h1 align="center">Memory AGENTX</h1>

<p align="center">
  <em>Conception et Évaluation d'un Système de Mémoire Persistante Contrôlée pour les Agents de Code Basés sur les LLM</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/langage-TypeScript-007ACC?style=flat-square" alt="TypeScript" />
  <img src="https://img.shields.io/badge/langage-Python-3776AB?style=flat-square" alt="Python" />
  <img src="https://img.shields.io/badge/runtime-Bun-000000?style=flat-square" alt="Bun" />
  <img src="https://img.shields.io/badge/shell-PowerShell-5391FE?style=flat-square" alt="PowerShell" />
</p>

<p align="center">
  <a href="README.md">English</a> •
  <a href="README.fr.md">Français</a> •
  <a href="README.es.md">Español</a> •
  <a href="README.zh.md">中文</a> •
  <a href="README.ja.md">日本語</a>
</p>

---

## Qu'est-ce que MemoriX ?

**MemoriX** est un système de mémoire persistante avancé, conçu spécifiquement pour les agents de codage autonomes basés sur les grands modèles de langage (LLM), tels qu'OpenCode.

Alors que les agents IA assistent de plus en plus dans les tâches complexes de développement logiciel, leur continuité entre les sessions reste fragile. Lorsqu'une session se termine, tout le contexte (décisions, contraintes, conventions) s'évapore généralement. Les solutions existantes comme les bases de données vectorielles (RAG) échouent à fournir une mémoire à long terme contrôlée, auditable et interrogeable sans provoquer une surcharge du contexte.

**MemoriX transforme la mémoire de l'agent d'un simple défi de stockage en un problème structuré de gouvernance des connaissances.** Il offre un contrôle d'admission explicite, un oubli logique, une isolation stricte des projets, et un comportement de saturation sécurisé.

---

## Architecture du Système

MemoriX s'inspire de la structure à plusieurs niveaux de la mémoire humaine et impose un cycle de vie strict : **observer → proposer → valider → récupérer → mettre à jour → oublier**.

### 1. Mémoire à Court Terme (STM)
Un journal transitoire des interactions récentes. Le STM sert de tampon éphémère ; il n'est **pas** interrogé lors d'une recherche standard de mémoire.

### 2. Cold Site (Archive Historique)
Une archive durable en ajout seul (`events_archive.jsonl`) qui stocke tous les événements pour la traçabilité. Il préserve l'historique brut mais est strictement mis en quarantaine du raisonnement actif.

### 3. Archive de Projet
Une branche spécialisée du Cold Site qui stocke les jalons structurés du projet et les instantanés (snapshots) de versions.

### 4. Candidate Store (La Frontière de Validation)
L'automatisation peut sélectionner et proposer des informations, mais l'admission dans la mémoire active nécessite une **validation explicite**. Le Candidate Store agit comme une zone d'attente pour les connaissances proposées (état `PENDING`).

### 5. Titan Hot Site (Mémoire Active)
Le seul système de mémoire active interrogé par l'agent. Il s'appuie sur le backend neuronal Titan. Seules les mémoires validées y entrent. Il gère la déduplication, l'oubli logique et regroupe les mémoires en blocs thématiques.

---

## Tech Stack & Intégration

MemoriX maintient une frontière d'exécution nette en utilisant le **Model Context Protocol (MCP)** via JSON-RPC sur `stdio`.

- **Couche d'Orchestration (TypeScript / Bun)** : Gère le cycle de vie de l'agent (SDLC) et communique avec le sous-système de mémoire via MCP.
- **Sous-système de Mémoire (Python 3.10+)** : Gère le backend Titan, les pipelines de consolidation et le stockage.

Le système prend en charge nativement un **flux de travail SDLC Multi-Agents** :
- `sdlc` : Architecte/Orchestrateur (planification, délégation).
- `dev_branch` : Implémentation.
- `test_branch` : Tests indépendants et validation.

---

## Benchmarks & Performances Clés

Évalué rigoureusement via un benchmark A/B (2 048 exécutions sur 32 familles de tâches) :
- **+28.0% de Taux de Réussite** : Le taux de réussite est passé de 31,9 % (sans mémoire) à 60,0 % (avec MemoriX).
- **Isolation Parfaite** : Zéro fuite d'informations entre différents projets ou utilisateurs.
- **Élasticité de Capacité** : Comportement de saturation sécurisé testé jusqu'à 6 000 000 d'éléments. Le système rejette élégamment le surplus au lieu d'écraser les mémoires existantes une fois la limite (50 000) atteinte.
- **Latence** : Surcharge négligeable (+120 ms de latence de récupération médiane).

---

## Guide d'Installation Complet (De A à Z)

Ce guide vous accompagnera pour installer MemoriX et OpenCode de zéro. Il est conçu pour être accessible même si vous êtes totalement novice avec ces outils.

### Étape 1 : Prérequis

Assurez-vous d'avoir installé les éléments suivants sur votre machine :

1. **Git** : Utilisé pour télécharger le code source.
   - Télécharger & Installer : [git-scm.com](https://git-scm.com/)
2. **Node.js & Bun** : Bun est un environnement d'exécution JavaScript ultra-rapide utilisé pour lancer OpenCode.
   - Télécharger Node.js : [nodejs.org](https://nodejs.org/)
   - Installer Bun : Ouvrez votre terminal (PowerShell) et exécutez :
     ```powershell
     powershell -c "irm bun.sh/install.ps1 | iex"
     ```
3. **Python 3.10 ou supérieur** : Requis pour le backend de mémoire Titan.
   - Télécharger & Installer : [python.org](https://www.python.org/downloads/)
   - **Important** : Lors de l'installation de Python, assurez-vous de cocher la case **"Add Python to PATH"**.

### Étape 2 : Cloner le Dépôt

Ouvrez votre terminal (PowerShell recommandé) et téléchargez le code source de MemoriX :

```powershell
# Naviguez vers le dossier de votre choix
cd C:\Votre\Dossier\Prefere

# Cloner le dépôt
git clone https://github.com/anomalyco/memoriX.git

# Entrer dans le répertoire
cd memoriX
```

### Étape 3 : Installer les Dépendances JavaScript

Utilisez Bun pour installer tous les paquets nécessaires :

```powershell
bun install
```
*(Cela peut prendre quelques instants selon votre connexion.)*

### Étape 4 : Vérifier l'Environnement Python

Le système nécessite Python 3. Pour vérifier que tout est bien configuré, MemoriX inclut un script de pré-validation :

```powershell
.\tools\memorix\runtime\start_opencode_with_memorix.ps1 -ValidateOnly
```
**Résultat attendu :**
Vous devriez voir un message indiquant `MemoriXGateway import OK`. Si vous voyez une erreur concernant Python, assurez-vous qu'il est bien installé et ajouté à votre PATH.

### Étape 5 : Lancer le Système !

Une fois la validation réussie, lancez l'interface OpenCode avec la mémoire MemoriX activée :

```powershell
.\tools\memorix\runtime\start_opencode_with_memorix.ps1
```
Ce script lance le serveur MCP en arrière-plan et démarre l'interface OpenCode. Vous êtes maintenant prêt à coder avec un agent qui *se souvient vraiment*.

---

## Opérations Avancées

MemoriX inclut plusieurs outils avancés de maintenance, situés dans `tools/memorix/operations` :

- **Consolidation Nocturne** : `run_memorix_nightly.ps1` exécute la consolidation en arrière-plan.
- **Commande Globale** : `install_memorix_opencode_command.ps1` enregistre MemoriX globalement sur votre système.
- **Sauvegarde & Restauration** : `memorix_runtime_backup.py` permet de sauvegarder la mémoire de votre agent en toute sécurité.

---

## Documentation Supplémentaire
- [Architecture Détaillée](docs/MEMORIX_FINAL_ARCHITECTURE.md)
- [Manuel des Opérations](docs/MEMORIX_OPERATIONS.md)
