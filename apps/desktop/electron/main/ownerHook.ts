import { spawn, type ChildProcess } from "child_process";
import path from "path";

export interface HookStart {
  model: string;
  token: string;
  url: string;
  owner: string;
}

export interface HookLog {
  info(line: string): void;
}

export interface SpawnFn {
  (command: string, args: string[], options: { cwd?: string; windowsHide?: boolean; env?: NodeJS.ProcessEnv }): ChildProcess;
}

export function workerScript(fromDir = __dirname): string {
  return path.resolve(fromDir, "../../../memory/hooks/agent_worker.py");
}

export function workerArgs(scriptPath: string, input: HookStart): string[] {
  if (!input.model.trim()) throw new Error("model is required");
  if (!input.token.trim()) throw new Error("token is required");
  if (!/^https?:\/\//.test(input.url)) throw new Error("url must be http(s)");
  return [
    scriptPath,
    "--model",
    input.model,
    "--token",
    input.token,
    "--url",
    input.url,
    "--owner",
    input.owner,
    "--runner",
    "owner-hook",
  ];
}

export function redactArgs(args: string[]): string[] {
  const copy = [...args];
  const index = copy.indexOf("--token");
  if (index >= 0 && index + 1 < copy.length) copy[index + 1] = "[redacted]";
  return copy;
}

export class OwnerHook {
  private child: ChildProcess | null = null;
  private model: string | null = null;

  constructor(
    private readonly log: HookLog,
    private readonly spawnFn: SpawnFn = spawn,
    private readonly python = process.env.TM_PYTHON ?? "python",
    private readonly scriptPath = workerScript(),
  ) {}

  status(): { running: boolean; model: string | null } {
    return { running: this.child !== null && this.child.exitCode === null && !this.child.killed, model: this.model };
  }

  start(input: HookStart): { running: boolean; model: string } {
    if (this.status().running) this.stop();
    const args = workerArgs(this.scriptPath, input);
    this.log.info(`owner-hook start ${redactArgs([this.python, ...args]).join(" ")}`);
    this.child = this.spawnFn(this.python, args, { windowsHide: true });
    this.model = input.model;
    return { running: true, model: input.model };
  }

  stop(): { running: false } {
    if (this.child && this.child.exitCode === null && !this.child.killed) {
      this.child.kill();
    }
    this.child = null;
    this.model = null;
    this.log.info("owner-hook stop");
    return { running: false };
  }
}

export interface TokenVault {
  isEncryptionAvailable(): boolean;
  encryptString(value: string): Buffer;
  decryptString(value: Buffer): string;
}

export class TokenStore {
  private blob: Buffer | null = null;

  constructor(private readonly vault: TokenVault, private readonly log: HookLog) {}

  save(token: string): void {
    if (!this.vault.isEncryptionAvailable()) {
      throw new Error("safeStorage encryption is unavailable");
    }
    this.blob = this.vault.encryptString(token);
    this.log.info("token stored (ciphertext only)");
  }

  status(): { stored: boolean; masked: string | null; encryptionAvailable: boolean } {
    return {
      stored: this.blob !== null,
      masked: this.blob ? "••••••••" : null,
      encryptionAvailable: this.vault.isEncryptionAvailable(),
    };
  }

  /** Decrypts only for the callback that builds the worker argv. Callers must not log the value. */
  withToken<T>(use: (token: string) => T): T {
    if (!this.blob) throw new Error("owner-device token is not stored");
    return use(this.vault.decryptString(this.blob));
  }
}
