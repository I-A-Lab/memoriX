import { describe, expect, test } from "bun:test"
import { parse } from "jsonc-parser"
import path from "path"

const promptPath = path.join(
  import.meta.dir,
  "../../src/agent/prompt/sdlc.txt",
)

const configPath = path.join(
  import.meta.dir,
  "../../../../.opencode/opencode.jsonc",
)

describe("SDLC memoriX final-milestone policy", () => {
  test("creates one pending candidate only after successful final validation", async () => {
    const prompt = await Bun.file(promptPath).text()

    expect(prompt).toContain(
      "Do not create a durable candidate merely because a project or cycle has started.",
    )
    expect(prompt).toContain(
      "FINAL VALIDATION PERSISTENCE SEQUENCE",
    )
    expect(prompt).toContain(
      "automatically perform this sequence exactly once",
    )
    expect(prompt).toContain(
      "call memory_store exactly once before project_archive_record",
    )
    expect(prompt).toContain(
      "Capture the returned candidateID and real short-term eventID.",
    )
    expect(prompt).toContain(
      "call project_archive_record exactly once with a non-empty source_event_ids array",
    )
    expect(prompt).toContain(
      "Never call project_archive_record with an empty or omitted source_event_ids field.",
    )
    expect(prompt).toContain(
      "Do not wait for the user to ask for candidate creation.",
    )
    expect(prompt).toContain(
      "Never run the final persistence sequence when tests fail",
    )
    expect(prompt).toContain(
      "Never call memory_candidate_validate or memory_candidate_reject automatically.",
    )
    expect(prompt).toContain(
      "idempotent within a cycle",
    )
  })

  test("allows automatic proposal but keeps Titan admission human-gated", async () => {
    const config = parse(
      await Bun.file(configPath).text(),
    ) as {
      permission?: Record<string, string>
    }

    expect(config.permission?.memory_store).toBe("allow")
    expect(config.permission?.project_archive_record).toBe(
      "allow",
    )
    expect(
      config.permission?.memory_candidate_validate,
    ).toBe("ask")
    expect(
      config.permission?.memory_candidate_reject,
    ).toBe("ask")
  })
})
