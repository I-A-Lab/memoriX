import { Effect } from "effect"
import type { DatabaseMigration } from "../migration"

export default {
  id: "20260720063037_add_sdlc_table",
  up(tx) {
    return Effect.gen(function* () {
      yield* tx.run(`
        CREATE TABLE \`sdlc\` (
          \`session_id\` text NOT NULL,
          \`content\` text NOT NULL,
          \`status\` text NOT NULL,
          \`priority\` text NOT NULL,
          \`position\` integer NOT NULL,
          \`time_created\` integer NOT NULL,
          \`time_updated\` integer NOT NULL,
          CONSTRAINT \`sdlc_pk\` PRIMARY KEY(\`session_id\`, \`position\`),
          CONSTRAINT \`fk_sdlc_session_id_session_id_fk\` FOREIGN KEY (\`session_id\`) REFERENCES \`session\`(\`id\`) ON DELETE CASCADE
        );
      `)
      yield* tx.run(`CREATE INDEX \`sdlc_session_idx\` ON \`sdlc\` (\`session_id\`);`)
    })
  },
} satisfies DatabaseMigration.Migration
