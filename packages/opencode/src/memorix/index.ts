export { getRetentionRankingStatus, inspectRetentionRanking } from "./retention-ranking-facade"
export type { RetentionRankingFacadeService, RetentionRankingFacadeResult } from "./retention-ranking-facade"
export { getMemoryPressureStatus, inspectMemoryPressure } from "./memory-pressure-facade"
export type { MemoryPressureFacadeService, MemoryPressureFacadeResult } from "./memory-pressure-facade"
export { getCapacityStatus, planCapacityPruning, pruneCapacity } from "./capacity-facade"
export type { CapacityFacadeService, CapacityFacadeResult } from "./capacity-facade"
export {
  getProjectSnapshotThroughMemoriX,
  listProjectEntriesThroughMemoriX,
  rebuildProjectSnapshotThroughMemoriX,
  recordProjectEntryThroughMemoriX,
} from "./project-archive-facade"

export type {
  ProjectArchiveFacadeMetadata,
  ProjectArchiveFacadeResult,
  ProjectArchiveFacadeService,
} from "./project-archive-facade"

export {
  getMemoriXStatus,
  listCandidatesThroughMemoriX,
  rejectCandidateThroughMemoriX,
  runConsolidationThroughMemoriX,
  runNightlyThroughMemoriX,
  validateCandidateThroughMemoriX,
} from "./candidate-facade"

export type {
  CandidateFacadeFailure,
  CandidateFacadeMetadata,
  CandidateFacadeResult,
  CandidateFacadeService,
} from "./candidate-facade"
export { MemoriXClient } from "./client"

export {
  MemoriXClientError,
  MemoriXConfigurationError,
  MemoriXDisabledError,
  MemoriXNotConnectedError,
  MemoriXTimeoutError,
  MemoriXToolCallError,
} from "./errors"

export {
  MemoriXService,
  getDefaultMemoriXService,
  memoriXServiceOptionsFromEnvironment,
  resetDefaultMemoriXService,
} from "./service"

export {
  memoriXHookOptionsFromEnvironment,
  recordToolResultHook,
  recordUserMessageHook,
} from "./hooks"

export type {
  MemoriXHookService,
  MemoriXToolResultHookInput,
  MemoriXUserMessageHookInput,
} from "./hooks"

export type {
  MemoriXClientContract,
  MemoriXClientFactory,
  MemoriXServiceDependencies,
} from "./service"

export {
  retrieveMemoryThroughMemoriX,
  storeMemoryThroughMemoriX,
} from "./memory-facade"

export type {
  MemoryFacadeContext,
  MemoryFacadeResult,
  MemoryFacadeService,
  MemoryFact,
  MemoryRetrieveFacadeInput,
  MemoryRetrieveFacadeMetadata,
  MemoryStoreFacadeInput,
  MemoryStoreFacadeMetadata,
  MemoryStoreStatus,
} from "./memory-facade"

export type {
  JSONObject,
  JSONPrimitive,
  JSONValue,
  MemoriXArchivedEvent,
  MemoriXCandidate,
  MemoriXCandidateStatus,
  MemoriXClientOptions,
  MemoriXProposeCandidateInput,
  MemoriXProjectArchiveEntry,
  MemoriXProjectArchiveEntryType,
  MemoriXProjectEntryRecordInput,
  MemoriXProjectSnapshot,
  MemoriXRecordedEvent,
  MemoriXHookEnvironment,
  MemoriXHookOptions,
  MemoriXHookOutcome,
  MemoriXRecordEventInput,
  MemoriXRetrievalMatch,
  MemoriXStoredEvent,
  MemoriXRetrievalResult,
  MemoriXServiceEnvironment,
  MemoriXServiceErrorCode,
  MemoriXServiceFailure,
  MemoriXServiceOptions,
  MemoriXServiceResult,
  MemoriXServiceSuccess,
  MemoriXStatus,
  MemoriXToolCallResult,
  MemoriXToolDefinition,
  MemoriXToolName,
} from "./types"
