declare namespace NodeJS {
  interface Process {
    argv: string[];
    env: Record<string, string | undefined>;
    exit(code?: number): never;
    cwd(): string;
  }
}

declare var process: NodeJS.Process;

interface NodeRequire {
  (id: string): any;
  resolve(id: string): string;
}

declare var require: NodeRequire;

declare module 'path' {
  export function resolve(...paths: string[]): string;
  export function join(...paths: string[]): string;
}

declare module 'fs/promises' {
  export function readFile(path: string, options: { encoding: string } | string): Promise<string>;
  export function readFile(path: string): Promise<Buffer>;
  export function writeFile(path: string, data: string | Uint8Array): Promise<void>;
  export function access(path: string): Promise<void>;
}

declare class Buffer extends Uint8Array {
  toString(encoding?: string): string;
  static from(data: string, encoding?: string): Buffer;
}
