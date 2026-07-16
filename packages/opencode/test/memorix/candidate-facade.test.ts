import { describe, expect, test } from "bun:test"

import {
  getMemoriXStatus,
  listCandidatesThroughMemoriX,
  rejectCandidateThroughMemoriX,
  runConsolidationThroughMemoriX,
  validateCandidateThroughMemoriX,
  type CandidateFacadeService,
  type MemoriXCandidate,
  type MemoriXStatus,
} from "../../src/memorix"

const pendingCandidate = {
  candidate_id: "candidate_test",
  content: "Validated retrieval uses the Titan hot site.",
  reason: "Durable architecture rule.",
  source_event_ids: ["event_test"],
  created_at: "2026-07-15T08:00:00+00:00",
  status: "pending",
  importance: 0.9,
  confidence: 0.95,
  surprise: 0.5,
  target_memory_id: null,
  metadata: {},
} as unknown as MemoriXCandidate

const rejectedCandidate = {
  ...pendingCandidate,
  status: "rejected",
} as unknown as MemoriXCandidate

const memoryStatus = {
  architecture: "memorix_hot_cold",
  retrieval_contract:
    "hot_site_only_no_cold_fallback",
  cold_site_contract:
    "explicit_audit_history_only",
  automatic_rehydration: false,
} as unknown as MemoriXStatus

function successfulService(): CandidateFacadeService {
  return {
    listCandidates: async () => ({
      ok: true,
      value: [pendingCandidate],
    }),

    validateCandidate: async () => ({
      ok: true,
      value: {
        memory_id: "memory_test",
        source_candidate_id: "candidate_test",
      },
    }),

    rejectCandidate: async () => ({
      ok: true,
      value: rejectedCandidate,
    }),

    runConsolidation: async () => ({
      ok: true,
      value: {
        mode: "manual",
        created_candidate_ids: ["candidate_test"],
      },
    }),

    runNightly: async () => ({

      ok: true,

      value: {

        status: "completed",

      },

    }),


    status: async () => ({
      ok: true,
      value: memoryStatus,
    }),
  }
}

describe("candidate memoriX facade", () => {
  test("lists pending candidates", async () => {
    const result = await listCandidatesThroughMemoriX(
      successfulService(),
      "pending",
    )

    expect(result.metadata.ok).toBe(true)
    expect(result.metadata.operation).toBe(
      "list_candidates",
    )
    expect(result.metadata.candidateCount).toBe(1)
    expect(result.output).toContain("candidate_test")
  })

  test("validates one candidate", async () => {
    const result = await validateCandidateThroughMemoriX(
      successfulService(),
      {
        candidateID: "candidate_test",
        validatedBy: "Elwen",
        validationReason: "Reviewed manually.",
      },
    )

    expect(result.metadata.ok).toBe(true)
    expect(result.metadata.operation).toBe(
      "validate_candidate",
    )
    expect(result.output).toContain("memory_test")
  })

  test("rejects one candidate", async () => {
    const result = await rejectCandidateThroughMemoriX(
      successfulService(),
      {
        candidateID: "candidate_test",
        rejectedBy: "Elwen",
        rejectionReason: "Not durable.",
      },
    )

    expect(result.metadata.ok).toBe(true)
    expect(result.metadata.operation).toBe(
      "reject_candidate",
    )
    expect(result.metadata.candidate?.status).toBe(
      "rejected",
    )
  })

  test("runs manual consolidation", async () => {
    const result = await runConsolidationThroughMemoriX(
      successfulService(),
      "manual",
    )

    expect(result.metadata.ok).toBe(true)
    expect(result.metadata.operation).toBe(
      "run_consolidation",
    )
    expect(result.output).toContain("manual")
  })

  test("returns memoriX status", async () => {
    const result = await getMemoriXStatus(
      successfulService(),
    )

    expect(result.metadata.ok).toBe(true)
    expect(result.metadata.operation).toBe("status")
    expect(result.output).toContain(
      "memorix_hot_cold",
    )
  })

  test("converts a service failure safely", async () => {
    const service: CandidateFacadeService = {
      ...successfulService(),
      listCandidates: async () => ({
        ok: false,
        code: "operation",
        message: "candidate store unavailable",
      }),
    }

    const result = await listCandidatesThroughMemoriX(
      service,
    )

    expect(result.metadata.ok).toBe(false)
    expect(result.metadata.failure?.code).toBe(
      "operation",
    )
    expect(result.output).toContain(
      "candidate store unavailable",
    )
  })
})
