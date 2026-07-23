
import { Effect, Schema } from "effect"
import { getDefaultMemoriXService, runPolicyLifecycle, type JSONObject, type PolicyLifecycleFacadeResult } from "../memorix"
import * as Tool from "./tool"
const PolicyLifecycleActionSchema = Schema.Union([
  Schema.Literal("inspect"),
  Schema.Literal("propose"),
  Schema.Literal("approve"),
  Schema.Literal("reject"),
  Schema.Literal("activation_plan"),
  Schema.Literal("activate"),
  Schema.Literal("rollback_plan"),
  Schema.Literal("rollback"),
])

const Parameters = Schema.Struct({
  action: PolicyLifecycleActionSchema,
  version_id: Schema.optional(Schema.String),
  actor: Schema.optional(Schema.String),
  reason: Schema.optional(Schema.String),
  validation_id: Schema.optional(Schema.String),
  max_trials: Schema.optional(Schema.Number),
  seed: Schema.optional(Schema.Number),
})
type Metadata = PolicyLifecycleFacadeResult["metadata"]
export const PolicyLifecycleTool = Tool.define<typeof Parameters, Metadata, never>("policy_lifecycle", Effect.succeed({ description: "Inspect or explicitly change the versioned memoriX policy registry.", parameters: Parameters, execute: (params, ctx) => Effect.promise(async () => { if (["propose","approve","reject","activate","rollback"].includes(params.action)) await ctx.ask({ permission: "policy_lifecycle", patterns: [params.action], always: [params.action], metadata: {} }); return runPolicyLifecycle(getDefaultMemoriXService(), params as unknown as JSONObject) }) } satisfies Tool.DefWithoutID<typeof Parameters, Metadata>))
