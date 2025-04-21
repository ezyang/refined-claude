import { EventType, eventWithTime, IncrementalSource } from 'rrweb';
import { serializedNodeWithId } from '@rrweb/types';
import { Window } from 'happy-dom';
import * as fs from 'fs';
import * as path from 'path';
import { Mirror, rebuild, createCache } from 'rrweb-snapshot';

// Define Node constants from DOM spec since they might not be available in test environment
const NODE_ELEMENT = 1;
const NODE_TEXT = 3;

/**
 * Loads an rrweb recording from a JSON file
 * @param filePath Path to the rrweb recording JSON file
 * @returns The parsed rrweb events
 */
export function loadRrwebRecording(filePath: string): eventWithTime[] {
  const fullPath = path.resolve(filePath);
  const fileContent = fs.readFileSync(fullPath, 'utf-8');
  const recording = JSON.parse(fileContent);
  return recording.events;
}

/**
 * Creates a virtual DOM environment using happy-dom
 * @returns A Window instance with a document
 */
export function createVirtualDom(): Window {
  const window = new Window({
    url: 'https://claude.ai',
    width: 1920,
    height: 1080
  });

  // Initialize with a basic HTML structure
  window.document.write('<!DOCTYPE html><html><head></head><body></body></html>');

  return window;
}

/**
 * Applies a snapshot event to the virtual DOM
 * @param window The happy-dom Window instance
 * @param event The rrweb snapshot event
 * @param mirror The mirror to track node mapping between calls
 * @param cache The cache for CSS processing
 */
export function applySnapshotToVirtualDom(
  window: Window,
  event: eventWithTime,
  mirror: Mirror,
  cache: any
): void {
  const document = window.document;

  if (event.type === EventType.FullSnapshot) {
    // Clear the existing document content
    document.documentElement.innerHTML = '';

    // Process the full snapshot data
    const { data } = event;

    // Get the correct root node from the snapshot
    try {
      // A full snapshot contains multiple properties, but rebuild() specifically needs the 'node' property
      // which is the serialized DOM tree with IDs for incremental patches
      const rootNode = data.node; // This is the serializedNodeWithId that rebuild expects

      // The snapshot data may also include:
      // - initialOffset (scrolling position)
      // - width/height (viewport dimensions)
      // But rebuild() specifically works with the DOM structure in the node property

      rebuild(rootNode, {
        doc: document as unknown as Document,
        mirror,
        hackCss: true, // Apply CSS hacks for better replay
        afterAppend: (node: Node, id: number) => {
          // Handle any post-append operations if needed
        },
        cache
      });
    } catch (error) {
      console.error('Error rebuilding DOM from snapshot:', error);
    }
  } else if (event.type === EventType.IncrementalSnapshot) {
    // Handle incremental snapshot
    const { data } = event;

    // Process different types of incremental updates
    if (data.source === IncrementalSource.Mutation) {
      // Handle DOM mutations
      if (Array.isArray(data.adds)) {
        for (const mutation of data.adds) {
          try {
            // Add new nodes
            const parentNode = mirror.getNode(mutation.parentId);
            if (parentNode) {
              const newNode = rebuild(mutation as unknown as serializedNodeWithId, {
                doc: document as unknown as Document,
                mirror,
                hackCss: true,
                afterAppend: (node: Node, id: number) => {
                  // Handle post-append operations
                },
                cache
              });

              if (newNode && mutation.nextId) {
                const nextNode = mirror.getNode(mutation.nextId);
                if (parentNode && nextNode) {
                  parentNode.insertBefore(newNode, nextNode);
                } else if (parentNode) {
                  parentNode.appendChild(newNode);
                }
              }
            }
          } catch (error) {
            console.error('Error processing mutation add:', error);
          }
        }
      }

      // Process attribute mutations
      if (Array.isArray(data.attributes)) {
        for (const mutation of data.attributes) {
          try {
            const node = mirror.getNode(mutation.id);
            if (node && node.nodeType === NODE_ELEMENT) {
              const element = node as Element;
              for (const [attributeName, attributeValue] of Object.entries(mutation.attributes)) {
                if (attributeValue === null) {
                  element.removeAttribute(attributeName);
                } else {
                  element.setAttribute(attributeName, attributeValue as string);
                }
              }
            }
          } catch (error) {
            console.error('Error processing attribute mutation:', error);
          }
        }
      }

      // Process text mutations
      if (Array.isArray(data.texts)) {
        for (const mutation of data.texts) {
          try {
            const node = mirror.getNode(mutation.id);
            if (node && node.nodeType === NODE_TEXT) {
              node.textContent = mutation.value;
            }
          } catch (error) {
            console.error('Error processing text mutation:', error);
          }
        }
      }

      // Process removals
      if (Array.isArray(data.removes)) {
        for (const mutation of data.removes) {
          try {
            const node = mirror.getNode(mutation.id);
            if (node && node.parentNode) {
              node.parentNode.removeChild(node);
              mirror.removeNodeFromMap(node);
            }
          } catch (error) {
            console.error('Error processing node removal:', error);
          }
        }
      }
    } else if (data.source === IncrementalSource.Scroll) {
      // Handle scroll events
      try {
        // Use type assertion to access id, x, and y properties
        const scrollData = data as unknown as { id: number; x: number; y: number };
        const node = mirror.getNode(scrollData.id);
        if (node && node.nodeType === NODE_ELEMENT) {
          const element = node as Element;
          if ('scrollTop' in element) {
            (element as HTMLElement).scrollTop = scrollData.y;
          }
          if ('scrollLeft' in element) {
            (element as HTMLElement).scrollLeft = scrollData.x;
          }
        } else if (scrollData.id === 0) {
          // Scrolling the document
          window.scrollTo(scrollData.x, scrollData.y);
        }
      } catch (error) {
        console.error('Error processing scroll:', error);
      }
    } else if (data.source === IncrementalSource.Input) {
      // Handle input events
      try {
        // Use type assertion to access id and input properties
        const inputData = data as unknown as { id: number; text?: string; isChecked?: boolean };
        const node = mirror.getNode(inputData.id);
        if (node && node.nodeType === NODE_ELEMENT) {
          const element = node as Element;
          if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA' || element.tagName === 'SELECT') {
            const inputElement = element as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;
            if (inputData.text !== undefined) {
              inputElement.value = inputData.text;
            }
            if (inputData.isChecked !== undefined && 'checked' in inputElement) {
              (inputElement as HTMLInputElement).checked = inputData.isChecked;
            }
          }
        }
      } catch (error) {
        console.error('Error processing input:', error);
      }
    }
  }
}

