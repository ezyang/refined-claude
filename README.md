# Refined Claude Extension

This Chrome extension adds the following enhancements to claude.ai:

1. Triggers a notification when Claude has finished responding.  Also, the
   favicon changes grey while generation is happening, and then has a red dot
   when it is done, indicating you should check the window.
2. Auto-click "Continue" when it occurs (can be disabled)

## Known bugs

- Auto-click for "Continue" occurs even if you merely navigate onto a page
  that has a Continue on it.

- We will indefinitely click "Continue" if you hit the message limit and are
  simultaneously rate limited.

- When you start a fresh chat from the main screen, we don't seem to properly
  change the favicon to indicate we are generating.

- There is some code for auto-approve tool use but it's broken right now, and
  difficult for me to test as Anthropic as (temporarily?) opted into some flow
  where tool approvals persist across chats.

### Development Workflow

To build the extension:

```bash
pnpm build
```

Then load the `dist` directory as an unpacked extension in Chrome.

## Testing

Run tests with:

```bash
pnpm test
```

The tests replay rrweb recordings of claude.ai with the extension loaded and verify that
the extension triggers appropriately, so they take a bit of time to run.
