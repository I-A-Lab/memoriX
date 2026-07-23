import { describe, expect, test } from "bun:test"

import {
  getProjectSnapshotThroughMemoriX,
  listProjectEntriesThroughMemoriX,
  rebuildProjectSnapshotThroughMemoriX,
  recordProjectEntryThroughMemoriX,
  type MemoriXProjectArchiveEntry,
  type MemoriXProjectSnapshot,
  type ProjectArchiveFacadeService,
} from "../../src/memorix"

function statefulService() {
  const entries: MemoriXProjectArchiveEntry[] = []
  const snapshots: MemoriXProjectSnapshot[] = []

  const service: ProjectArchiveFacadeService = {
    recordProjectArchiveEntry: async (input) => {
      const entry: MemoriXProjectArchiveEntry = {
        ...input,
        entry_id: `project_entry_${entries.length + 1}`,
        metadata: input.metadata ?? {},
        created_at: "2026-07-16T17:00:00+00:00",
        recorded_at: "2026-07-16T17:01:00+00:00",
      }
      entries.push(entry)
      return { ok: true, value: entry }
    },
    listProjectArchiveEntries: async (options = {}) => ({
      ok: true,
      value: entries.filter(
        (entry) =>
          (options.projectID === undefined || entry.project_id === options.projectID) &&
          (options.entryType === undefined || entry.entry_type === options.entryType),
      ),
    }),
    rebuildProjectSnapshot: async (projectID) => {
      const projectEntries = entries.filter((entry) => entry.project_id === projectID)
      const identity = projectEntries.filter((entry) => entry.entry_type === "identity").at(-1)
      if (!identity) {
        return {
          ok: false,
          code: "operation",
          message: "Project identity is required.",
        }
      }
      const snapshot: MemoriXProjectSnapshot = {
        project_id: projectID,
        name: identity.title,
        summary: identity.content,
        objectives: projectEntries
          .filter((entry) => entry.entry_type === "objective")
          .map((entry) => entry.content),
        decisions: projectEntries
          .filter((entry) => entry.entry_type === "decision")
          .map((entry) => entry.content),
        architecture: [],
        milestones: [],
        completed_tasks: [],
        remaining_tasks: [],
        problems: [],
        solutions: [],
        latest_changes: [],
        source_entry_ids: projectEntries.map((entry) => entry.entry_id),
        version: snapshots.length + 1,
        updated_at: "2026-07-16T17:02:00+00:00",
      }
      snapshots.push(snapshot)
      return { ok: true, value: snapshot }
    },
    getProjectSnapshot: async (projectID) => ({
      ok: true,
      value:
        snapshots.filter((snapshot) => snapshot.project_id === projectID).at(-1) ?? null,
    }),
  }

  return { service }
}

describe("project archive integration flow", () => {
  test("record, list, rebuild and get preserve one project flow", async () => {
    const { service } = statefulService()

    const identity = await recordProjectEntryThroughMemoriX(service, {
      project_id: "memorix",
      entry_type: "identity",
      title: "memoriX",
      content: "Long-term memory for AI agents.",
      source_event_ids: ["event_identity"],
      author: "Elwen",
    })
    const objective = await recordProjectEntryThroughMemoriX(service, {
      project_id: "memorix",
      entry_type: "objective",
      title: "Objective",
      content: "Provide durable project memory.",
      source_event_ids: ["event_objective"],
      author: "Elwen",
    })
    const listed = await listProjectEntriesThroughMemoriX(service, {
      projectID: "memorix",
    })
    const rebuilt = await rebuildProjectSnapshotThroughMemoriX(service, "memorix")
    const latest = await getProjectSnapshotThroughMemoriX(service, "memorix")

    expect(identity.metadata.ok).toBe(true)
    expect(objective.metadata.ok).toBe(true)
    expect(listed.metadata.entries).toHaveLength(2)
    expect(rebuilt.metadata.snapshot?.version).toBe(1)
    expect(rebuilt.metadata.snapshot?.objectives).toEqual([
      "Provide durable project memory.",
    ])
    expect(latest.metadata.snapshot).toEqual(rebuilt.metadata.snapshot)
  })

  test("a service failure remains non-blocking", async () => {
    const { service } = statefulService()
    service.recordProjectArchiveEntry = async () => ({
      ok: false,
      code: "operation",
      message: "simulated failure",
    })

    const result = await recordProjectEntryThroughMemoriX(service, {
      project_id: "memorix",
      entry_type: "note",
      title: "Note",
      content: "This operation fails safely.",
      source_event_ids: ["event_failure"],
      author: "Elwen",
    })

    expect(result.metadata.ok).toBe(false)
    expect(result.metadata.failure?.code).toBe("operation")
    expect(result.output).toContain("simulated failure")
  })
})
