# @sublime-claude/utils

Utility functions for the sublime-claude project.

## Usage

```typescript
import { greet } from '@sublime-claude/utils';

const message = greet('World');
console.log(message); // Outputs: "Hello, World!"
```

## Functions

### greet

Returns a greeting message for the given name.

```typescript
function greet(name: string): string
```

Parameters:
- `name`: The name to greet

Returns:
- A greeting string

Throws:
- Error if name is empty
