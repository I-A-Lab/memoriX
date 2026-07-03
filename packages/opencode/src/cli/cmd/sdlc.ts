import { Effect } from "effect"
import { effectCmd } from "../effect-cmd"
import type { Argv } from "yargs"
import path from "path"
import { RunCommand } from "./run"

export const SdlcCommand = effectCmd({
  command: "sdlc [message..]",
  describe: "run the autonomous SDLC dual-track agent pipeline",
  instance: () => true,
  directory: (args: any) => (args.dir ? path.resolve(process.cwd(), args.dir) : process.cwd()),
  builder: (yargs: Argv) =>
    yargs
      .positional("message", {
        describe: "task or problem statement for the SDLC architect",
        type: "string",
        array: true,
        default: [],
      })
      .option("dir", {
        type: "string",
        describe: "directory to run in",
      }),
  handler: Effect.fn("Cli.sdlc")(function* (args): Generator<any, any, any> {
    const runHandler = RunCommand.handler as any
    return yield* runHandler({
      ...args,
      agent: "sdlc",
      sdlc: true,
      command: undefined,
      continue: undefined,
      session: undefined,
      fork: undefined,
      share: undefined,
      model: undefined,
      format: "default",
      file: undefined,
      title: undefined,
      attach: undefined,
      password: undefined,
      username: undefined,
      port: undefined,
      variant: undefined,
      thinking: undefined,
      mini: false,
      replay: true,
      "replay-limit": undefined,
      replayLimit: undefined,
      "dangerously-skip-permissions": false,
      dangerouslySkipPermissions: false,
      demo: false,
    })
  }) as any,
})
