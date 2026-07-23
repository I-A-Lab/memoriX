import type { MemoriXService } from "./service"
import type { JSONObject } from "./types"
export type ConsolidationFacadeService = Pick<MemoriXService, "consolidation">
export async function runConsolidation(service: ConsolidationFacadeService, input: JSONObject) {
  const value = await service.consolidation(input)
  if (!value.ok) return { title: "memoriX consolidation", output: value.message, metadata: { operation: "consolidation", ok: false, failure: { code: value.code, message: value.message } } }
  return { title: "memoriX consolidation", output: JSON.stringify(value.value, null, 2), metadata: { operation: "consolidation", ok: true, report: value.value } }
}
