import type {
  Hooks,
  Plugin,
} from "@opencode-ai/plugin"

import {
  getDefaultMemoriXService,
  memoriXHookOptionsFromEnvironment,
  recordToolResultHook,
  recordUserMessageHook,
  resetDefaultMemoriXService,
} from "../../packages/opencode/src/memorix"

function textFromParts(
  parts: Array<{
    type: string
    text?: string
    synthetic?: boolean
    ignored?: boolean
  }>,
): string {
  return parts
    .filter(
      (part) =>
        part.type === "text" &&
        typeof part.text === "string" &&
        !part.synthetic &&
        !part.ignored,
    )
    .map((part) => part.text?.trim())
    .filter(
      (text): text is string =>
        Boolean(text),
    )
    .join("\n\n")
}

const MemoriXPlugin: Plugin = async () => {
  const service =
    getDefaultMemoriXService()

  const options =
    memoriXHookOptionsFromEnvironment()

  const hooks: Hooks = {
    async "chat.message"(input, output) {
      try {
        const text = textFromParts(
          output.parts,
        )

        await recordUserMessageHook(
          service,
          options,
          {
            sessionID: input.sessionID,
            messageID: input.messageID,
            agent: input.agent,
            model: input.model,
            variant: input.variant,
            text,
          },
        )
      } catch {
        // memoriX hooks must never interrupt OpenCode.
      }
    },

    async "tool.execute.after"(
      input,
      output,
    ) {
      try {
        await recordToolResultHook(
          service,
          options,
          {
            sessionID: input.sessionID,
            callID: input.callID,
            tool: input.tool,
            args: input.args,
            title: output.title,
            output: output.output,
            metadata: output.metadata,
          },
        )
      } catch {
        // memoriX hooks must never interrupt OpenCode.
      }
    },

    async dispose() {
      await resetDefaultMemoriXService()
    },
  }

  return hooks
}

export default MemoriXPlugin
