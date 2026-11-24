import { spawn, type ChildProcess } from "child_process";
import fs from "fs";
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

export interface DesktopCredentials {
  sessionToken: string;
  sessionId: string;
  deviceToken: string;
  tmTokenId: string;
  userId: string;
  displayName: string | null;
  email: string | null;
}

export interface DesktopAuthStatus {
  signedIn: boolean;
  userId: string | null;
  displayName: string | null;
  email: string | null;
  hasDeviceToken: boolean;
}

export class TokenStore {
  private blob: Buffer | null = null;
  private credsBlob: Buffer | null = null;
  private cachedMeta: Omit<DesktopAuthStatus, "signedIn" | "hasDeviceToken"> | null = null;

  constructor(
    private readonly vault: TokenVault,
    private readonly log: HookLog,
    private readonly storagePath: string | null = null,
  ) {}

  save(token: string): void {
    if (!this.vault.isEncryptionAvailable()) {
      throw new Error("safeStorage encryption is unavailable");
    }
    this.blob = this.vault.encryptString(token);
    this.log.info("token stored (ciphertext only)");
  }

  saveCredentials(creds: DesktopCredentials): void {
    if (!this.vault.isEncryptionAvailable()) {
      throw new Error("safeStorage encryption is unavailable");
    }
    const serialized = JSON.stringify(creds);
    this.credsBlob = this.vault.encryptString(serialized);
    this.blob = this.vault.encryptString(creds.deviceToken);
    this.cachedMeta = {
      userId: creds.userId,
      displayName: creds.displayName,
      email: creds.email,
    };
    if (this.storagePath) {
      fs.mkdirSync(path.dirname(this.storagePath), { recursive: true });
      fs.writeFileSync(this.storagePath, this.credsBlob, { mode: 0o600 });
    }
    this.log.info("desktop credentials stored (safeStorage ciphertext only)");
  }

  loadFromDisk(): boolean {
    if (!this.storagePath || !fs.existsSync(this.storagePath)) return false;
    if (!this.vault.isEncryptionAvailable()) return false;
    try {
      const raw = fs.readFileSync(this.storagePath);
      const parsed = JSON.parse(this.vault.decryptString(raw)) as DesktopCredentials;
      if (!parsed.sessionToken || !parsed.deviceToken || !parsed.userId) return false;
      this.credsBlob = raw;
      this.blob = this.vault.encryptString(parsed.deviceToken);
      this.cachedMeta = {
        userId: parsed.userId,
        displayName: parsed.displayName ?? null,
        email: parsed.email ?? null,
      };
      return true;
    } catch {
      return false;
    }
  }

  clear(): void {
    this.blob = null;
    this.credsBlob = null;
    this.cachedMeta = null;
    if (this.storagePath && fs.existsSync(this.storagePath)) {
      try {
        fs.unlinkSync(this.storagePath);
      } catch {
        // Ignore unlink errors.
      }
    }
    this.log.info("desktop credentials cleared");
  }

  status(): { stored: boolean; masked: string | null; encryptionAvailable: boolean } {
    return {
      stored: this.blob !== null,
      masked: this.blob ? "••••••••" : null,
      encryptionAvailable: this.vault.isEncryptionAvailable(),
    };
  }

  authStatus(): DesktopAuthStatus {
    return {
      signedIn: this.credsBlob !== null && this.cachedMeta !== null,
      userId: this.cachedMeta?.userId ?? null,
      displayName: this.cachedMeta?.displayName ?? null,
      email: this.cachedMeta?.email ?? null,
      hasDeviceToken: this.blob !== null,
    };
  }

  /** Decrypts only for the callback that builds the worker argv. Callers must not log the value. */
  withToken<T>(use: (token: string) => T): T {
    if (!this.blob) throw new Error("owner-device token is not stored");
    return use(this.vault.decryptString(this.blob));
  }

  /** Decrypts stored credentials strictly within the callback scope. Callers must not log tokens. */
  withCredentials<T>(use: (creds: DesktopCredentials) => T): T {
    if (!this.credsBlob) throw new Error("Sign-in required");
    const parsed = JSON.parse(this.vault.decryptString(this.credsBlob)) as DesktopCredentials;
    return use(parsed);
  }
}
