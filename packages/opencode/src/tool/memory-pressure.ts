import { Effect, Schema } from "effect"
import {
  getDefaultMemoriXService,
  getMemoryPressureStatus,
  inspectMemoryPressure,
  type MemoryPressureFacadeResult,
} from "../memorix"
import * as Tool from "./tool"

const Status = Schema.Struct({
  simulate_count: Schema.optional(Schema.Number),
  assessment_limit: Schema.optional(Schema.Number),
})
const Inspect = Schema.Struct({ memory_id: Schema.String })
type Metadata = MemoryPressureFacadeResult["metadata"]

export const MemoryPressureStatusTool = Tool.define<
  typeof Status,
  Metadata,
  never
>(
  "memory_pressure_status",
  Effect.succeed({
    description:
      "Inspect persisted memoriX hot-site pressure without mutation or Titan loading.",
    parameters: Status,
    execute: (
      params: Schema.Schema.Type<typeof Status>,
      _ctx: Tool.Context<Metadata>,
    ) =>
      Effect.promise(() =>
        getMemoryPressureStatus(
          getDefaultMemoriXService(),
          params.simulate_count,
          params.assessment_limit ?? 100,
        ),
      ),
  } satisfies Tool.DefWithoutID<typeof Status, Metadata>),
)

export const MemoryPressureInspectTool = Tool.define<
  typeof Inspect,
  Metadata,
  never
>(
  "memory_pressure_inspect",
  Effect.succeed({
    description:
      "Inspect one persisted memoriX memory pressure assessment by ID.",
    parameters: Inspect,
    execute: (
      params: Schema.Schema.Type<typeof Inspect>,
      _ctx: Tool.Context<Metadata>,
    ) =>
      Effect.promise(() =>
        inspectMemoryPressure(
          getDefaultMemoriXService(),
          params.memory_id,
        ),
      ),
  } satisfies Tool.DefWithoutID<typeof Inspect, Metadata>),
)
