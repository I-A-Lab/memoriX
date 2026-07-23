
import type { MemoriXService } from "./service"
import type { JSONObject } from "./types"
export type TopicBlocksFacadeService = Pick<MemoriXService, "topicBlocks">
export type TopicBlocksFacadeResult = { title: string; output: string; metadata: { operation: string; ok: boolean; report?: JSONObject; failure?: { code: string; message: string } } }
export async function runTopicBlocks(service: TopicBlocksFacadeService, input: JSONObject): Promise<TopicBlocksFacadeResult> {
  const value = await service.topicBlocks(input)
  if (!value.ok) return { title: "memoriX topic blocks", output: value.message, metadata: { operation: "topic_blocks", ok: false, failure: { code: value.code, message: value.message } } }
  return { title: "memoriX topic blocks", output: JSON.stringify(value.value, null, 2), metadata: { operation: "topic_blocks", ok: true, report: value.value } }
}
