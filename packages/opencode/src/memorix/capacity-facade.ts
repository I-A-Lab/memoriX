import type { MemoriXService } from "./service"
import type { JSONObject } from "./types"

export type CapacityFacadeService = Pick<MemoriXService, "capacityStatus" | "capacityPlan" | "capacityPrune">
export type CapacityFacadeResult = { title: string; output: string; metadata: { operation: string; ok: boolean; report?: JSONObject; failure?: { code: string; message: string } } }
function result(operation: string, title: string, value: Awaited<ReturnType<MemoriXService["capacityStatus"]>>): CapacityFacadeResult {
  if (!value.ok) return { title, output: `memoriX operation unavailable: ${value.message}`, metadata: { operation, ok: false, failure: { code: value.code, message: value.message } } }
  return { title, output: JSON.stringify(value.value, null, 2), metadata: { operation, ok: true, report: value.value } }
}
export async function getCapacityStatus(service: CapacityFacadeService, simulateActiveItems?: number) { return result("capacity_status", "memoriX capacity status", await service.capacityStatus(simulateActiveItems)) }
export async function planCapacityPruning(service: CapacityFacadeService) { return result("capacity_plan", "memoriX capacity pruning plan", await service.capacityPlan()) }
export async function pruneCapacity(service: CapacityFacadeService, input: { appliedBy: string; reason: string; maxDeactivations?: number }) { return result("capacity_prune", "memoriX capacity pruning applied", await service.capacityPrune(input)) }
