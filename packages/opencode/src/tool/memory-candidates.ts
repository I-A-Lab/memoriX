import { Effect, Schema } from "effect"
import {
  getDefaultMemoriXService,
  getMemoriXStatus,
  listCandidatesThroughMemoriX,
  rejectCandidateThroughMemoriX,
  runConsolidationThroughMemoriX,
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
          patterns: [params.candidate_id],
          always: [],
          metadata: {
            operation: "validate_candidate",
            candidate_id: params.candidate_id,
            validated_by: params.validated_by,
            validation_reason: params.validation_reason,
            final_content: params.final_content,
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
