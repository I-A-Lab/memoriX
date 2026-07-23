
import { Effect, Schema } from "effect"
import { getDefaultMemoriXService, runTopicBlocks, type JSONObject, type TopicBlocksFacadeResult } from "../memorix"
import * as Tool from "./tool"
const Action = Schema.Union([
  Schema.Literal("inspect"), Schema.Literal("detect"), Schema.Literal("plan"),
  Schema.Literal("create"), Schema.Literal("rename"), Schema.Literal("add_alias"),
  Schema.Literal("remove_alias"), Schema.Literal("archive"), Schema.Literal("restore"),
  Schema.Literal("route"), Schema.Literal("merge_plan"), Schema.Literal("merge"), Schema.Literal("rebalance_plan"),
])
const Parameters = Schema.Struct({
  action: Action, item_id: Schema.optional(Schema.String), content: Schema.optional(Schema.String),
  topic: Schema.optional(Schema.String), block_id: Schema.optional(Schema.String),
  source_block_id: Schema.optional(Schema.String), target_block_id: Schema.optional(Schema.String),
  value: Schema.optional(Schema.String), actor: Schema.optional(Schema.String),
})
type Metadata = TopicBlocksFacadeResult["metadata"]
export const TopicBlocksTool = Tool.define<typeof Parameters, Metadata, never>("topic_blocks", Effect.succeed({
  description: "Inspect, plan, or explicitly manage dynamic memoriX topic blocks.", parameters: Parameters,
  execute: (params, ctx) => Effect.promise(async () => {
    if (["create","rename","add_alias","remove_alias","archive","restore","route","merge"].includes(params.action)) {
      await ctx.ask({ permission: "topic_blocks", patterns: [params.action], always: [params.action], metadata: {} })
    }
    return runTopicBlocks(getDefaultMemoriXService(), params as unknown as JSONObject)
  }),
} satisfies Tool.DefWithoutID<typeof Parameters, Metadata>))
