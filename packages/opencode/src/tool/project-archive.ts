import { Effect, Schema } from "effect"

import {
  getDefaultMemoriXService,
  getProjectSnapshotThroughMemoriX,
  listProjectEntriesThroughMemoriX,
  rebuildProjectSnapshotThroughMemoriX,
  recordProjectEntryThroughMemoriX,
  type ProjectArchiveFacadeMetadata,
} from "../memorix"
import * as Tool from "./tool"

export const ProjectEntryTypeSchema = Schema.Union([
  Schema.Literal("identity"),
  Schema.Literal("objective"),
  Schema.Literal("decision"),
  Schema.Literal("architecture"),
  Schema.Literal("milestone"),
  Schema.Literal("task_completed"),
  Schema.Literal("task_remaining"),
  Schema.Literal("problem"),
  Schema.Literal("solution"),
  Schema.Literal("change"),
  Schema.Literal("note"),
])

const RecordParameters = Schema.Struct({
  project_id: Schema.String,
  entry_type: ProjectEntryTypeSchema,
  title: Schema.String,
  content: Schema.String,
  source_event_ids: Schema.Array(Schema.String),
  author: Schema.String,
})

const ListParameters = Schema.Struct({
  project_id: Schema.optional(Schema.String),
  entry_type: Schema.optional(ProjectEntryTypeSchema),
})

const SnapshotParameters = Schema.Struct({
  project_id: Schema.String,
})

export const ProjectArchiveRecordTool = Tool.define<
  typeof RecordParameters,
  ProjectArchiveFacadeMetadata,
  never
>(
  "project_archive_record",
  Effect.succeed({
    description: "Append one explicit structured entry to the memoriX project archive.",
    parameters: RecordParameters,
    execute: (params, ctx) =>
      Effect.gen(function* () {
        yield* ctx.ask({
          permission: "project_archive_record",
          patterns: [params.project_id],
          always: [],
          metadata: {
            operation: "record_project_entry",
            project_id: params.project_id,
            entry_type: params.entry_type,
            title: params.title,
          },
        })
        return yield* Effect.promise(() =>
          recordProjectEntryThroughMemoriX(
            getDefaultMemoriXService(),
            {
              ...params,
              source_event_ids: [
                ...params.source_event_ids,
              ],
            },
          ),
        )
      }),
  }),
)

export const ProjectArchiveListTool = Tool.define<
  typeof ListParameters,
  ProjectArchiveFacadeMetadata,
  never
>(
  "project_archive_list",
  Effect.succeed({
    description: "List memoriX project archive entries without mutation.",
    parameters: ListParameters,
    execute: (params, _ctx) =>
      Effect.promise(() =>
        listProjectEntriesThroughMemoriX(
          getDefaultMemoriXService(),
          {
            projectID: params.project_id,
            entryType: params.entry_type,
          },
        ),
      ),
  }),
)

export const ProjectSnapshotRebuildTool = Tool.define<
  typeof SnapshotParameters,
  ProjectArchiveFacadeMetadata,
  never
>(
  "project_snapshot_rebuild",
  Effect.succeed({
    description: "Rebuild and append the next memoriX project snapshot version.",
    parameters: SnapshotParameters,
    execute: (params, ctx) =>
      Effect.gen(function* () {
        yield* ctx.ask({
          permission: "project_snapshot_rebuild",
          patterns: [params.project_id],
          always: [],
          metadata: {
            operation: "rebuild_project_snapshot",
            project_id: params.project_id,
          },
        })
        return yield* Effect.promise(() =>
          rebuildProjectSnapshotThroughMemoriX(
            getDefaultMemoriXService(),
            params.project_id,
          ),
        )
      }),
  }),
)

export const ProjectSnapshotGetTool = Tool.define<
  typeof SnapshotParameters,
  ProjectArchiveFacadeMetadata,
  never
>(
  "project_snapshot_get",
  Effect.succeed({
    description: "Read the latest memoriX project snapshot without mutation.",
    parameters: SnapshotParameters,
    execute: (params, _ctx) =>
      Effect.promise(() =>
        getProjectSnapshotThroughMemoriX(
          getDefaultMemoriXService(),
          params.project_id,
        ),
      ),
  }),
)
