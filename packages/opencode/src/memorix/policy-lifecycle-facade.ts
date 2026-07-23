
import type { MemoriXService } from "./service"
import type { JSONObject } from "./types"
export type PolicyLifecycleFacadeService = Pick<MemoriXService, "policyLifecycle">
export type PolicyLifecycleFacadeResult = { title: string; output: string; metadata: { operation: string; ok: boolean; report?: JSONObject; failure?: { code: string; message: string } } }
export async function runPolicyLifecycle(service: PolicyLifecycleFacadeService, input: JSONObject): Promise<PolicyLifecycleFacadeResult> {
  const value = await service.policyLifecycle(input)
  if (!value.ok) return { title: "memoriX policy lifecycle", output: value.message, metadata: { operation: "policy_lifecycle", ok: false, failure: { code: value.code, message: value.message } } }
  return { title: "memoriX policy lifecycle", output: JSON.stringify(value.value, null, 2), metadata: { operation: "policy_lifecycle", ok: true, report: value.value } }
}
