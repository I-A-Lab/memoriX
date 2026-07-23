import { Effect, Schema } from "effect"
import { getAdaptiveRoutingPlan, getDefaultMemoriXService, type AdaptiveRoutingFacadeResult, type JSONObject } from "../memorix"
import * as Tool from "./tool"

const Parameters = Schema.Struct({
  target_id: Schema.String,
  retention_score: Schema.optional(Schema.Number),
  importance: Schema.optional(Schema.Number),
  confidence: Schema.optional(Schema.Number),
  surprise: Schema.optional(Schema.Number),
  protected: Schema.optional(Schema.Boolean),
  pinned: Schema.optional(Schema.Boolean),
  human_validated: Schema.optional(Schema.Boolean),
  required_slots: Schema.optional(Schema.Number),
  configured_capacity: Schema.optional(Schema.Number),
  assessment_limit: Schema.optional(Schema.Number),
  simulate_memory_count: Schema.optional(Schema.Number),
})
type Metadata = AdaptiveRoutingFacadeResult["metadata"]

export const AdaptiveRoutingPlanTool = Tool.define<typeof Parameters, Metadata, never>(
  "adaptive_routing_plan",
  Effect.succeed({
    description: "Build a read-only adaptive-routing plan for one memoriX candidate.",
    parameters: Parameters,
    execute: (params, _ctx) => Effect.promise(() => getAdaptiveRoutingPlan(getDefaultMemoriXService(), params as unknown as JSONObject)),
  } satisfies Tool.DefWithoutID<typeof Parameters, Metadata>),
)
