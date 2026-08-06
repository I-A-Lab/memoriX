export const MEMORIX_BENCHMARK_MODE_ENV = "MEMORIX_BENCHMARK_MODE"

export type MemoriXBenchmarkMode = "default" | "no_memory" | "memorix_core" | "memorix_full"

export function memoriXBenchmarkMode(environment: Record<string, string | undefined> = process.env): MemoriXBenchmarkMode {
  const value = environment[MEMORIX_BENCHMARK_MODE_ENV]?.trim().toLowerCase()
  if (value === "no_memory" || value === "memorix_core" || value === "memorix_full") return value
  return "default"
}

export function strictNoMemoryMode(environment: Record<string, string | undefined> = process.env): boolean {
  return memoriXBenchmarkMode(environment) === "no_memory"
}

export function memoriXToolsEnabled(environment: Record<string, string | undefined> = process.env): boolean {
  return !strictNoMemoryMode(environment)
}

export function promptForMemoriXMode(prompt: string, environment: Record<string, string | undefined> = process.env): string {
  if (!strictNoMemoryMode(environment)) return prompt
  return prompt.replace(/^MEMORIX[^\n]*\n(?:-.*\n)+(?:\n)?/gm, "").trim()
}
