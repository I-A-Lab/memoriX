import { describe, expect, test } from "bun:test"
import { analyzeTestOutput } from "../../src/session/break-log"

describe("BreakLog forensic analysis", () => {
  test("returns success report when exitCode is 0", () => {
    const report = analyzeTestOutput("All 5 tests passed", "", 0, 1, 5)
    expect(report.passed).toBe(true)
    expect(report.canRetry).toBe(false)
    expect(report.failedTests).toHaveLength(0)
    expect(report.formattedFeedback).toContain("SUCCÈS")
  })

  test("identifies failed tests and permits retry when under maxAttempts", () => {
    const stdout = "FAIL test/example.test.ts\n× should calculate correctly\nAssertionError: expected 1 to be 2"
    const report = analyzeTestOutput(stdout, "", 1, 2, 5)
    expect(report.passed).toBe(false)
    expect(report.canRetry).toBe(true)
    expect(report.exitCode).toBe(1)
    expect(report.failedTests.length).toBeGreaterThan(0)
    expect(report.formattedFeedback).toContain("Tentative 2/5")
    expect(report.formattedFeedback).toContain("Instruction d'auto-guérison")
  })

  test("disables retry when maxAttempts (5) ceiling is reached", () => {
    const stdout = "FAIL test/example.test.ts\nerror: fatal error"
    const report = analyzeTestOutput(stdout, "", 1, 5, 5)
    expect(report.passed).toBe(false)
    expect(report.canRetry).toBe(false)
    expect(report.formattedFeedback).toContain("Plafond de tentatives atteint (5/5)")
  })
})
