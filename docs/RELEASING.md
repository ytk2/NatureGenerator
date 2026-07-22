# Releasing

NatureGenerator releases use reviewed source, real Autodesk Fusion evidence,
and immutable annotated semantic-version tags.

## Release workflow

1. Define the Sprint scope and write its design record before implementation.
2. Create a feature branch from an updated, clean `main`.
3. Implement with Codex or manually, preserving layer boundaries and regression
   outputs.
4. Review the complete diff and run the full automated validation suite.
5. Run the documented real Fusion acceptance test on macOS. Record inputs,
   MeshBody behavior, counts, timings, regressions, and visual limitations.
6. Commit and push only the reviewed Sprint files.
7. Open a Draft Pull Request to `main`; keep it Draft until review is complete.
8. Merge through GitHub after approval. Do not tag an unmerged feature branch.
9. Update local `main`, verify it exactly matches `origin/main`, and create an
   annotated semantic-version tag on the merge commit.
10. Push the tag. Optionally create a GitHub Release only when explicitly
    requested and release notes and assets are ready.

Example tag creation:

```bash
git tag -a v0.9.0 -m "Root Generator"
git push origin v0.9.0
```

The version and message are release decisions, not values to infer from an
unfinished Sprint.

## Required release evidence

- Exact full-test, Python compilation, boundary-scan, documentation, and
  artifact-scan results.
- Exact deterministic regression digests where the generator has one.
- Real Fusion platform and observed parameter, vertex, face, and timing values.
- Screenshots copied without fabrication or visual alteration.
- Honest known limitations and any parameters that were not exhaustively
  tested.
- Merge commit SHA, annotated tag object SHA, and confirmation that local and
  remote tags peel to the same `main` commit.

## Tag and rollback policy

Published tags are immutable. Never force-update, delete and recreate, or move
a release tag to repair a release. If a release is wrong, preserve its tag,
document the issue, make the correction through a reviewed branch, and publish
a new semantic version. Users can roll back by checking out the prior release
tag; source history remains the recovery mechanism.
