import { Effect, Schema } from "effect"
import {
  forgetMemoryThroughMemoriX,
  getDefaultMemoriXService,
  getMemoriXStatus,
  listCandidatesThroughMemoriX,
  rejectCandidateThroughMemoriX,
  runConsolidationThroughMemoriX,
  runNightlyThroughMemoriX,
  validateCandidateThroughMemoriX,
  type CandidateFacadeMetadata,
} from "../memorix"
import * as Tool from "./tool"

export const CandidateStatusSchema = Schema.Union([
  Schema.Literal("pending"),
  Schema.Literal("validated"),
  Schema.Literal("rejected"),
])

export const CandidateListParameters = Schema.Struct({
  status: Schema.optional(
    CandidateStatusSchema.annotate({
      description:
        "Optional lifecycle status used to filter memoriX candidates.",
    }),
  ),
})

export const CandidateValidateParameters = Schema.Struct({
  candidate_id: Schema.String.annotate({
    description:
      "The exact identifier of the pending candidate to validate.",
  }),
  validated_by: Schema.String.annotate({
    description:
      "The human reviewer responsible for the validation.",
  }),
  validation_reason: Schema.String.annotate({
    description:
      "The explicit human reason for validating this candidate.",
  }),
  final_content: Schema.optional(
    Schema.String.annotate({
      description:
        "Optional reviewed content replacing the proposed candidate content.",
    }),
  ),
  supersedes_memory_id: Schema.optional(
    Schema.String.annotate({
      description:
        "Optional exact memory ID this validation supersedes. When provided, that memory is soft-deactivated after the replacement is stored.",
    }),
  ),
})

export const CandidateRejectParameters = Schema.Struct({
  candidate_id: Schema.String.annotate({
    description:
      "The exact identifier of the pending candidate to reject.",
  }),
  rejected_by: Schema.String.annotate({
    description:
      "The human reviewer responsible for the rejection.",
  }),
  rejection_reason: Schema.String.annotate({
    description:
      "The explicit human reason for rejecting this candidate.",
  }),
})

export const ConsolidationParameters = Schema.Struct({
  mode: Schema.optional(
    Schema.String.annotate({
      description:
        "Consolidation mode. Defaults to manual.",
    }),
  ),
})

export const NightlyParameters = Schema.Struct({
  clear_short_term_after_success: Schema.optional(
    Schema.Boolean.annotate({
      description:
        "Clear short-term events only after a successful nightly run. Defaults to true.",
    }),
  ),
})

export const MemoryStatusParameters = Schema.Struct({})

export const MemoryCandidatesListTool = Tool.define<
  typeof CandidateListParameters,
  CandidateFacadeMetadata,
  never
>(
  "memory_candidates_list",
  Effect.succeed({
    description:
      "List memoriX memory candidates. This operation is read-only and may filter candidates by pending, validated, or rejected status.",
    parameters: CandidateListParameters,
    execute: (
      params: Schema.Schema.Type<
        typeof CandidateListParameters
      >,
      _ctx: Tool.Context<CandidateFacadeMetadata>,
    ) =>
      Effect.promise(() =>
        listCandidatesThroughMemoriX(
          getDefaultMemoriXService(),
          params.status,
        ),
      ),
  } satisfies Tool.DefWithoutID<
    typeof CandidateListParameters,
    CandidateFacadeMetadata
  >),
)

export const MemoryCandidateValidateTool = Tool.define<
  typeof CandidateValidateParameters,
  CandidateFacadeMetadata,
  never
>(
  "memory_candidate_validate",
  Effect.succeed({
    description:
      "Validate one pending memoriX candidate after an explicit human review. Validation writes the reviewed memory to the Titan hot site only.",
    parameters: CandidateValidateParameters,
    execute: (
      params: Schema.Schema.Type<
        typeof CandidateValidateParameters
      >,
      ctx: Tool.Context<CandidateFacadeMetadata>,
    ) =>
      Effect.gen(function* () {
        yield* ctx.ask({
          permission: "memory_candidate_validate",
          patterns: [
            params.candidate_id,
            ...(params.supersedes_memory_id !== undefined
              ? [params.supersedes_memory_id]
              : []),
          ],
          always: [],
          metadata: {
            operation: "validate_candidate",
            candidate_id: params.candidate_id,
            validated_by: params.validated_by,
            validation_reason: params.validation_reason,
            final_content: params.final_content,
            ...(params.supersedes_memory_id !== undefined
              ? {
                  supersedes_memory_id:
                    params.supersedes_memory_id,
                }
              : {}),
          },
        })

        return yield* Effect.promise(() =>
          validateCandidateThroughMemoriX(
            getDefaultMemoriXService(),
            {
              candidateID: params.candidate_id,
              validatedBy: params.validated_by,
              validationReason:
                params.validation_reason,
              finalContent: params.final_content,
              ...(params.supersedes_memory_id !== undefined
                ? {
                    supersedesMemoryID:
                      params.supersedes_memory_id,
                  }
                : {}),
            },
          ),
        )
      }),
  } satisfies Tool.DefWithoutID<
    typeof CandidateValidateParameters,
    CandidateFacadeMetadata
  >),
)

export const MemoryCandidateRejectTool = Tool.define<
  typeof CandidateRejectParameters,
  CandidateFacadeMetadata,
  never
