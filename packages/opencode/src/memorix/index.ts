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

export type {
  JSONObject,
  JSONPrimitive,
  JSONValue,
  MemoriXClientOptions,
  MemoriXRecordEventInput,
  MemoriXRetrievalMatch,
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
