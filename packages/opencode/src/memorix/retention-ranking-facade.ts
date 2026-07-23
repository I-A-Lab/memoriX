import type { MemoriXService } from "./service"
import type { JSONObject } from "./types"

export type RetentionRankingFacadeService = Pick<
  MemoriXService,
  "retentionRankingStatus" | "retentionRankingInspect"
>

export type RetentionRankingFacadeResult = {
  title: string
  output: string
  metadata: {
    operation: string
    ok: boolean
    report?: JSONObject | null
    failure?: { code: string; message: string }
  }
}

function result(
  operation: string,
  title: string,
  value: Awaited<
    ReturnType<MemoriXService["retentionRankingInspect"]>
  >,
): RetentionRankingFacadeResult {
  if (!value.ok) {
    return {
      title,
      output: `memoriX operation unavailable: ${value.message}`,
      metadata: {
        operation,
        ok: false,
        failure: { code: value.code, message: value.message },
      },
    }
  }
  return {
    title,
    output: JSON.stringify(value.value, null, 2),
    metadata: { operation, ok: true, report: value.value },
  }
}

export async function getRetentionRankingStatus(
  service: RetentionRankingFacadeService,
  simulateCount?: number,
  assessmentLimit = 100,
): Promise<RetentionRankingFacadeResult> {
  return result(
    "retention_ranking_status",
    "memoriX adaptive retention ranking",
    await service.retentionRankingStatus(
      simulateCount,
      assessmentLimit,
    ),
  )
}

export async function inspectRetentionRanking(
  service: RetentionRankingFacadeService,
  memoryID: string,
): Promise<RetentionRankingFacadeResult> {
  return result(
    "retention_ranking_inspect",
    "memoriX adaptive retention assessment",
    await service.retentionRankingInspect(memoryID),
  )
}
