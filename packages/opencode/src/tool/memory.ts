import { Effect, Schema } from "effect"
import * as Tool from "./tool"
import path from "path"
import fs from "fs/promises"

const MEMORY_DIR = path.join(".opencode", "memory")
const MEMORY_FILE = path.join(MEMORY_DIR, "titan_store.json")

export interface MemoryFact {
  id: string
  subject: string
  content: string
  tags: readonly string[]
  timestamp: number
}

const ensureMemoryStore = async (): Promise<MemoryFact[]> => {
  try {
    await fs.mkdir(MEMORY_DIR, { recursive: true })
    const data = await fs.readFile(MEMORY_FILE, "utf-8")
    return JSON.parse(data)
  } catch {
    return []
  }
}

const saveMemoryStore = async (facts: MemoryFact[]): Promise<void> => {
  await fs.mkdir(MEMORY_DIR, { recursive: true })
  await fs.writeFile(MEMORY_FILE, JSON.stringify(facts, null, 2), "utf-8")
}

export const StoreParameters = Schema.Struct({
  subject: Schema.String.annotate({ description: "The subject or architectural component of the fact" }),
  content: Schema.String.annotate({ description: "The detailed fact, contract, or decision to memorize" }),
  tags: Schema.Array(Schema.String).annotate({ description: "Tags for categorization and retrieval (e.g., ['prd', 'interface', 'api'])" }),
})

type StoreMetadata = {
  fact: MemoryFact
}

export const MemoryStoreTool = Tool.define<typeof StoreParameters, StoreMetadata, never>(
  "memory_store",
  Effect.gen(function* () {
    return {
      description: "Store an important architectural fact, interface contract, or progress state into Titan long-term memory.",
      parameters: StoreParameters,
      execute: (params: Schema.Schema.Type<typeof StoreParameters>, ctx: Tool.Context<StoreMetadata>) =>
        Effect.gen(function* () {
          const facts = yield* Effect.promise(() => ensureMemoryStore())
          const newFact: MemoryFact = {
            id: Math.random().toString(36).substring(2, 11),
            subject: params.subject,
            content: params.content,
            tags: [...params.tags],
            timestamp: Date.now(),
          }
          facts.push(newFact)
          yield* Effect.promise(() => saveMemoryStore(facts))

          return {
            title: `Stored memory: ${params.subject}`,
            output: `Successfully stored fact [ID: ${newFact.id}] under subject '${params.subject}'.`,
            metadata: { fact: newFact },
          }
        }),
    } satisfies Tool.DefWithoutID<typeof StoreParameters, StoreMetadata>
  }),
)

export const RetrieveParameters = Schema.Struct({
  query: Schema.String.annotate({ description: "Search query or keywords to match against stored memory facts" }),
  tags: Schema.optional(Schema.Array(Schema.String)).annotate({ description: "Optional list of tags to filter by" }),
})

type RetrieveMetadata = {
  results: MemoryFact[]
}

export const MemoryRetrieveTool = Tool.define<typeof RetrieveParameters, RetrieveMetadata, never>(
  "memory_retrieve",
  Effect.gen(function* () {
    return {
      description: "Retrieve architectural facts, interface contracts, or progress states from Titan long-term memory.",
      parameters: RetrieveParameters,
      execute: (params: Schema.Schema.Type<typeof RetrieveParameters>, ctx: Tool.Context<RetrieveMetadata>) =>
        Effect.gen(function* () {
          const facts = yield* Effect.promise(() => ensureMemoryStore())
          const q = params.query.toLowerCase()
          const results = facts.filter((f) => {
            const matchesQuery =
              f.subject.toLowerCase().includes(q) ||
              f.content.toLowerCase().includes(q) ||
              f.tags.some((t) => t.toLowerCase().includes(q))
            const matchesTags =
              !params.tags || params.tags.length === 0 || params.tags.some((pt) => f.tags.includes(pt))
            return matchesQuery && matchesTags
          })

          return {
            title: `Retrieved ${results.length} memory facts`,
            output: results.length > 0 ? JSON.stringify(results, null, 2) : "No matching memory facts found.",
            metadata: { results },
          }
        }),
    } satisfies Tool.DefWithoutID<typeof RetrieveParameters, RetrieveMetadata>
  }),
)
