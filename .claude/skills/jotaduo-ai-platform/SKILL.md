```markdown
# jotaduo-ai-platform Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches the core development patterns and conventions used in the `jotaduo-ai-platform` Python codebase. Learn how to structure files, write imports and exports, follow commit message guidelines, and organize tests. Use the documented commands and workflows to streamline your development process and maintain consistency across the project.

## Coding Conventions

### File Naming
- Use **snake_case** for all file and module names.
  - Example: `data_processor.py`, `user_service.py`

### Import Style
- Use **relative imports** within the project.
  - Example:
    ```python
    from .utils import calculate_score
    from ..models import User
    ```

### Export Style
- Use **named exports** (explicitly listing what is exported).
  - Example:
    ```python
    __all__ = ['DataProcessor', 'process_data']
    ```

### Commit Messages
- Follow **conventional commits** with the `feat` prefix for new features.
  - Example:
    ```
    feat: add user authentication module
    ```
- Average commit message length: ~54 characters.

## Workflows

### Feature Development
**Trigger:** When adding a new feature to the codebase  
**Command:** `/feature-development`

1. Create a new branch for your feature.
2. Implement the feature using snake_case for files and relative imports.
3. Add or update tests in files matching `*.test.*`.
4. Commit your changes using the `feat` prefix and a concise description.
5. Open a pull request for review.

### Testing Code
**Trigger:** When verifying code functionality  
**Command:** `/run-tests`

1. Locate or create test files following the `*.test.*` pattern.
2. Write tests for your new or updated code.
3. Run the test suite using the project's preferred test runner (framework unknown; check project docs or use `pytest` as a default).
4. Ensure all tests pass before merging.

## Testing Patterns

- Test files follow the `*.test.*` naming pattern.
  - Example: `user_service.test.py`, `data_processor.test.py`
- The specific testing framework is **unknown**; check project documentation or use standard Python test runners like `pytest` or `unittest`.
- Place tests alongside the code or in a dedicated `tests/` directory.

## Commands

| Command               | Purpose                                      |
|-----------------------|----------------------------------------------|
| /feature-development  | Start the feature development workflow       |
| /run-tests            | Run the test suite for the codebase          |
```
