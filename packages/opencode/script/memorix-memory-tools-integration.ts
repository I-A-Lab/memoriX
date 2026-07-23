import os from "node:os"
import path from "node:path"
import {
  mkdtemp,
  readFile,
  rm,
} from "node:fs/promises"

import {
  MemoriXClient,
  MemoriXService,
  retrieveMemoryThroughMemoriX,
  storeMemoryThroughMemoriX,
} from "../src/memorix"

function assertCondition(
  condition: unknown,
  message: string,
): asserts condition {
  if (!condition) throw new Error(message)
}

async function optionalFile(
  filePath: string,
): Promise<Buffer | undefined> {
  try {
    return await readFile(filePath)
  } catch (error) {
    if (
      error instanceof Error &&
      "code" in error &&
      error.code === "ENOENT"
    ) {
      return undefined
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
    "memorix-memory-tools-",
  ),
)

const legacyStorePath = path.join(
  repositoryRoot,
  ".opencode",
  "memory",
  "titan_store.json",
)

const legacyBefore =
  await optionalFile(legacyStorePath)

const serviceOptions = {
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
}

const context = {
  sessionID:
    "session_memory_tools_integration",
  messageID:
    "message_memory_tools_integration",
  agent: "integration_agent",
}

let service =
  new MemoriXService(serviceOptions)

try {
  console.log(
    "[1/6] Calling memory_store facade...",
  )

  const stored =
    await storeMemoryThroughMemoriX(
      service,
      {
        subject:
          "Facade retrieval contract",
        content:
          "memory_retrieve reads only human-validated Titan hot-site memories.",
        tags: [
          "architecture",
          "hot-only",
        ],
      },
      context,
    )

  assertCondition(
    stored.metadata.status ===
      "pending_review",
    `Unexpected store status: ${stored.metadata.status}`,
  )

  const candidateID =
    stored.metadata.candidateID

  assertCondition(
    candidateID,
    "memory_store did not create a pending candidate.",
  )

  console.log(
    "[2/6] Confirming pending memory is not retrieved...",
  )

  const beforeValidation =
    await retrieveMemoryThroughMemoriX(
      service,
      {
        query:
          "Facade retrieval contract",
      },
    )

  assertCondition(
    beforeValidation.metadata.results
      .length === 0,
    "An unvalidated candidate leaked into hot retrieval.",
  )

  await service.close()

  console.log(
    "[3/6] Human-validating the pending candidate...",
  )

  const reviewer = new MemoriXClient({
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

  await reviewer.connect()

  try {
    await reviewer.callTool(
      "memorix_validate_candidate",
      {
        candidate_id: candidateID,
        validated_by:
          "integration_human_reviewer",
        validation_reason:
          "Approved during the memory-tool facade integration test.",
      },
    )
  } finally {
    await reviewer.close()
  }

  console.log(
    "[4/6] Restarting service and retrieving validated memory...",
  )

  service = new MemoriXService(
    serviceOptions,
  )

  const afterValidation =
    await retrieveMemoryThroughMemoriX(
      service,
      {
        query:
          "Facade retrieval contract",
        tags: ["hot-only"],
      },
    )

  assertCondition(
    afterValidation.metadata.source ===
      "hot_site",
    "memory_retrieve did not use the hot site.",
  )

  assertCondition(
    afterValidation.metadata.results
      .length === 1,
    `Expected one validated result, received ${afterValidation.metadata.results.length}.`,
  )

  assertCondition(
    afterValidation.metadata.results[0]
      ?.subject ===
      "Facade retrieval contract",
    "The stored subject was not preserved.",
  )

  console.log(
    "[5/6] Verifying old JSON store was untouched...",
  )

  const legacyAfter =
    await optionalFile(legacyStorePath)

  assertCondition(
    legacyBefore === undefined
      ? legacyAfter === undefined
      : legacyAfter !== undefined &&
          legacyBefore.equals(
            legacyAfter,
          ),
    "The legacy titan_store.json file was modified.",
  )

  console.log(
    "[6/6] memory_store / memory_retrieve facades: OK",
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
    "Temporary memory-tool runtime removed.",
  )
}
