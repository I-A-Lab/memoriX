import { Effect, Schema } from "effect"
import { getDefaultMemoriXService, runObservability, type JSONObject } from "../memorix"
import * as Tool from "./tool"
const Action = Schema.Union([
  Schema.Literal("audit"), Schema.Literal("collect"), Schema.Literal("report"), Schema.Literal("inspect"),
  Schema.Literal("snapshot"), Schema.Literal("snapshots"), Schema.Literal("compare"), Schema.Literal("drift"),
  Schema.Literal("alerts"), Schema.Literal("acknowledge"),
])
const Parameters = Schema.Struct({ action: Action, snapshot_id: Schema.optional(Schema.String), baseline_snapshot_id: Schema.optional(Schema.String), current_snapshot_id: Schema.optional(Schema.String), alert_id: Schema.optional(Schema.String), actor: Schema.optional(Schema.String), reason: Schema.optional(Schema.String), limit: Schema.optional(Schema.Number), threshold: Schema.optional(Schema.Number), assessment_limit: Schema.optional(Schema.Number) })
export const ObservabilityTool = Tool.define<typeof Parameters, { operation: string; ok: boolean }, never>("observability", Effect.succeed({ description: "Inspect and persist memoriX observability diagnostics.", parameters: Parameters, execute: (params, ctx) => Effect.promise(async () => { if (["snapshot","acknowledge"].includes(params.action)) await ctx.ask({ permission: "observability", patterns: [params.action], always: [params.action], metadata: {} }); return runObservability(getDefaultMemoriXService(), params as unknown as JSONObject) }) }))