>(
  "memory_candidate_reject",
  Effect.succeed({
    description:
      "Reject one pending memoriX candidate after an explicit human review. Rejection never writes to the Titan hot site.",
    parameters: CandidateRejectParameters,
    execute: (
      params: Schema.Schema.Type<
        typeof CandidateRejectParameters
      >,
      ctx: Tool.Context<CandidateFacadeMetadata>,
    ) =>
      Effect.gen(function* () {
        yield* ctx.ask({
          permission: "memory_candidate_reject",
          patterns: [params.candidate_id],
          always: [],
          metadata: {
            operation: "reject_candidate",
            candidate_id: params.candidate_id,
            rejected_by: params.rejected_by,
            rejection_reason: params.rejection_reason,
          },
        })

        return yield* Effect.promise(() =>
          rejectCandidateThroughMemoriX(
            getDefaultMemoriXService(),
            {
              candidateID: params.candidate_id,
              rejectedBy: params.rejected_by,
              rejectionReason:
                params.rejection_reason,
            },
          ),
        )
      }),
  } satisfies Tool.DefWithoutID<
    typeof CandidateRejectParameters,
    CandidateFacadeMetadata
  >),
)

export const MemoryForgetParameters = Schema.Struct({
  memory_id: Schema.String.annotate({
    description:
      "The exact identifier of the validated memoriX memory to soft-forget.",
  }),
  validated_by: Schema.String.annotate({
    description:
      "The human operator requesting the soft-forget.",
  }),
  reason: Schema.String.annotate({
    description:
      "The explicit reason for soft-forgetting this memory.",
  }),
})

export const MemoryForgetTool = Tool.define<
  typeof MemoryForgetParameters,
  CandidateFacadeMetadata,
  never
>(
  "memory_forget",
  Effect.succeed({
    description:
      "Soft-forget one validated memoriX memory by exact identifier. The memory is deactivated in the Titan hot site only and remains available in audit history.",
    parameters: MemoryForgetParameters,
    execute: (
      params: Schema.Schema.Type<
        typeof MemoryForgetParameters
      >,
      ctx: Tool.Context<CandidateFacadeMetadata>,
    ) =>
      Effect.gen(function* () {
        yield* ctx.ask({
          permission: "memory_forget",
          patterns: [params.memory_id],
          always: [],
          metadata: {
            operation: "forget_memory",
            memory_id: params.memory_id,
            validated_by: params.validated_by,
            reason: params.reason,
          },
        })

        return yield* Effect.promise(() =>
          forgetMemoryThroughMemoriX(
            getDefaultMemoriXService(),
            {
              memoryId: params.memory_id,
              validatedBy: params.validated_by,
              reason: params.reason,
            },
          ),
        )
      }),
  } satisfies Tool.DefWithoutID<
    typeof MemoryForgetParameters,
    CandidateFacadeMetadata
  >),
)

export const MemoryConsolidateTool = Tool.define<
  typeof ConsolidationParameters,
  CandidateFacadeMetadata,
  never
>(
  "memory_consolidate",
  Effect.succeed({
    description:
      "Run memoriX Titan V2 consolidation over short-term events. This creates pending candidates only and never validates them automatically.",
    parameters: ConsolidationParameters,
    execute: (
      params: Schema.Schema.Type<
        typeof ConsolidationParameters
      >,
      ctx: Tool.Context<CandidateFacadeMetadata>,
    ) =>
      Effect.gen(function* () {
        const mode = params.mode ?? "manual"

        yield* ctx.ask({
          permission: "memory_consolidate",
          patterns: [mode],
          always: [],
          metadata: {
            operation: "run_consolidation",
            mode,
          },
        })

        return yield* Effect.promise(() =>
          runConsolidationThroughMemoriX(
            getDefaultMemoriXService(),
            mode,
          ),
        )
      }),
  } satisfies Tool.DefWithoutID<
    typeof ConsolidationParameters,
    CandidateFacadeMetadata
  >),
)

export const MemoryNightlyRunTool = Tool.define<
  typeof NightlyParameters,
  CandidateFacadeMetadata,
  never
>(
  "memory_nightly_run",
  Effect.succeed({
    description:
      "Run the protected memoriX nightly consolidation. This may create pending candidates, replay active Titan memories, and clear short-term events only after success.",
    parameters: NightlyParameters,
    execute: (
      params: Schema.Schema.Type<
        typeof NightlyParameters
      >,
      ctx: Tool.Context<CandidateFacadeMetadata>,
    ) =>
      Effect.gen(function* () {
        const clearShortTermAfterSuccess =
          params.clear_short_term_after_success ?? true

        yield* ctx.ask({
          permission: "memory_nightly_run",
          patterns: [
            clearShortTermAfterSuccess
              ? "clear-short-term-after-success"
              : "keep-short-term",
          ],
          always: [],
          metadata: {
            operation: "run_nightly",
            clear_short_term_after_success:
              clearShortTermAfterSuccess,
          },
        })

        return yield* Effect.promise(() =>
          runNightlyThroughMemoriX(
            getDefaultMemoriXService(),
            clearShortTermAfterSuccess,
          ),
        )
      }),
  } satisfies Tool.DefWithoutID<
    typeof NightlyParameters,
    CandidateFacadeMetadata
  >),
)

export const MemoryStatusTool = Tool.define<
  typeof MemoryStatusParameters,
  CandidateFacadeMetadata,
  never
>(
  "memory_status",
  Effect.succeed({
    description:
      "Return the current memoriX architecture, storage, candidate, and Titan status without mutating memory.",
    parameters: MemoryStatusParameters,
    execute: (
      _params: Schema.Schema.Type<
        typeof MemoryStatusParameters
      >,
      _ctx: Tool.Context<CandidateFacadeMetadata>,
    ) =>
      Effect.promise(() =>
        getMemoriXStatus(
          getDefaultMemoriXService(),
        ),
      ),
  } satisfies Tool.DefWithoutID<
    typeof MemoryStatusParameters,
    CandidateFacadeMetadata
  >),
)
