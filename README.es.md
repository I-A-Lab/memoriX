<h1 align="center">Memory AGENTX</h1>

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

## ¿Qué es MemoriX?

**MemoriX** es un sistema avanzado de memoria persistente diseñado específicamente para agentes de codificación autónomos basados en modelos de lenguaje grandes (LLM), como OpenCode.

**MemoriX transforma la memoria del agente de un simple desafío de almacenamiento a un problema estructurado de gobernanza del conocimiento.** Proporciona un control de admisión explícito, olvido lógico, aislamiento estricto de proyectos y un comportamiento de saturación segura.

---

## Arquitectura del Sistema

MemoriX se inspira en la estructura de la memoria humana. Aplica un ciclo de vida estricto: **observar → proponer → validar → recuperar → actualizar → olvidar**.

1. **Memoria a Corto Plazo (STM)**: Registro transitorio de interacciones recientes.
2. **Sitio Frío (Archivo Histórico)**: Archivo de solo adición para auditoría.
3. **Archivo de Proyecto**: Instantáneas estructuradas e hitos del proyecto.
4. **Almacén de Candidatos (Candidate Store)**: Área de espera para la validación de conocimientos propuestos.
5. **Sitio Caliente de Titan (Memoria Activa)**: La única memoria activa consultada durante la recuperación. Solo ingresan memorias validadas.

---

## Benchmarks y Rendimiento

Evaluado rigurosamente mediante un benchmark A/B (2,048 ejecuciones en 32 familias de tareas):
- **+28.0% Tasa de Éxito**: Mejora general del 31.9% al 60.0%.
- **Aislamiento Perfecto**: Cero fugas de información.
- **Elasticidad de Capacidad**: Comportamiento de saturación segura probado hasta 6,000,000 de elementos.
- **Latencia**: Sobrecarga mínima (+120 ms).

---

## Guía de Instalación Completa (De la A a la Z)

Esta guía te ayudará a instalar MemoriX y OpenCode desde cero. Está diseñada para ser accesible incluso si eres nuevo en estas herramientas.

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
git clone https://github.com/anomalyco/memoriX.git
cd memoriX
```

### Paso 3: Instalar Dependencias JavaScript

Usa Bun para instalar los paquetes necesarios:

```powershell
bun install
```

### Paso 4: Verificar el Entorno Python

Verifica que Python esté correctamente configurado con el script de validación:

```powershell
.\tools\memorix\runtime\start_opencode_with_memorix.ps1 -ValidateOnly
```
Deberías ver `MemoriXGateway import OK`.

### Paso 5: ¡Iniciar el Sistema!

Una vez que la validación sea exitosa, inicia la interfaz de OpenCode:

```powershell
.\tools\memorix\runtime\start_opencode_with_memorix.ps1
```
¡Ahora estás listo para programar con un agente que *realmente recuerda*!

---

## Documentación Adicional
- [Arquitectura Detallada](docs/MEMORIX_FINAL_ARCHITECTURE.md)
- [Manual de Operaciones](docs/MEMORIX_OPERATIONS.md)
