import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import { join } from "node:path"

const source = readFileSync(
  join(import.meta.dir, "../../src/tool/project-archive.ts"),
  "utf8",
)

function block(id: string, next?: string) {
  const start = source.indexOf(`"${id}"`)
  const end = next ? source.indexOf(`"${next}"`, start + id.length) : source.length
  return source.slice(start, end)
}

describe("project archive native permissions", () => {
  test("record asks before facade call", () => {
    const value = block("project_archive_record", "project_archive_list")
    expect(value.indexOf("ctx.ask")).toBeLessThan(
      value.indexOf("recordProjectEntryThroughMemoriX("),
    )
    expect(value).toContain('permission: "project_archive_record"')
  })

  test("snapshot rebuild asks before facade call", () => {
    const value = block("project_snapshot_rebuild", "project_snapshot_get")
    expect(value.indexOf("ctx.ask")).toBeLessThan(
      value.indexOf("rebuildProjectSnapshotThroughMemoriX("),
    )
    expect(value).toContain('permission: "project_snapshot_rebuild"')
  })

  test("read-only tools do not ask", () => {
    expect(block("project_archive_list", "project_snapshot_rebuild")).not.toContain("ctx.ask")
    expect(block("project_snapshot_get")).not.toContain("ctx.ask")
  })
})
