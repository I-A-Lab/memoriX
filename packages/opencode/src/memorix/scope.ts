export type MemoriXTrustedScope = {
  projectID?: string
  userID?: string
}

export type MemoriXTrustedScopeInput = {
  projectID?: unknown
  userID?: unknown
}

export function normalizeMemoriXScopeIdentifier(
  value: unknown,
): string | undefined {
  if (typeof value !== "string") return undefined

  const normalized = value.trim()
  return normalized.length > 0 ? normalized : undefined
}

export function resolveTrustedMemoriXScope(
  input: MemoriXTrustedScopeInput,
): MemoriXTrustedScope {
  const projectID = normalizeMemoriXScopeIdentifier(
    input.projectID,
  )
  const userID = normalizeMemoriXScopeIdentifier(
    input.userID,
  )

  return {
    ...(projectID ? { projectID } : {}),
    ...(userID ? { userID } : {}),
  }
}
