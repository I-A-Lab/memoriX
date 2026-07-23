import { describe, expect, test } from "bun:test"

import {
  getProjectSnapshotThroughMemoriX,
  recordProjectEntryThroughMemoriX,
  type ProjectArchiveFacadeService,
} from "../../src/memorix"

const entry = {
  entry_id: "project_entry_test",
  project_id: "memorix",
  entry_type: "decision" as const,
  title: "Decision",
  content: "Keep history append-only.",
  source_event_ids: ["event_test"],
  author: "Elwen",
  created_at: "2026-07-16T14:00:00+00:00",
  recorded_at: "2026-07-16T14:01:00+00:00",
  metadata: {},
}

function service(): ProjectArchiveFacadeService {
  return {
    recordProjectArchiveEntry: async () => ({ ok: true, value: entry }),
    listProjectArchiveEntries: async () => ({ ok: true, value: [entry] }),
    rebuildProjectSnapshot: async () => ({
      ok: true,
      value: {
        project_id: "memorix",
        name: "memoriX",
        summary: "Memory system.",
        objectives: [],
        decisions: [entry.content],
        architecture: [],
        milestones: [],
        completed_tasks: [],
        remaining_tasks: [],
        problems: [],
        solutions: [],
        latest_changes: [],
        source_entry_ids: [entry.entry_id],
        version: 1,
        updated_at: "2026-07-16T14:02:00+00:00",
      },
    }),
    getProjectSnapshot: async () => ({ ok: true, value: null }),
  }
}

describe("project archive facade", () => {
  test("records one entry", async () => {
    const result = await recordProjectEntryThroughMemoriX(service(), {
      project_id: "memorix",
      entry_type: "decision",
      title: "Decision",
      content: entry.content,
      source_event_ids: ["event_test"],
      author: "Elwen",
    })
    expect(result.metadata.ok).toBe(true)
    expect(result.metadata.entry?.entry_id).toBe(entry.entry_id)
  })

  test("represents a missing snapshot safely", async () => {
    const result = await getProjectSnapshotThroughMemoriX(service(), "memorix")
    expect(result.metadata.ok).toBe(true)
    expect(result.metadata.snapshot).toBeNull()
  })
})
