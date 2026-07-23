import os from "node:os"
import path from "node:path"
import { mkdtemp, rm } from "node:fs/promises"

import { MemoriXService } from "../src/memorix"

function assertCondition(
  condition: unknown,
  message: string,
): asserts condition {
  if (!condition) throw new Error(message)
}

const pythonExecutable =
  process.env.MEMORIX_PYTHON_EXECUTABLE?.trim()

assertCondition(
  pythonExecutable,
  "MEMORIX_PYTHON_EXECUTABLE is required.",
)

const repositoryRoot = path.resolve(
  import.meta.dir,
  "../../..",
)

const runtimeRoot = await mkdtemp(
  path.join(
    os.tmpdir(),
    "memorix-opencode-service-",
  ),
)

const disabled = new MemoriXService({
  enabled: false,
  pythonExecutable,
  projectRoot: repositoryRoot,
  runtimeRoot,
})

const disabledStatus = await disabled.status()

assertCondition(
  !disabledStatus.ok &&
    disabledStatus.code === "disabled",
  "Disabled service did not return a safe disabled result.",
)

const service = new MemoriXService({
  enabled: true,
  pythonExecutable,
  projectRoot: repositoryRoot,
  runtimeRoot,
  timeoutMs: 30_000,
  titanDModel: 32,
  titanHiddenDim: 32,
  titanMaxItems: 100,
  titanDevice: "cpu",
  titanTopK: 5,
  titanMinScore: 0,
})

try {
  console.log("[1/4] Lazy service has not connected yet.")

  assertCondition(
    service.connected === false,
    "Service connected before its first operation.",
  )

  console.log("[2/4] Calling status through safe service.")

  const status = await service.status()

  assertCondition(
    status.ok,
    status.ok
      ? ""
      : `Status failed: ${status.message}`,
  )

  assertCondition(
    service.connected,
    "Service did not lazily connect.",
  )

  assertCondition(
    status.value.retrieval_contract ===
      "hot_site_only_no_cold_fallback",
    "Invalid retrieval contract.",
  )

  console.log("[3/4] Recording event through safe service.")

  const recorded = await service.recordEvent({
    content:
      "memoriX service integration cold token SERVICE-COLD-8192.",
    event_type: "architecture_rule",
    source: "opencode_service_integration",
    importance: 0.9,
    confidence: 1,
    surprise: 0.5,
  })

  assertCondition(
    recorded.ok,
    recorded.ok
      ? ""
      : `Record failed: ${recorded.message}`,
  )

  const hot = await service.context(
    "SERVICE-COLD-8192",
  )

  assertCondition(
    hot.ok,
    hot.ok
      ? ""
      : `Context failed: ${hot.message}`,
  )

  assertCondition(
    hot.value.source === "hot_site",
    "Context did not use hot_site.",
  )

  assertCondition(
    hot.value.matches.length === 0,
    "Cold information leaked into hot retrieval.",
  )

  const cold = await service.searchColdHistory(
    "SERVICE-COLD-8192",
  )

  assertCondition(
    cold.ok,
    cold.ok
      ? ""
      : `Cold search failed: ${cold.message}`,
  )

  assertCondition(
    cold.value.source === "cold_audit",
    "Explicit cold search did not use cold_audit.",
  )

  assertCondition(
    cold.value.matches.length === 1,
    "Expected one cold audit result.",
  )

  console.log("[4/4] Non-blocking service integration: OK")
} finally {
  await service.close()
  await disabled.close()

  await rm(runtimeRoot, {
    recursive: true,
    force: true,
    maxRetries: 10,
    retryDelay: 100,
  })

  console.log("Temporary service runtime removed.")
}
