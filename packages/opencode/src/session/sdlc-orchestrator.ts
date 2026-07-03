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
  readonly runGate: (attempt?: number, maxAttempts?: number) => Effect.Effect<BreakLogReport>
  readonly executePipeline: (prompt: string, maxAttempts?: number) => Effect.Effect<{ status: "END" | "FAILED"; attempts: number; lastLog: BreakLogReport }>
}

export class Service extends Context.Service<Service, Interface>()("@opencode/SdlcOrchestrator") {}

export const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    const todo = yield* Todo.Service

    const runGate = Effect.fn("SdlcOrchestrator.runGate")(function* (attempt: number = 1, maxAttempts: number = 5) {
      return yield* Effect.promise(async () => {
        try {
          const { stdout, stderr } = await execAsync("bun test")
          return analyzeTestOutput(stdout || "", stderr || "", 0, attempt, maxAttempts)
        } catch (err: any) {
          const stdout = err.stdout || ""
          const stderr = err.stderr || err.message || ""
          const exitCode = err.code || 1
          return analyzeTestOutput(stdout, stderr, exitCode, attempt, maxAttempts)
        }
      }).pipe(Effect.orDie)
    })

    const executePipeline = Effect.fn("SdlcOrchestrator.executePipeline")(function* (prompt: string, maxAttempts: number = 5) {
      let attempt = 1
      let lastLog: BreakLogReport | undefined

      while (attempt <= maxAttempts) {
        const prdDir = path.join(".opencode", "specs")
        yield* Effect.promise(() => fs.mkdir(prdDir, { recursive: true })).pipe(Effect.orDie)

        const devPlan = path.join(".opencode", "plans", "dev_plan.md")
        const testPlan = path.join(".opencode", "plans", "test_plan.md")
        yield* Effect.all([
          todo.syncToMarkdown(devPlan, []),
          todo.syncToMarkdown(testPlan, []),
        ], { concurrency: "unbounded" })

        lastLog = yield* runGate(attempt, maxAttempts)

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
