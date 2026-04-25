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

### Human-in-the-loop: do not “auto-fix” fresh Red tests in the same pass

- When adding a **new Red test** (new behavior or regression), the agent must **not** immediately change production code to make it pass in the same uninterrupted agent pass.
- A **human checkpoint is required** between Red and Green so the author can trust the test was actually red at least once (e.g. user runs the test, or explicitly instructs the agent to proceed to Green after reviewing the failing output).

## Naming and test layout conventions (mandatory)

### Semantic naming only (no issue/epic codes)

- Use **semantic, intention-revealing names** for everything: files, modules, functions, classes, variables, and tests.
- **Do not** encode epic/story/bug/issue identifiers in names (e.g. avoid `test_e1_*`, `E1B1*`, `issue_123_*`). Keep such references in commit/PR text, or as a short note inside a document like `docs/bugs.md`.

### Test modules: split by kind

Keep automated tests physically separated by purpose:

- `tests/unit/`: fast, isolated logic tests (controllers, pure functions, rules).
- `tests/ui/`: UI/toolkit adapter wiring with fakes (e.g. pystray adapter menu construction).
- `tests/integration/`: subprocess / multi-process / end-to-end seam tests (e.g. launching `python -m callscribe`).

If CI currently runs only on the target platform, keep the **test code** platform-agnostic anyway; scope **execution** via CI configuration or markers, not by baking OS-only skips into test modules.

### Cross-platform intent

- Build and test **portable seams** (e.g. single-instance locking/activation) behind small abstractions, so the app can be ported to other desktop OSes without rewriting application logic.

## Repository hygiene

- Do not commit IDE/editor config directories (e.g., `.vscode/`, `.idea/`).
- Prefer adding shared configuration via repo files (e.g., `.editorconfig`, `pyproject.toml`) rather than IDE settings.

