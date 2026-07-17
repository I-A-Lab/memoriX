import { Effect, Schema } from "effect"
import {
  getCapacityStatus,
  getDefaultMemoriXService,
  planCapacityPruning,
  pruneCapacity,
  type CapacityFacadeResult,
} from "../memorix"
import * as Tool from "./tool"

export const CapacityStatusParameters = Schema.Struct({
  simulate_active_items: Schema.optional(
    Schema.Number.annotate({
      description:
        "Optional simulated number of active hot-site memories. No objects are allocated.",
    }),
  ),
})

export const CapacityPlanParameters = Schema.Struct({})

export const CapacityPruneParameters = Schema.Struct({
  applied_by: Schema.String.annotate({
    description:
      "Identity of the human operator approving the soft pruning.",
  }),
  reason: Schema.String.annotate({
    description:
      "Explicit reason for applying the approved pruning plan.",
  }),
  max_deactivations: Schema.optional(
    Schema.Number.annotate({
      description:
        "Optional maximum number of hot-site memories to deactivate.",
    }),
  ),
})

type CapacityToolMetadata =
  CapacityFacadeResult["metadata"]

export const MemoryCapacityStatusTool = Tool.define<
  typeof CapacityStatusParameters,
  CapacityToolMetadata,
  never
>(
  "memory_capacity_status",
  Effect.succeed({
    description:
      "Inspect memoriX hot-site capacity without mutation.",
    parameters: CapacityStatusParameters,
    execute: (
      params: Schema.Schema.Type<
        typeof CapacityStatusParameters
      >,
      _ctx: Tool.Context<CapacityToolMetadata>,
    ) =>
      Effect.promise(() =>
        getCapacityStatus(
          getDefaultMemoriXService(),
          params.simulate_active_items,
        ),
      ),
  } satisfies Tool.DefWithoutID<
    typeof CapacityStatusParameters,
    CapacityToolMetadata
  >),
)

export const MemoryCapacityPlanTool = Tool.define<
  typeof CapacityPlanParameters,
  CapacityToolMetadata,
  never
>(
  "memory_capacity_plan",
  Effect.succeed({
    description:
      "Build a dry-run memoriX soft-pruning plan without applying changes.",
    parameters: CapacityPlanParameters,
    execute: (
      _params: Schema.Schema.Type<
        typeof CapacityPlanParameters
      >,
      _ctx: Tool.Context<CapacityToolMetadata>,
    ) =>
      Effect.promise(() =>
        planCapacityPruning(
          getDefaultMemoriXService(),
        ),
      ),
  } satisfies Tool.DefWithoutID<
    typeof CapacityPlanParameters,
    CapacityToolMetadata
  >),
)

export const MemoryCapacityPruneTool = Tool.define<
  typeof CapacityPruneParameters,
  CapacityToolMetadata,
  never
>(
  "memory_capacity_prune",
  Effect.succeed({
    description:
      "Apply explicitly approved hot-site soft pruning without touching the cold site.",
    parameters: CapacityPruneParameters,
    execute: (
      params: Schema.Schema.Type<
        typeof CapacityPruneParameters
      >,
      ctx: Tool.Context<CapacityToolMetadata>,
    ) =>
      Effect.gen(function* () {
        yield* ctx.ask({
          permission: "memory_capacity_prune",
          patterns: [params.applied_by],
          always: [],
          metadata: {
            operation: "capacity_prune",
            applied_by: params.applied_by,
            reason: params.reason,
            max_deactivations:
              params.max_deactivations,
          },
        })

        return yield* Effect.promise(() =>
          pruneCapacity(
            getDefaultMemoriXService(),
            {
              appliedBy: params.applied_by,
              reason: params.reason,
              maxDeactivations:
                params.max_deactivations,
            },
          ),
        )
      }),
  } satisfies Tool.DefWithoutID<
    typeof CapacityPruneParameters,
    CapacityToolMetadata
  >),
)
