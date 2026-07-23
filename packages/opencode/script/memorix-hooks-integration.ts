import os from "node:os"
import path from "node:path"
import {
  mkdtemp,
  readFile,
  rm,
} from "node:fs/promises"

import {
  MemoriXService,
  memoriXHookOptionsFromEnvironment,
  recordToolResultHook,
  recordUserMessageHook,
} from "../src/memorix"

function assertCondition(
  condition: unknown,
  message: string,
): asserts condition {
  if (!condition) throw new Error(message)
}

async function lineCount(
  filePath: string,
): Promise<number> {
  try {
    const content = await readFile(
      filePath,
      "utf8",
    )

    return content
      .split(/\r?\n/)
      .filter(Boolean)
      .length
  } catch (error) {
    if (
      error instanceof Error &&
      "code" in error &&
      error.code === "ENOENT"
    ) {
      return 0
    }

    throw error
  }
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
    "memorix-hooks-integration-",
  ),
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

const disabledOptions =
  memoriXHookOptionsFromEnvironment({})

const enabledOptions =
  memoriXHookOptionsFromEnvironment({
    MEMORIX_HOOK_CAPTURE_MESSAGES:
      "true",
    MEMORIX_HOOK_CAPTURE_TOOL_RESULTS:
      "true",
  })

try {
  console.log(
    "[1/6] Verifying hooks are disabled by default...",
  )

  const disabledMessage =
    await recordUserMessageHook(
      service,
      disabledOptions,
      {
        sessionID: "session_hooks",
        messageID: "message_disabled",
        agent: "integration_agent",
        text: "Disabled message",
      },
    )

  assertCondition(
    disabledMessage.status === "skipped",
    "Message hook was enabled by default.",
  )

  console.log(
    "[2/6] Recording one user message...",
  )

  const messageResult =
    await recordUserMessageHook(
      service,
      enabledOptions,
      {
        sessionID: "session_hooks",
        messageID: "message_enabled",
        agent: "integration_agent",
        model: {
          providerID: "test",
          modelID: "test",
        },
        text:
          "Passive hook integration message HOOK-MESSAGE-4817.",
      },
    )

  assertCondition(
    messageResult.status === "recorded",
    "User-message hook did not record an event.",
  )

  console.log(
    "[3/6] Confirming memory tools are excluded...",
  )

  const ignoredTool =
    await recordToolResultHook(
      service,
      enabledOptions,
      {
        sessionID: "session_hooks",
        callID: "call_ignored",
        tool: "memory_store",
        args: {},
        title: "Memory",
        output: "Ignored",
        metadata: {},
      },
    )

  assertCondition(
    ignoredTool.status === "skipped",
    "memory_store should be excluded from hook capture.",
  )

  console.log(
    "[4/6] Recording one normal tool result...",
  )

  const toolResult =
    await recordToolResultHook(
      service,
      enabledOptions,
      {
        sessionID: "session_hooks",
        callID: "call_recorded",
        tool: "read",
        args: {
          filePath: "README.md",
        },
        title: "Read README",
        output:
          "Passive tool hook token HOOK-TOOL-5928.",
        metadata: {},
      },
    )

  assertCondition(
    toolResult.status === "recorded",
    "Tool-result hook did not record an event.",
  )

  console.log(
    "[5/6] Verifying short-term and cold counts...",
  )

  const status = await service.status()

  assertCondition(
    status.ok,
    status.ok
      ? ""
      : `Status failed: ${status.message}`,
  )

  assertCondition(
    status.value.short_term_events === 2,
    `Expected two short-term events, received ${status.value.short_term_events}.`,
  )

  assertCondition(
    status.value.cold_archive_events === 2,
    `Expected two cold events, received ${status.value.cold_archive_events}.`,
  )

  assertCondition(
    status.value.hot_memories_active === 0,
    "Passive hooks unexpectedly wrote to the hot site.",
  )

  assertCondition(
    status.value.candidates.pending === 0,
    "Passive hooks unexpectedly created candidates.",
  )

  console.log(
    "[6/6] Verifying physical cold archive...",
  )

  const coldPath =
    path.join(
      runtimeRoot,
      "cold_site",
      "events_archive.jsonl",
    )

  const coldLines =
    await lineCount(coldPath)

  assertCondition(
    coldLines === 2,
    `Expected two cold JSONL records, received ${coldLines}.`,
  )

  console.log(
    "memoriX passive hooks integration: OK",
  )
} finally {
  await service.close()

  await rm(runtimeRoot, {
    recursive: true,
    force: true,
    maxRetries: 10,
    retryDelay: 100,
  })

  console.log(
    "Temporary hooks runtime removed.",
  )
}
