# Getting Started

NatureGenerator is tested with Autodesk Fusion on macOS. There is currently no
installer, so setup uses Fusion's **Scripts and Add-Ins** dialog.

## Use the stable release

For normal use, download or check out the stable `v0.8.0` source. Keep the
`NatureGenerator` directory together so that it contains
`NatureGenerator.py`, `NatureGenerator.manifest`, `commands/`, `generators/`,
and the other package directories.

1. In Fusion, open **Utilities > Add-Ins > Scripts and Add-Ins**.
2. Add or copy the `NatureGenerator` add-in folder into Fusion's add-in
   location.
3. Select NatureGenerator and choose **Run**. Enable run-on-startup if desired.
4. Open **Generate Nature** in the Design workspace Add-Ins panel.
5. Select Sponge, Coral, Rock, or Bark, adjust the displayed preset parameters,
   and generate a MeshBody.

Higher Resolution values increase mesh density and pure-Python run time. Seeds
make supported procedural variations repeatable. Parameter ranges shown in the
dialog are part of each preset's metadata.

Root appears only on the unreleased Sprint 11 development branch and still
requires real Fusion acceptance before release.

## Developer checkout

Clone the repository, switch to a feature branch created from current `main`,
and run the dependency-free tests from the repository root:

```bash
PYTHONPATH=NatureGenerator python3 -m unittest discover -s NatureGenerator/tests
```

Point Fusion at the checkout's `NatureGenerator` add-in directory. Restart or
stop and run the add-in after changing Python files. Development branches may
contain unreleased presets and should not be treated as stable installations.

To recover the released Bark baseline:

```bash
git fetch origin --tags
git checkout v0.8.0
```

That checkout is detached and is suitable for inspection or recovery. Create a
new branch before making changes.

## Troubleshooting

- If Fusion cannot import sibling packages, confirm the selected add-in folder
  directly contains `NatureGenerator.py`; do not select the repository parent.
- If **Generate Nature** is missing, stop and rerun the add-in and inspect
  Fusion's Text Commands/log output for the startup diagnostic.
- If controls are duplicated, stop the add-in before reloading it and restart
  Fusion if an earlier development run left UI state behind.
- If generation is slow, return Resolution to the preset default before
  changing other parameters.
- Do not install third-party Python packages into Fusion for this project; the
  runtime uses the standard library only.

See [Contributing](../CONTRIBUTING.md) for development conventions and
[Releasing](RELEASING.md) for the review and release process.
