import {
  describe,
  expect,
  test,
} from "bun:test"
import path from "node:path"

import {
  memoriXServiceOptionsFromEnvironment,
  resolveDefaultMemoriXRuntimeRoot,
} from "../../src/memorix/service"

describe("memoriX runtime root resolution", () => {
  test("explicit runtime environment has priority", () => {
    const explicit = path.resolve(
      "C:/custom/memorix-runtime",
    )

    expect(
      resolveDefaultMemoriXRuntimeRoot({
        MEMORIX_RUNTIME_ROOT: explicit,
        LOCALAPPDATA: "C:/ignored",
      }),
    ).toBe(explicit)
  })

  test("uses LOCALAPPDATA for a Windows-style environment", () => {
    const localAppData = path.resolve(
      "C:/Users/test/AppData/Local",
    )

    expect(
      resolveDefaultMemoriXRuntimeRoot({
        LOCALAPPDATA: localAppData,
      }),
    ).toBe(
      path.resolve(
        localAppData,
        "memoriX",
        "runtime",
      ),
    )
  })

  test("uses XDG_DATA_HOME when LOCALAPPDATA is absent", () => {
    const xdgDataHome = path.resolve(
      "/tmp/xdg-data",
    )

    expect(
      resolveDefaultMemoriXRuntimeRoot({
        XDG_DATA_HOME: xdgDataHome,
      }),
    ).toBe(
      path.resolve(
        xdgDataHome,
        "memoriX",
        "runtime",
      ),
    )
  })

  test("uses the supplied home fallback outside the repository", () => {
    const home = path.resolve("/tmp/memorix-home")
    const repository = path.resolve(
      import.meta.dir,
      "../../../..",
    )

    const runtime =
      resolveDefaultMemoriXRuntimeRoot(
        {},
        {
          homeDirectory: home,
          temporaryDirectory:
            path.resolve("/tmp/memorix-temp"),
        },
      )

    expect(runtime).toBe(
      path.resolve(
        home,
        ".local",
        "share",
        "memoriX",
        "runtime",
      ),
    )
    expect(runtime.startsWith(repository)).toBe(false)
  })

  test("service options use the same default resolver", () => {
    const localAppData = path.resolve(
      "C:/Users/test/AppData/Local",
    )

    const options =
      memoriXServiceOptionsFromEnvironment({
        LOCALAPPDATA: localAppData,
      })

    expect(options.runtimeRoot).toBe(
      path.resolve(
        localAppData,
        "memoriX",
        "runtime",
      ),
    )
  })

  test("an explicit service override still has highest priority", () => {
    const override = path.resolve(
      "C:/override/memorix-runtime",
    )

    const options =
      memoriXServiceOptionsFromEnvironment(
        {
          MEMORIX_RUNTIME_ROOT:
            "C:/environment/memorix-runtime",
          LOCALAPPDATA:
            "C:/Users/test/AppData/Local",
        },
        {
          runtimeRoot: override,
        },
      )

    expect(options.runtimeRoot).toBe(override)
  })
})
