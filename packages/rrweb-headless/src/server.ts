import * as http from 'http';
import { AddressInfo } from 'net';

/**
 * Creates a simple HTTP server to serve replay content
 * This ensures content scripts can be properly injected (unlike with data: URLs)
 */
export async function createReplayServer(): Promise<{
  server: http.Server;
  port: number;
  serveContent: (content: string) => void;
  close: () => Promise<void>;
}> {
  let currentContent = '';

  // Create the server
  const server = http.createServer((req, res) => {
    res.writeHead(200, {
      'Content-Type': 'text/html',
      'Access-Control-Allow-Origin': '*',
    });
    res.end(currentContent);
  });

  // Start the server on a random available port
  await new Promise<void>(resolve => {
    server.listen(0, '127.0.0.1', () => {
      resolve();
    });
  });

  // Get the assigned port
  const port = (server.address() as AddressInfo).port;

  console.log(`[DRIVER] Replay server started on http://localhost:${port}`);

  return {
    server,
    port,
    serveContent: (content: string) => {
      currentContent = content;
    },
    close: () => {
      return new Promise<void>((resolve, reject) => {
        server.close(err => {
          if (err) {
            reject(err);
          } else {
            resolve();
          }
        });
      });
    },
  };
}
