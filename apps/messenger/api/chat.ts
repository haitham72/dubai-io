// POST /api/chat {messages:[{role,text}]} → {text, action?}. OpenAI with intent tools (ported from server/server.py).
import { body, env, fail, isLuna, json, openai, route, type ChatCompletion } from "../lib/http.js";

const dubaiDay = (d: Date) =>
  `${d.toLocaleDateString("en-US", { weekday: "long", timeZone: "Asia/Dubai" })} ${d.toLocaleDateString("en-CA", { timeZone: "Asia/Dubai" })}`;
/** Spelled-out calendar so "next Friday" / "tomorrow" resolve correctly (small models are bad at date math). */
const nextWeek = (today: Date) =>
  Array.from({ length: 8 }, (_, i) => dubaiDay(new Date(today.getTime() + (i + 1) * 86_400_000))).join(", ");

const SYSTEM_PROMPT = (today: Date) =>
  "You are Messenger AI, a concise and friendly assistant inside the Messenger chat app. " +
  `Today is ${dubaiDay(today)} (Dubai). The coming days are: ${nextWeek(today)}. "Next <weekday>" means the first such day in that list. ` +
  "Use the tools when the user asks for an image, a video, flights, research, or weather; otherwise answer directly in plain markdown. " +
  "When the user asks to make, create or generate a video, reel or clip, call generate_video (never generate_image). " +
  "Convert city names to IATA codes and relative dates like 'next Friday' to YYYY-MM-DD dates yourself. " +
  "Always reply in the language of the user's latest message: English in, English out; Arabic in, Arabic out.";

const TOOLS = [
  { type: "function", function: { name: "generate_image", description: "Generate an image with the Higgs image model.", parameters: { type: "object", properties: { prompt: { type: "string" } }, required: ["prompt"] } } },
  { type: "function", function: { name: "generate_video", description: "Create a short video, reel or clip from a text description. Use this for any request to make, create or generate a video, reel or clip — never generate_image for those.", parameters: { type: "object", properties: { prompt: { type: "string" } }, required: ["prompt"] } } },
  {
    type: "function", function: {
      name: "search_flights", description: "Search flights between two airports.",
      parameters: {
        type: "object",
        properties: {
          from: { type: "string", description: "Origin IATA code" }, to: { type: "string", description: "Destination IATA code" },
          depart: { type: "string", description: "Outbound date YYYY-MM-DD" }, return: { type: "string", description: "Return date YYYY-MM-DD" },
          passengers: { type: "integer" }, cabin: { type: "string", enum: ["economy", "business", "first"] },
        },
        required: ["from", "to", "depart"],
      },
    },
  },
  { type: "function", function: { name: "research_topic", description: "Research a topic on the web and write a short brief with key findings. Use for 'research', 'look into', 'what's the latest on', market/industry questions.", parameters: { type: "object", properties: { topic: { type: "string" } }, required: ["topic"] } } },
  { type: "function", function: { name: "get_weather", description: "Get the current weather for a city (frontend fetches Open-Meteo).", parameters: { type: "object", properties: { city: { type: "string" } }, required: ["city"] } } },
];

export const POST = route(async (req) => {
  const { messages } = await body<{ messages?: { role: string; text: string }[] }>(req);
  if (!messages?.length) return fail(400, "messages is required");
  const model = env("OPENAI_MODEL", "gpt-4o-mini");
  const resp = await openai<ChatCompletion>("chat/completions", {
    model,
    messages: [
      { role: "system", content: SYSTEM_PROMPT(new Date()) },
      ...messages.map((m) => ({ role: ["user", "assistant", "system"].includes(m.role) ? m.role : "user", content: m.text })),
    ],
    tools: TOOLS, tool_choice: "auto",
    ...(isLuna(model) ? { reasoning_effort: "none" } : {}),
  });
  const msg = resp.choices[0]?.message;
  const call = msg?.tool_calls?.[0];
  if (call) {
    let args: Record<string, unknown> = {};
    try { args = JSON.parse(call.function.arguments || "{}"); } catch { /* unusable args → text */ }
    const name = call.function.name;
    if (name === "generate_image" && args.prompt) return json({ text: "On it — generating your image. I'll post it in Messenger Updates.", action: { type: "image", prompt: String(args.prompt) } });
    if (name === "generate_video" && args.prompt) return json({ text: "On it — creating your video. I'll post it in Messenger Updates.", action: { type: "video", prompt: String(args.prompt) } });
    if (name === "search_flights" && args.from && args.to && args.depart) {
      const cabin = ["economy", "business", "first"].includes(String(args.cabin)) ? String(args.cabin) : "economy";
      const query = {
        from: String(args.from).toUpperCase(), to: String(args.to).toUpperCase(), depart: String(args.depart),
        passengers: Number(args.passengers) || 1, cabin, ...(args.return ? { return: String(args.return) } : {}),
      };
      return json({ text: `On it — searching flights ${query.from} → ${query.to}.`, action: { type: "flight", query } });
    }
    if (name === "research_topic" && args.topic) return json({ text: "On it — researching that now. I'll post the brief in Messenger Updates.", action: { type: "research", topic: String(args.topic) } });
    if (name === "get_weather" && args.city) return json({ text: `Here's the weather in ${args.city}.`, action: { type: "weather", city: String(args.city) } });
  }
  return json({ text: msg?.content ?? "" });
});
