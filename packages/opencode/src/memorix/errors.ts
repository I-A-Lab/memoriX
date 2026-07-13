export class MemoriXClientError extends Error {
  override readonly cause?: unknown

  constructor(message: string, options?: { cause?: unknown }) {
    super(message)
    this.name = "MemoriXClientError"
    this.cause = options?.cause
  }
}

export class MemoriXTimeoutError extends MemoriXClientError {
  readonly timeoutMs: number

  constructor(operation: string, timeoutMs: number) {
    super(`memoriX operation timed out: ${operation} (${timeoutMs} ms)`)
    this.name = "MemoriXTimeoutError"
    this.timeoutMs = timeoutMs
  }
}

export class MemoriXNotConnectedError extends MemoriXClientError {
  constructor() {
    super("memoriX MCP client is not connected.")
    this.name = "MemoriXNotConnectedError"
  }
}

export class MemoriXToolCallError extends MemoriXClientError {
  readonly toolName: string

  constructor(toolName: string, message: string) {
    super(`memoriX tool ${toolName} failed: ${message}`)
    this.name = "MemoriXToolCallError"
    this.toolName = toolName
  }
}
