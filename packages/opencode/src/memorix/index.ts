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
  MemoriXRecordedEvent,
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
