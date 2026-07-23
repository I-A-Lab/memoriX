import type { MemoriXService } from "./service"
import type { JSONObject } from "./types"
export type PolicySearchFacadeService = Pick<MemoriXService, "policySearch">
export type PolicySearchFacadeResult = { title: string; output: string; metadata: { operation: string; ok: boolean; report?: JSONObject; failure?: { code: string; message: string } } }
export async function getPolicySearch(service: PolicySearchFacadeService, input: JSONObject): Promise<PolicySearchFacadeResult> {
  const value = await service.policySearch(input)
  if (!value.ok) return { title: "memoriX policy search", output: value.message, metadata: { operation: "policy_search", ok: false, failure: { code: value.code, message: value.message } } }
  return { title: "memoriX policy search", output: JSON.stringify(value.value, null, 2), metadata: { operation: "policy_search", ok: true, report: value.value } }
}
