import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import path from "node:path"

import {
  memoriXServiceOptionsFromEnvironment,
  resolveTrustedMemoriXScope,
} from "../../src/memorix"
import {
  trustedMemoryScopeFromContext,
} from "../../src/tool/memory"

const repositoryRoot = path.resolve(
  import.meta.dir,
  "../../../..",
)

describe("trusted memoriX scope", () => {
  test("normalizes trusted project and user identifiers", () => {
    expect(
      resolveTrustedMemoriXScope({
        projectID: "  project-alpha  ",
        userID: "  user-elwen  ",
      }),
    ).toEqual({
      projectID: "project-alpha",
      userID: "user-elwen",
    })
  })

  test("drops blank or non-string identifiers", () => {
    expect(
      resolveTrustedMemoriXScope({
        projectID: "   ",
        userID: 42,
      }),
    ).toEqual({})
  })

  test("reads the configured user from MEMORIX_USER_ID", () => {
    const options = memoriXServiceOptionsFromEnvironment(
      {
        MEMORIX_USER_ID: "  user-elwen  ",
      },
      {
        projectRoot: repositoryRoot,
        runtimeRoot: path.join(
          repositoryRoot,
          ".tmp",
          "memorix-trusted-scope",
        ),
      },
    )

    expect(options.userID).toBe("user-elwen")
  })

  test("uses session project and configured user only", () => {
    const scope = trustedMemoryScopeFromContext(
      {
        extra: {
          projectID: "project-alpha",
          ignoredProjectID: "project-beta",
        },
      },
      "user-elwen",
    )

    expect(scope).toEqual({
      projectID: "project-alpha",
      userID: "user-elwen",
    })
  })

  test("native tool schemas expose no model-controlled scope", () => {
    const source = readFileSync(
      path.join(
        repositoryRoot,
        "packages/opencode/src/tool/memory.ts",
      ),
      "utf8",
    )

    expect(source).not.toContain(
      "project_id: Schema",
    )
    expect(source).not.toContain(
      "user_id: Schema",
    )
    expect(source).toContain(
      "projectID: scope.projectID",
    )
    expect(source).toContain(
      "userID: scope.userID",
    )
  })

  test("session tool context injects the current project", () => {
    const source = readFileSync(
      path.join(
        repositoryRoot,
        "packages/opencode/src/session/tools.ts",
      ),
      "utf8",
    )

    expect(source).toContain(
      "projectID: String(input.session.projectID)",
    )
    expect(source).toContain(
      "projectDirectory: input.session.directory",
    )
  })
})
