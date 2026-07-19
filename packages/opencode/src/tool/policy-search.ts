import { Effect, Schema } from "effect"
import { getDefaultMemoriXService, getPolicySearch, type JSONObject, type PolicySearchFacadeResult } from "../memorix"
import * as Tool from "./tool"
const Parameters = Schema.Struct({ max_trials: Schema.optional(Schema.Number), seed: Schema.optional(Schema.Number), assessment_limit: Schema.optional(Schema.Number), simulate_memory_count: Schema.optional(Schema.Number), runtime_only: Schema.optional(Schema.Boolean), observed_at: Schema.optional(Schema.String) })
type Metadata = PolicySearchFacadeResult["metadata"]
export const PolicySearchTool = Tool.define<typeof Parameters, Metadata, never>("policy_search", Effect.succeed({ description: "Run bounded read-only memoriX memory-policy search.", parameters: Parameters, execute: (params, _ctx) => Effect.promise(() => getPolicySearch(getDefaultMemoriXService(), params as unknown as JSONObject)) } satisfies Tool.DefWithoutID<typeof Parameters, Metadata>))
