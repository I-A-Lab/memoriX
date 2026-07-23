import type { MemoriXService } from "./service"
import type {
  MemoriXProjectArchiveEntry,
  MemoriXProjectArchiveEntryType,
  MemoriXProjectEntryRecordInput,
  MemoriXProjectSnapshot,
} from "./types"

export type ProjectArchiveFacadeService = Pick<
  MemoriXService,
  | "recordProjectArchiveEntry"
  | "listProjectArchiveEntries"
  | "rebuildProjectSnapshot"
  | "getProjectSnapshot"
>

export type ProjectArchiveFacadeMetadata = {
  operation:
    | "record_project_entry"
    | "list_project_entries"
    | "rebuild_project_snapshot"
    | "get_project_snapshot"
  ok: boolean
  entry?: MemoriXProjectArchiveEntry
  entries?: MemoriXProjectArchiveEntry[]
  snapshot?: MemoriXProjectSnapshot | null
  failure?: { code: string; message: string }
}

export type ProjectArchiveFacadeResult = {
  title: string
  output: string
  metadata: ProjectArchiveFacadeMetadata
}

function failure(
  operation: ProjectArchiveFacadeMetadata["operation"],
  title: string,
  result: { code: string; message: string },
): ProjectArchiveFacadeResult {
  return {
    title,
    output: `memoriX operation unavailable: ${result.message}`,
    metadata: {
      operation,
      ok: false,
      failure: { code: result.code, message: result.message },
    },
  }
}

export async function recordProjectEntryThroughMemoriX(
  service: ProjectArchiveFacadeService,
  input: MemoriXProjectEntryRecordInput,
): Promise<ProjectArchiveFacadeResult> {
  const result = await service.recordProjectArchiveEntry(input)
  if (!result.ok) {
    return failure("record_project_entry", "Project entry recording failed", result)
  }
  return {
    title: "Project archive entry recorded",
    output: JSON.stringify(result.value, null, 2),
    metadata: {
      operation: "record_project_entry",
      ok: true,
      entry: result.value,
    },
  }
}

export async function listProjectEntriesThroughMemoriX(
  service: ProjectArchiveFacadeService,
  options: {
    projectID?: string
    entryType?: MemoriXProjectArchiveEntryType
  } = {},
): Promise<ProjectArchiveFacadeResult> {
  const result = await service.listProjectArchiveEntries(options)
  if (!result.ok) {
    return failure("list_project_entries", "Project entries unavailable", result)
  }
  return {
    title: `Project archive entries: ${result.value.length}`,
    output: JSON.stringify(result.value, null, 2),
    metadata: {
      operation: "list_project_entries",
      ok: true,
      entries: result.value,
    },
  }
}

export async function rebuildProjectSnapshotThroughMemoriX(
  service: ProjectArchiveFacadeService,
  projectID: string,
): Promise<ProjectArchiveFacadeResult> {
  const result = await service.rebuildProjectSnapshot(projectID)
  if (!result.ok) {
    return failure("rebuild_project_snapshot", "Project snapshot rebuild failed", result)
  }
  return {
    title: "Project snapshot rebuilt",
    output: JSON.stringify(result.value, null, 2),
    metadata: {
      operation: "rebuild_project_snapshot",
      ok: true,
      snapshot: result.value,
    },
  }
}

export async function getProjectSnapshotThroughMemoriX(
  service: ProjectArchiveFacadeService,
  projectID: string,
): Promise<ProjectArchiveFacadeResult> {
  const result = await service.getProjectSnapshot(projectID)
  if (!result.ok) {
    return failure("get_project_snapshot", "Project snapshot unavailable", result)
  }
  return {
    title: result.value ? "Project snapshot" : "No project snapshot",
    output: result.value ? JSON.stringify(result.value, null, 2) : "No project snapshot exists.",
    metadata: {
      operation: "get_project_snapshot",
      ok: true,
      snapshot: result.value,
    },
  }
}
