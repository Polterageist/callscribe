# Agent Rules (Callscribe)

Project-specific rules for AI coding agents working in this repository.

## Documentation language workflow

- **Documents are authored in Russian first.**
- After the Russian version is stable, **finalize an English copy** (translation) as a separate document.
- Keep Russian and English versions **consistent**; when one changes, update the other.

## TDD workflow (mandatory)

- **TDD is mandatory** for any behavior change where tests are feasible.
- Follow **Red → Green → Refactor**:
  - **Red**: write a failing test that captures the intended behavior (or a regression for a bug).
  - **Green**: implement the minimal change to make the test pass.
  - **Refactor**: clean up without changing behavior; keep tests green.

## Repository hygiene

- Do not commit IDE/editor config directories (e.g., `.vscode/`, `.idea/`).
- Prefer adding shared configuration via repo files (e.g., `.editorconfig`, `pyproject.toml`) rather than IDE settings.

