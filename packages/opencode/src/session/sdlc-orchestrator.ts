import { LayerNode } from "@opencode-ai/core/effect/layer-node"
import { Effect, Context, Layer } from "effect"
import path from "path"
import fs from "fs/promises"
import { analyzeTestOutput, type BreakLogReport } from "./break-log"
import { Todo } from "./todo"
import { exec } from "child_process"
import { promisify } from "util"

const execAsync = promisify(exec)

export interface Interface {
  readonly runGate: (attempt?: number, maxAttempts?: number, testCommand?: string) => Effect.Effect<BreakLogReport>
  readonly executePipeline: (
    prompt: string,
    maxAttempts?: number,
    testCommand?: string,
  ) => Effect.Effect<{ status: "END" | "FAILED"; attempts: number; lastLog: BreakLogReport }>
}

export class Service extends Context.Service<Service, Interface>()("@opencode/SdlcOrchestrator") {}

export const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    const todo = yield* Todo.Service

    const runGate = Effect.fn("SdlcOrchestrator.runGate")(function* (
      attempt: number = 1,
      maxAttempts: number = 5,
      testCommand: string = "bun test",
    ) {
      return yield* Effect.promise(async () => {
        try {
          const { stdout, stderr } = await execAsync(testCommand)
          return analyzeTestOutput(stdout || "", stderr || "", 0, attempt, maxAttempts)
        } catch (err: any) {
          const stdout = err.stdout || ""
          const stderr = err.stderr || err.message || ""
          const exitCode = err.code || 1
          return analyzeTestOutput(stdout, stderr, exitCode, attempt, maxAttempts)
        }
      }).pipe(Effect.orDie)
    })

    const executePipeline = Effect.fn("SdlcOrchestrator.executePipeline")(function* (
      prompt: string,
      maxAttempts: number = 5,
      testCommand: string = "bun test",
    ) {
      let attempt = 1
      let lastLog: BreakLogReport | undefined

      const prdDir = path.join(".opencode", "specs")
      const plansDir = path.join(".opencode", "plans")
      yield* Effect.promise(() => fs.mkdir(prdDir, { recursive: true })).pipe(Effect.orDie)
      yield* Effect.promise(() => fs.mkdir(plansDir, { recursive: true })).pipe(Effect.orDie)

      while (attempt <= maxAttempts) {
        lastLog = yield* runGate(attempt, maxAttempts, testCommand)

        if (lastLog.passed) {
          return { status: "END" as const, attempts: attempt, lastLog }
        }

        if (!lastLog.canRetry) {
          return { status: "FAILED" as const, attempts: attempt, lastLog }
        }

        attempt++
      }

      return {
        status: "FAILED" as const,
        attempts: attempt - 1,
        lastLog: lastLog || analyzeTestOutput("", "Unknown error", 1, attempt, maxAttempts),
      }
    })

    return Service.of({ runGate, executePipeline })
  }),
)

export const node = LayerNode.make({
  service: Service,
  layer: layer,
  deps: [Todo.node],
})

export * as SdlcOrchestrator from "./sdlc-orchestrator"
