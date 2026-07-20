import type { MemoriXService } from "./service"
import type { JSONObject } from "./types"
export type ObservabilityFacadeService = Pick<MemoriXService, "observability">
export async function runObservability(service: ObservabilityFacadeService, input: JSONObject) {
  const value = await service.observability(input)
  if (!value.ok) return { title: "memoriX observability", output: value.message, metadata: { operation: "observability", ok: false, failure: { code: value.code, message: value.message } } }
  return { title: "memoriX observability", output: JSON.stringify(value.value, null, 2), metadata: { operation: "observability", ok: true, report: value.value } }
}
