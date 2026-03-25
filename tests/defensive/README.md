# Defensive Tests

Ongoing security and integrity verification tests.

## Test Categories

### Prompt Injection Defense
- Validate that external content containing instructions is ignored
- Test common injection patterns from SecLists `Ai/LLM_Testing/`
- Verify constitutional security rules are enforced

### Secret Scanning
- Verify no secrets in staged git files
- Scan outputs for credential patterns
- Validate protected paths are inaccessible

### Input Validation
- Test boundary conditions on all tool inputs
- Verify path traversal prevention
- Test malformed input handling

### Access Control
- Verify file permission boundaries
- Test that blocked commands are rejected
- Validate MCP server restrictions

## Running Tests

```bash
# Run all defensive tests
./tests/defensive/run-all.sh

# Run specific category
./tests/defensive/run-all.sh --category injection
```

## Adding Tests

Each test file: `test_{category}_{name}.sh`
Must output: `PASS: {description}` or `FAIL: {description}`
Log failures to `memory/learning/failures/`
