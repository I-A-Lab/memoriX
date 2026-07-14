import { Effect, Schema } from "effect"

import {
  getDefaultMemoriXService,
  retrieveMemoryThroughMemoriX,
  storeMemoryThroughMemoriX,
  type MemoryFact,
  type MemoryRetrieveFacadeMetadata,
  type MemoryStoreFacadeMetadata,
} from "../memorix"
import * as Tool from "./tool"

export type { MemoryFact }

export const StoreParameters = Schema.Struct({
  subject: Schema.String.annotate({
    description:
      "The subject or architectural component of the fact",
  }),
  content: Schema.String.annotate({
    description:
      "The detailed fact, contract, or decision to memorize",
  }),
  tags: Schema.Array(Schema.String).annotate({
    description:
      "Tags for categorization and retrieval " +
      "(for example: ['prd', 'interface', 'api'])",
  }),
})

export const MemoryStoreTool = Tool.define<
  typeof StoreParameters,
  MemoryStoreFacadeMetadata,
  never
>(
  "memory_store",
  Effect.gen(function* () {
    return {
      description:
        "Archive an important architectural fact in memoriX and " +
        "create a pending candidate for human validation. " +
        "This tool never validates or writes directly to the Titan hot site.",
      parameters: StoreParameters,
      execute: (
        params: Schema.Schema.Type<
          typeof StoreParameters
        >,
        ctx: Tool.Context<
          MemoryStoreFacadeMetadata
        >,
      ) =>
        Effect.promise(() =>
          storeMemoryThroughMemoriX(
            getDefaultMemoriXService(),
            {
              subject: params.subject,
              content: params.content,
              tags: params.tags,
            },
            {
              sessionID: String(ctx.sessionID),
              messageID: String(ctx.messageID),
              agent: ctx.agent,
            },
          ),
        ),
    } satisfies Tool.DefWithoutID<
      typeof StoreParameters,
      MemoryStoreFacadeMetadata
    >
  }),
)

export const RetrieveParameters = Schema.Struct({
  query: Schema.String.annotate({
    description:
      "Search query or keywords to match against active, " +
      "human-validated Titan hot-site memories",
  }),
  tags: Schema.optional(
    Schema.Array(Schema.String),
  ).annotate({
    description:
      "Optional tags used to filter validated hot-site results",
  }),
})

export const MemoryRetrieveTool = Tool.define<
  typeof RetrieveParameters,
  MemoryRetrieveFacadeMetadata,
  never
>(
  "memory_retrieve",
  Effect.gen(function* () {
    return {
      description:
        "Retrieve active, human-validated architectural facts from " +
        "the memoriX Titan hot site only. This tool never searches " +
        "or falls back to cold history.",
      parameters: RetrieveParameters,
      execute: (
        params: Schema.Schema.Type<
          typeof RetrieveParameters
        >,
        _ctx: Tool.Context<
          MemoryRetrieveFacadeMetadata
        >,
      ) =>
        Effect.promise(() =>
          retrieveMemoryThroughMemoriX(
            getDefaultMemoriXService(),
            {
              query: params.query,
              tags: params.tags,
            },
          ),
        ),
    } satisfies Tool.DefWithoutID<
      typeof RetrieveParameters,
      MemoryRetrieveFacadeMetadata
    >
  }),
)
