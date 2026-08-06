import { describe, expect, test } from "bun:test"
import { memoriXBenchmarkMode, memoriXToolsEnabled, promptForMemoriXMode, strictNoMemoryMode } from "../../src/memorix"

describe("strict no-memory benchmark mode", () => {
  test("recognizes supported modes safely", () => {
    expect(memoriXBenchmarkMode({ MEMORIX_BENCHMARK_MODE: "no_memory" })).toBe("no_memory")
    expect(memoriXBenchmarkMode({ MEMORIX_BENCHMARK_MODE: "invalid" })).toBe("default")
  })

  test("disables memoriX tools only for the strict baseline", () => {
    expect(strictNoMemoryMode({ MEMORIX_BENCHMARK_MODE: "no_memory" })).toBe(true)
    expect(memoriXToolsEnabled({ MEMORIX_BENCHMARK_MODE: "no_memory" })).toBe(false)
    expect(memoriXToolsEnabled({ MEMORIX_BENCHMARK_MODE: "memorix_core" })).toBe(true)
  })

  test("removes memoriX prompt sections in no_memory mode", () => {
    const prompt = "HEADER\n\nMEMORIX READ-ONLY CONTEXT\n- call memory_retrieve\n- never store secrets\n\nNEXT SECTION\n- keep this"
    const result = promptForMemoriXMode(prompt, { MEMORIX_BENCHMARK_MODE: "no_memory" })
    expect(result).not.toContain("MEMORIX")
    expect(result).not.toContain("memory_retrieve")
    expect(result).toContain("NEXT SECTION")
  })
})
