# Contributing

## Development principles

- Keep `core/` and `generators/` independent from Autodesk Fusion 360 APIs.
- Put Fusion-specific imports and object conversion in `fusion/` or the add-in
  entry point.
- Use the Python standard library unless a dependency is discussed and approved.
- Prefer deterministic geometry algorithms with explicit units and tolerances.
- Add focused tests for behavior introduced by each change.

## Local workflow

1. Create a focused feature branch from `main`.
2. Make a small, documented change.
3. Run the test suite:

   ```bash
   python3 -m unittest discover -s NatureGenerator/tests
   ```

4. Review the diff for accidental Fusion dependencies in geometry modules.
5. Open a pull request that explains the design choice and validation performed.

## Fusion 360 testing

To exercise the add-in inside Fusion 360, register the repository's
`NatureGenerator/` directory as a Scripts and Add-Ins location. Fusion-specific
behavior requires Fusion 360's bundled Python environment; the geometry core and
its unit tests should continue to run in ordinary Python.

Do not commit generated meshes, local Fusion files, editor state, bytecode, or
credentials.
