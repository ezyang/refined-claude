import { loadRrwebRecording, processRrwebRecording } from '../utils';
import { PageStateMatcher } from '../matchers/pageStateMatcher';
import { getAllowToolDialogRule } from '../rules';
import * as path from 'path';
import { Window } from 'happy-dom';

describe('PageStateMatcher', () => {
  // Test the basic functionality of PageStateMatcher
  describe('basic functionality', () => {
    let document: Document;

    beforeEach(() => {
      // Create a simple document with happy-dom
      const window = new Window({
        url: 'https://claude.ai',
        width: 1024,
        height: 768
      });

      window.document.write(`
        <!DOCTYPE html>
        <html>
        <head></head>
        <body>
          <dialog name="Allow tool from sublime-claude" open>
            <h2>Allow tool from sublime-claude?</h2>
            <p>This tool may access your conversation.</p>
            <button>Allow</button>
            <button>Deny</button>
          </dialog>
        </body>
        </html>
      `);

      document = window.document;
    });

    test('matches when selector is present', () => {
      const matcher = new PageStateMatcher({
        css: ["dialog[name^='Allow tool from']"]
      });

      expect(matcher.matches(document)).toBe(true);
    });

    test('does not match when selector is absent', () => {
      const matcher = new PageStateMatcher({
        css: [".some-non-existent-class"]
      });

      expect(matcher.matches(document)).toBe(false);
    });
  });

  // Test with the actual rrweb recording
  describe('with rrweb recording', () => {
    let recordingDocument: Document;

    beforeAll(() => {
      // Load and process the rrweb recording
      const recordingPath = path.resolve(__dirname, '../../testdata/approve-tool.json');
      const events = loadRrwebRecording(recordingPath);
      recordingDocument = processRrwebRecording(events);
    });

    test('rule matches when dialog appears in recording', () => {
      // Get the rule we want to test
      const rule = getAllowToolDialogRule();

      // Extract the PageStateMatcher from the rule
      const matcher = rule.conditions[0] as PageStateMatcher;

      // Test if the matcher matches the document from the recording
      expect(matcher.matches(recordingDocument)).toBe(true);
    });
  });
});
