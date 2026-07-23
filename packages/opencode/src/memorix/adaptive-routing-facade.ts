import type { MemoriXService } from "./service"
import type { JSONObject } from "./types"

export type AdaptiveRoutingFacadeService = Pick<MemoriXService, "adaptiveRoutingPlan">
export type AdaptiveRoutingFacadeResult = {
  title: string
  output: string
  metadata: { operation: string; ok: boolean; report?: JSONObject; failure?: { code: string; message: string } }
}

export async function getAdaptiveRoutingPlan(
  service: AdaptiveRoutingFacadeService,
  input: JSONObject,
): Promise<AdaptiveRoutingFacadeResult> {
  const value = await service.adaptiveRoutingPlan(input)
  if (!value.ok) return { title: "memoriX adaptive routing", output: value.message, metadata: { operation: "adaptive_routing_plan", ok: false, failure: { code: value.code, message: value.message } } }
  return { title: "memoriX adaptive routing", output: JSON.stringify(value.value, null, 2), metadata: { operation: "adaptive_routing_plan", ok: true, report: value.value } }
}
