/**
 * Global type definitions for window extensions
 */

import { findAndClickAllowButton, setupModalObserver } from './modalObserver';

declare global {
  interface Window {
    findAndClickAllowButton: typeof findAndClickAllowButton;
    setupModalObserver: typeof setupModalObserver;
  }
}

// This is a module declaration file, so we need an export to make TypeScript treat it as a module
export {};
