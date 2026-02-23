# Releasing flowbook

## Publish (official / pre-release)

1. `npm run ci` passes
2. `poetry build` → `dist/flowbook-*.whl`
3. `flowbook verify wheel` (optional)
4. **Tag** the release: `git tag v0.1.0a3`
5. **Publish** to PyPI: `twine upload dist/flowbook-0.1.0a3*`
6. Push tag: `git push origin v0.1.0a3`

## Pre-release (dev branch only)

- Push to **dev** branch only. Do not tag or publish.
- Alpha/beta versions (e.g. 0.1.0a3) are developed on dev until ready for release.
