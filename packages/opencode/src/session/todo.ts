import { LayerNode } from "@opencode-ai/core/effect/layer-node"
import { SessionID } from "./schema"
import { Effect, Layer, Context } from "effect"
import { Database } from "@opencode-ai/core/database/database"
import { eq } from "drizzle-orm"
import { asc } from "drizzle-orm"
import { TodoTable, SdlcTable } from "@opencode-ai/core/session/sql"
import { EventV2Bridge } from "@/event-v2-bridge"
import { SessionTodo } from "@opencode-ai/schema/session-todo"
import fs from "fs/promises"
import path from "path"

export const Info = SessionTodo.Info
export type Info = SessionTodo.Info

export const Event = SessionTodo.Event

export interface Interface {
  readonly update: (input: { sessionID: SessionID; todos: ReadonlyArray<Info>; agent?: string }) => Effect.Effect<void>
  readonly get: (sessionID: SessionID, agent?: string) => Effect.Effect<Info[]>
  readonly syncToMarkdown: (filepath: string, todos: ReadonlyArray<Info>) => Effect.Effect<void>
  readonly parseFromMarkdown: (filepath: string) => Effect.Effect<Info[]>
}

export class Service extends Context.Service<Service, Interface>()("@opencode/SessionTodo") {}

const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    const events = yield* EventV2Bridge.Service
    const { db } = yield* Database.Service

    const update = Effect.fn("Todo.update")(function* (input: { sessionID: SessionID; todos: ReadonlyArray<Info>; agent?: string }) {
      const table = input.agent === "sdlc" ? SdlcTable : TodoTable
      yield* db
        .transaction((tx) =>
          Effect.gen(function* () {
            yield* tx.delete(table).where(eq(table.session_id, input.sessionID)).run()
            if (input.todos.length === 0) return
            yield* tx
              .insert(table)
              .values(
                input.todos.map((todo, position) => ({
                  session_id: input.sessionID,
                  content: todo.content,
                  status: todo.status,
                  priority: todo.priority,
                  position,
                })),
              )
              .run()
          }),
        )
        .pipe(Effect.orDie)
      yield* events.publish(Event.Updated, input)
    })

    const get = Effect.fn("Todo.get")(function* (sessionID: SessionID, agent?: string) {
      const table = agent === "sdlc" ? SdlcTable : TodoTable
      const rows = yield* db
        .select()
        .from(table)
        .where(eq(table.session_id, sessionID))
        .orderBy(asc(table.position))
        .all()
        .pipe(Effect.orDie)
      return rows.map((row) => ({
        content: row.content,
        status: row.status,
        priority: row.priority,
      }))
    })

    const syncToMarkdown = Effect.fn("Todo.syncToMarkdown")(function* (filepath: string, todos: ReadonlyArray<Info>) {
      yield* Effect.promise(async () => {
        const dir = path.dirname(filepath)
        await fs.mkdir(dir, { recursive: true })
        const lines = todos.map((t) => {
          const mark = t.status === "completed" ? "[x]" : t.status === "in_progress" ? "[/]" : "[ ]"
          return `- ${mark} ${t.content}`
        })
        await fs.writeFile(filepath, lines.join("\n") + "\n", "utf-8")
      }).pipe(Effect.orDie)
    })

    const parseFromMarkdown = Effect.fn("Todo.parseFromMarkdown")(function* (filepath: string) {
      return yield* Effect.promise(async () => {
        try {
          const content = await fs.readFile(filepath, "utf-8")
          const todos: Info[] = []
          for (const line of content.split("\n")) {
            const match = line.match(/^\s*-\s*\[([ x\/])\]\s*(.+)$/)
            if (match) {
              const status = match[1] === "x" ? "completed" : match[1] === "/" ? "in_progress" : "pending"
              todos.push({ content: match[2].trim(), status: status as any, priority: "normal" as any })
            }
          }
          return todos
        } catch {
          return []
        }
      }).pipe(Effect.orDie)
    })

    return Service.of({ update, get, syncToMarkdown, parseFromMarkdown })
  }),
)

export const node = LayerNode.make({ service: Service, layer: layer, deps: [EventV2Bridge.node, Database.node] })

export * as Todo from "./todo"
