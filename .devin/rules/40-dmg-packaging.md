# Rule 40 — DMG Packaging

> **Law. DMGs must be built, signed, and notarized before release.**

## Build Rules

1. DMG is built from a clean source directory. No build artifacts in source.
2. DMG is created using `hdiutil` with UDZO compression.
3. Volume name matches the app name.
4. DMG includes: app bundle, Applications symlink, README (optional).

## Signing & Notarization

1. DMG must be signed with a Developer ID Application certificate.
2. DMG must be notarized via `notarytool submit`.
3. Notarization ticket must be stapled via `stapler staple`.
4. Verification: `spctl -a -t exec -vv <dmg>` must return "accepted".

## Artifact Requirements

1. The DMG file itself is the primary artifact.
2. Notarization log is a secondary artifact.
3. Build log is a tertiary artifact.
4. All three are referenced in the receipt.

## Enforcement

- `/build-dmg` workflow follows these rules step-by-step.
- Any step failure aborts the build.
- No "build successful" claim without `spctl` verification passing.
