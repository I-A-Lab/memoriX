import { Effect, Schema } from "effect"
import {
  getDefaultMemoriXService,
  getRetentionRankingStatus,
  inspectRetentionRanking,
  type RetentionRankingFacadeResult,
} from "../memorix"
import * as Tool from "./tool"

const Status = Schema.Struct({
  simulate_count: Schema.optional(Schema.Number),
  assessment_limit: Schema.optional(Schema.Number),
})
const Inspect = Schema.Struct({ memory_id: Schema.String })
type Metadata = RetentionRankingFacadeResult["metadata"]

export const RetentionRankingStatusTool = Tool.define<
  typeof Status,
  Metadata,
  never
>(
  "retention_ranking_status",
  Effect.succeed({
    description:
      "Rank persisted memoriX hot-site memories by adaptive retention score in dry-run mode.",
    parameters: Status,
    execute: (
      params: Schema.Schema.Type<typeof Status>,
      _ctx: Tool.Context<Metadata>,
    ) =>
      Effect.promise(() =>
        getRetentionRankingStatus(
          getDefaultMemoriXService(),
          params.simulate_count,
          params.assessment_limit ?? 100,
        ),
      ),
  } satisfies Tool.DefWithoutID<typeof Status, Metadata>),
)

export const RetentionRankingInspectTool = Tool.define<
  typeof Inspect,
  Metadata,
  never
>(
  "retention_ranking_inspect",
  Effect.succeed({
    description:
      "Inspect one persisted memoriX adaptive-retention assessment by ID.",
    parameters: Inspect,
    execute: (
      params: Schema.Schema.Type<typeof Inspect>,
      _ctx: Tool.Context<Metadata>,
    ) =>
      Effect.promise(() =>
        inspectRetentionRanking(
          getDefaultMemoriXService(),
          params.memory_id,
        ),
      ),
  } satisfies Tool.DefWithoutID<typeof Inspect, Metadata>),
)
