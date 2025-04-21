import { describe, it, expect } from 'vitest';
import { greet } from './index';

describe('greet', () => {
  it('should return a greeting with the provided name', () => {
    expect(greet('World')).toBe('Hello, World!');
  });

  it('should throw an error if name is empty', () => {
    expect(() => greet('')).toThrow('Name is required');
  });
});
