<h1 align="center">Memory AGENTX (NeuralMemo) </h1>

<p align="center">
  <em>Diseño y Evaluación de un Sistema de Memoria Persistente Controlada para Agentes de Código basados en LLM</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/lenguaje-TypeScript-007ACC?style=flat-square" alt="TypeScript" />
  <img src="https://img.shields.io/badge/lenguaje-Python-3776AB?style=flat-square" alt="Python" />
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

## ¿Qué es NeuralMemo?

**NeuralMemo** es un sistema avanzado de memoria persistente diseñado específicamente para agentes de codificación autónomos basados en modelos de lenguaje grandes (LLM), como OpenCode.

**NeuralMemo transforma la memoria del agente de un simple desafío de almacenamiento a un problema estructurado de gobernanza del conocimiento.** Proporciona un control de admisión explícito, olvido lógico, aislamiento estricto de proyectos y un comportamiento de saturación segura.

---

## Arquitectura del Sistema

NeuralMemo se inspira en la estructura de la memoria humana. Aplica un ciclo de vida estricto: **observar → proponer → validar → recuperar → actualizar → olvidar**.

1. **Memoria a Corto Plazo (STM)**: Registro transitorio de interacciones recientes.
2. **Sitio Frío (Archivo Histórico)**: Archivo de solo adición para auditoría.
3. **Archivo de Proyecto**: Instantáneas estructuradas e hitos del proyecto.
4. **Almacén de Candidatos (Candidate Store)**: Área de espera para la validación de conocimientos propuestos.
5. **Sitio Caliente de Titan (Memoria Activa)**: La única memoria activa consultada durante la recuperación. Solo ingresan memorias validadas.

---

## Benchmarks y Rendimiento

NeuralMemo fue evaluado rigurosamente mediante un benchmark A/B (2,048 ejecuciones en 32 familias de tareas usando `qwen2.5:3b`).

### 1. Resultados Globales del Benchmark A/B

| Métrica | Sin Memoria | NeuralMemo | Δ |
| ------- | ----------- | ------- | - |
| **Tasa de Éxito Global** | 31.9% (327/1024) | 60.0% (614/1024) | **+28.0pp** |
| **Latencia Mediana** | 3,384 ms | 3,504 ms | +120 ms |
| **Familias Evaluadas** | 32 | 32 | — |
| **Familias Ganadas** (Δ > 0) | — | 12 | — |
| **Familias Perdidas** (Δ < 0) | — | 4 | — |

### 2. Flujo de Trabajo SDLC Multi-Agente

Evalúa el éxito de tareas a través de distintos roles de agentes, previniendo fugas de información.

| Métrica | Sin Memoria | NeuralMemo | Delta |
| ------- | ----------- | ------- | ----- |
| **Tasa de Éxito** | 25.0% | 37.5% | **+12.5pp** |
| **Uso de Info Prohibida** | 0.0% | 0.0% | **Aislamiento Perfecto** |
| **Llamadas a Herramientas**| 5,000 | 8,750 | — |
| **Respuesta Media** | N/A | 257.3 ms | — |

### 3. Recuperación BFCL (Evaluación Ciega)

Evaluación independiente del mecanismo de calidad de recuperación.

| Etapa | Resultado | Tasa |
| ----- | --------- | ---- |
| Baseline correcta | 0/125 | 0% |
| Corpus contiene la referencia | 125/125 | 100% |
| Recuperación contiene la ref. | 96/125 | **76.8%** |
| Respuesta final correcta | 96/125 | **76.8%** |

### 4. Comportamiento en Saturación de Capacidad

Prueba del sistema frente a cargas crecientes y sobrecarga extrema.

| Elementos Activos | Admisión Permitida | Nivel de Presión | Ratio de Uso | Latencia de Decisión |
| ----------------- | ------------------ | ---------------- | ------------ | -------------------- |
| 10,000 | ✅ | estable | 0.2 | 0.0013 ms |
| **50,000** | ❌ | **crítico** | **1.0** | **0.0009 ms** |
| 500,000 | ❌ | crítico | 10.0 | 0.0024 ms |
| 6,000,000 | ❌ | crítico | 120.0 | 0.0023 ms |

*Nota: NeuralMemo rechaza el exceso de forma elegante (❌) en lugar de sobrescribir memorias existentes una vez que se alcanza la capacidad de 50,000, manteniendo una latencia inferior al milisegundo.*

---

## Guía de Instalación Completa (De la A a la Z)

Esta guía te ayudará a instalar NeuralMemo y OpenCode desde cero. Está diseñada para ser accesible incluso si eres nuevo en estas herramientas.

### Paso 1: Requisitos Previos

1. **Git**: Para descargar el código.
   - [git-scm.com](https://git-scm.com/)
2. **Node.js & Bun**: Bun es el entorno de ejecución necesario para OpenCode.
   - Instalar Bun en PowerShell:
     ```powershell
     powershell -c "irm bun.sh/install.ps1 | iex"
     ```
3. **Python 3.10 o superior**: Requerido para el backend Titan.
   - [python.org](https://www.python.org/downloads/)
   - **Importante**: Marca la casilla **"Add Python to PATH"** durante la instalación.

### Paso 2: Clonar el Repositorio

Abre tu terminal (se recomienda PowerShell):

```powershell
cd C:\Tu\Carpeta\Preferida
git clone https://github.com/anomalyco/NeuralMemo.git
cd NeuralMemo
```

### Paso 3: Instalar Dependencias JavaScript

Usa Bun para instalar los paquetes necesarios:

```powershell
bun install
```

### Paso 4: Verificar el Entorno Python

Verifica que Python esté correctamente configurado con el script de validación:

```powershell
.\tools\NeuralMemo\runtime\start_opencode_with_NeuralMemo.ps1
```
Deberías ver `NeuralMemoGateway import OK`.

### Paso 5: ¡Iniciar el Sistema!

Una vez que la validación sea exitosa, inicia la interfaz de OpenCode:

```powershell
.\tools\NeuralMemo\runtime\start_opencode_with_NeuralMemo.ps1
```
¡Ahora estás listo para programar con un agente que *realmente recuerda*!

---

## Documentación Adicional
- [Arquitectura Detallada](docs/NeuralMemo_FINAL_ARCHITECTURE.md)
- [Manual de Operaciones](docs/NeuralMemo_OPERATIONS.md)
