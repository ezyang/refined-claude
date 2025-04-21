/**
 * Returns a greeting message for the given name
 * @param name - The name to greet
 * @returns A greeting string
 */
export function greet(name: string): string {
  if (!name) {
    throw new Error('Name is required');
  }
  return `Hello, ${name}!`;
}
