import type { MemoriXService } from "./service"
import type { JSONObject } from "./types"

export type MemoryPressureFacadeService = Pick<
  MemoriXService,
  "memoryPressureStatus" | "memoryPressureInspect"
>

export type MemoryPressureFacadeResult = {
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
  value: Awaited<ReturnType<MemoriXService["memoryPressureInspect"]>>,
): MemoryPressureFacadeResult {
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

export async function getMemoryPressureStatus(
  service: MemoryPressureFacadeService,
  simulateCount?: number,
  assessmentLimit = 100,
): Promise<MemoryPressureFacadeResult> {
  return result(
    "memory_pressure_status",
    "memoriX memory pressure status",
    await service.memoryPressureStatus(simulateCount, assessmentLimit),
  )
}

export async function inspectMemoryPressure(
  service: MemoryPressureFacadeService,
  memoryID: string,
): Promise<MemoryPressureFacadeResult> {
  return result(
    "memory_pressure_inspect",
    "memoriX memory pressure assessment",
    await service.memoryPressureInspect(memoryID),
  )
}
