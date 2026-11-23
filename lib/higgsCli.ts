// Higgsfield CLI bridge for the LOCAL dev server only (the CLI is logged in on this machine; Vercel can't run it).
// Used for real image edits (Nano Banana 2 image-to-image) when no Higgs API keys are configured.
// Every call that creates a job costs credits — only explicit user edits reach this.
declare const process: { env: Record<string, string | undefined>; platform: string; execPath: string };

type ExecFile = (cmd: string, args: string[], opts: { timeout: number; shell?: boolean; maxBuffer?: number }, cb: (err: Error | null, stdout: string, stderr: string) => void) => void;

async function node() {
  const cp = (await import("node:child_process" as string)) as { execFile: ExecFile };
  const fs = (await import("node:fs/promises" as string)) as { writeFile: (p: string, d: Uint8Array) => Promise<void>; mkdtemp: (p: string) => Promise<string> };
  const os = (await import("node:os" as string)) as { tmpdir: () => string };
  const path = (await import("node:path" as string)) as { join: (...p: string[]) => string };
  return { cp, fs, os, path };
}

/** The CLI exists only where we run the dev server (never on Vercel). */
export const cliAvailable = () => !process.env.VERCEL && process.env.MIRSAL_HIGGS_CLI !== "0";

async function higgs(args: string[]): Promise<unknown> {
  const { cp, path } = await node();
  // Windows: the npm shim (higgsfield.cmd) needs a shell, which would split the prompt on spaces — run its script with
  // Node directly instead. Elsewhere the `higgsfield` binary is on PATH.
  const [cmd, base] = process.platform === "win32"
    ? [process.execPath, [process.env.HIGGSFIELD_JS ?? path.join(process.env.APPDATA ?? "", "npm", "node_modules", "@higgsfield", "cli", "bin", "higgsfield.js")]]
    : ["higgsfield", [] as string[]];
  const out = await new Promise<string>((resolve, reject) =>
    cp.execFile(cmd, [...base, ...args, "--json"], { timeout: 120_000, maxBuffer: 4 * 1024 * 1024 },
      (err, stdout, stderr) => (err ? reject(new Error((stderr || err.message).trim().slice(0, 200))) : resolve(stdout))));
  return JSON.parse(out);
}

type Job = { id?: string; status?: string; result_url?: string; error?: string };
const first = (data: unknown): Job => (Array.isArray(data) ? data[0] : data) as Job ?? {};

/** Start an image edit: the original image (URL) as reference + the edit prompt. Returns the CLI job id. */
export async function cliStartEdit(imageUrl: string, prompt: string, model = "nano_banana_flash"): Promise<string> {
  const { fs, os, path } = await node();
  const res = await fetch(imageUrl);
  if (!res.ok) throw new Error(`Couldn't fetch the original image (${res.status})`);
  const type = res.headers.get("content-type") ?? "image/jpeg";
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "mirsal-edit-"));
  const file = path.join(dir, `original.${type.includes("png") ? "png" : type.includes("webp") ? "webp" : "jpg"}`);
  await fs.writeFile(file, new Uint8Array(await res.arrayBuffer()));
  const job = first(await higgs(["generate", "create", model, "--prompt", prompt, "--image-references", file, "--resolution", "1k"]));
  if (!job.id) throw new Error("Higgsfield returned no job id");
  return job.id;
}

/** Poll a CLI job → running / completed with URL / failed. */
export async function cliJob(id: string): Promise<{ status: "running" | "completed" | "failed"; url?: string; error?: string }> {
  const job = first(await higgs(["generate", "get", id]));
  const status = (job.status ?? "").toLowerCase();
  if (status === "completed" && job.result_url) return { status: "completed", url: job.result_url };
  if (["failed", "nsfw", "canceled", "cancelled", "error"].includes(status)) return { status: "failed", error: job.error ?? `Higgsfield: ${status}` };
  return { status: "running" };
}
