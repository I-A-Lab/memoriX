import { defineConfig } from "drizzle-kit"

export default defineConfig({
  dialect: "sqlite",
  schema: ["./src/**/*.sql.ts", "./src/**/sql.ts"],
  out: "./migration",
  dbCredentials: {
    url: "C:/Users/anttn/.local/share/opencode/opencode-antoine.db", // ou opencode.db / opencode-local.db
  },
})
