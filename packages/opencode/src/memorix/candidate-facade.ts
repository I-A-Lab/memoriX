import type { MemoriXService } from "./service"
import type {
  JSONObject,
  MemoriXCandidate,
  MemoriXCandidateStatus,
  MemoriXStatus,
} from "./types"

export type CandidateFacadeService = Pick<
  MemoriXService,
  | "listCandidates"
  | "validateCandidate"
  | "forgetMemory"
  | "rejectCandidate"
  | "runConsolidation"
  | "runNightly"
  | "status"
>

export type CandidateFacadeFailure = {
  code: string
  message: string
}

export type CandidateFacadeMetadata = {
  operation:
    | "list_candidates"
    | "validate_candidate"
    | "forget_memory"
    | "reject_candidate"
    | "run_consolidation"
    | "run_nightly"
    | "status"
  ok: boolean
  candidateCount?: number
  candidate?: MemoriXCandidate
  candidates?: MemoriXCandidate[]
  status?: MemoriXStatus
  report?: JSONObject
  failure?: CandidateFacadeFailure
}

export type CandidateFacadeResult = {
  title: string
  output: string
  metadata: CandidateFacadeMetadata
}

function failureResult(
  operation: CandidateFacadeMetadata["operation"],
  title: string,
  failure: { code: string; message: string },
): CandidateFacadeResult {
  return {
    title,
    output: `memoriX operation unavailable: ${failure.message}`,
    metadata: {
      operation,
      ok: false,
      failure: {
        code: failure.code,
        message: failure.message,
      },
    },
  }
}

function candidateLine(
  candidate: MemoriXCandidate,
): string {
  return [
    `ID: ${candidate.candidate_id}`,
    `Status: ${candidate.status}`,
    `Content: ${candidate.content}`,
    `Reason: ${candidate.reason}`,
    `Importance: ${candidate.importance}`,
    `Confidence: ${candidate.confidence}`,
    `Surprise: ${candidate.surprise}`,
    `Created: ${candidate.created_at}`,
  ].join("\n")
}

export async function listCandidatesThroughMemoriX(
  service: CandidateFacadeService,
  status?: MemoriXCandidateStatus,
): Promise<CandidateFacadeResult> {
  const result = await service.listCandidates(status)

  if (!result.ok) {
    return failureResult(
      "list_candidates",
      "memoriX candidates unavailable",
      result,
    )
  }

  const candidates = result.value
  const output =
    candidates.length === 0
      ? "No matching memoriX candidates were found."
      : candidates.map(candidateLine).join("\n\n---\n\n")

  return {
    title: `memoriX candidates: ${candidates.length}`,
    output,
    metadata: {
      operation: "list_candidates",
      ok: true,
      candidateCount: candidates.length,
      candidates,
    },
  }
}

export async function validateCandidateThroughMemoriX(
  service: CandidateFacadeService,
  input: {
    candidateID: string
    validatedBy: string
    validationReason: string
    finalContent?: string
    supersedesMemoryID?: string | null
  },
): Promise<CandidateFacadeResult> {
  const result = await service.validateCandidate({
    ...input,
    ...(input.supersedesMemoryID !== undefined
      ? { supersedesMemoryID: input.supersedesMemoryID }
      : {}),
  })

  if (!result.ok) {
    return failureResult(
      "validate_candidate",
      "memoriX candidate validation failed",
      result,
    )
  }

  return {
    title: "memoriX candidate validated",
    output: JSON.stringify(result.value, null, 2),
    metadata: {
      operation: "validate_candidate",
      ok: true,
      report: result.value,
    },
  }
}

export async function rejectCandidateThroughMemoriX(
  service: CandidateFacadeService,
  input: {
    candidateID: string
    rejectedBy: string
    rejectionReason: string
  },
): Promise<CandidateFacadeResult> {
  const result = await service.rejectCandidate(input)

  if (!result.ok) {
    return failureResult(
      "reject_candidate",
      "memoriX candidate rejection failed",
      result,
    )
  }

  return {
    title: "memoriX candidate rejected",
    output: candidateLine(result.value),
    metadata: {
      operation: "reject_candidate",
      ok: true,
      candidate: result.value,
    },
  }
}

export async function forgetMemoryThroughMemoriX(
  service: CandidateFacadeService,
  input: {
    memoryId: string
    validatedBy: string
    reason: string
  },
): Promise<CandidateFacadeResult> {
  const result = await service.forgetMemory(input)
  if (!result.ok) {
    return failureResult(
      "forget_memory",
      "memoriX memory soft-forget failed",
      result,
    )
  }
  return {
    title: "memoriX memory soft-forgotten",
    output: JSON.stringify(result.value, null, 2),
    metadata: {
      operation: "forget_memory",
      ok: true,
      report: result.value,
    },
  }
}

export async function runConsolidationThroughMemoriX(
  service: CandidateFacadeService,
  mode = "manual",
): Promise<CandidateFacadeResult> {
  const result = await service.runConsolidation(mode)

  if (!result.ok) {
    return failureResult(
      "run_consolidation",
      "memoriX consolidation failed",
      result,
    )
  }

  return {
    title: "memoriX consolidation completed",
    output: JSON.stringify(result.value, null, 2),
    metadata: {
      operation: "run_consolidation",
      ok: true,
      report: result.value,
    },
  }
}

export async function runNightlyThroughMemoriX(
  service: CandidateFacadeService,
  clearShortTermAfterSuccess = true,
): Promise<CandidateFacadeResult> {
  const result = await service.runNightly(
    clearShortTermAfterSuccess,
  )

  if (!result.ok) {
    return failureResult(
      "run_nightly",
      "memoriX nightly consolidation failed",
      result,
    )
  }

  return {
    title: "memoriX nightly consolidation completed",
    output: JSON.stringify(result.value, null, 2),
    metadata: {
      operation: "run_nightly",
      ok: true,
      report: result.value,
    },
  }
}

export async function getMemoriXStatus(
  service: CandidateFacadeService,
): Promise<CandidateFacadeResult> {
  const result = await service.status()

  if (!result.ok) {
    return failureResult(
      "status",
      "memoriX status unavailable",
      result,
    )
  }

  return {
    title: "memoriX status",
    output: JSON.stringify(result.value, null, 2),
    metadata: {
      operation: "status",
      ok: true,
      status: result.value,
    },
  }
}
