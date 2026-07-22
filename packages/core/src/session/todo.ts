export * as SessionTodo from "./todo"

import { asc, eq } from "drizzle-orm"
import { Context, Effect, Layer } from "effect"
import { SessionTodo } from "@opencode-ai/schema/session-todo"
import { Database } from "../database/database"
import { makeLocationNode } from "../effect/app-node"
import { EventV2 } from "../event"
import { SessionSchema } from "./schema"
import { TodoTable, SdlcTable } from "./sql"

export const Info = SessionTodo.Info
export type Info = typeof Info.Type
export const Event = SessionTodo.Event

export interface Interface {
  readonly update: (input: {
    readonly sessionID: SessionSchema.ID
    readonly todos: ReadonlyArray<Info>
    readonly agent?: string
  }) => Effect.Effect<void>
  readonly get: (sessionID: SessionSchema.ID, agent?: string) => Effect.Effect<ReadonlyArray<Info>>
}

export class Service extends Context.Service<Service, Interface>()("@opencode/v2/SessionTodo") {}

export const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    const { db } = yield* Database.Service
    const events = yield* EventV2.Service

    const update = Effect.fn("SessionTodo.update")(function* (input: {
      readonly sessionID: SessionSchema.ID
      readonly todos: ReadonlyArray<Info>
      readonly agent?: string
    }) {
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

    const get = Effect.fn("SessionTodo.get")(function* (sessionID: SessionSchema.ID, agent?: string) {
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

    return Service.of({ update, get })
  }),
)

export const defaultLayer = layer.pipe(Layer.provide(EventV2.defaultLayer), Layer.provide(Database.defaultLayer))

export const node = makeLocationNode({ service: Service, layer, deps: [EventV2.node, Database.node] })