/**
 * Helper function to ensure the dialog element exists
 * @param document The document object
 */
function ensureDialogExists(document: any): void {
  if (!document.querySelector("dialog[name^='Allow tool from']")) {
    const dialog = document.createElement('dialog');
    dialog.setAttribute('name', 'Allow tool from sublime-claude');
    dialog.setAttribute('open', 'true');
    document.body.appendChild(dialog);
  }
}

/**
 * Processes an rrweb recording and returns the final DOM state along with match timestamps
 * @param events rrweb events to process
 * @param matcher Optional matcher to check when the condition first matches
 * @returns An object containing the document and match timestamps
 */
export function processRrwebRecording(events: eventWithTime[], matcher?: any): {
  document: any;
  firstMatchTimestamp: number | null;
  lastEventTimestamp: number | null;
} {
  const window = createVirtualDom();
  let firstMatchTimestamp: number | null = null;
  let lastEventTimestamp: number | null = null;

  // Create a mirror and cache that persist across all events
  const mirror = new Mirror();
  const cache = createCache();

  // Process snapshot events
  for (const event of events) {
    if (event.type === EventType.FullSnapshot || event.type === EventType.IncrementalSnapshot) {
      applySnapshotToVirtualDom(window, event, mirror, cache);
      lastEventTimestamp = event.timestamp;

      // If we have a matcher and we haven't found a match yet, check if this event causes a match
      if (matcher && firstMatchTimestamp === null && matcher.matches(window.document)) {
        firstMatchTimestamp = event.timestamp;
      }
    }
  }

  return {
    document: window.document,
    firstMatchTimestamp,
    lastEventTimestamp
  };
}
