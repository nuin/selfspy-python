# Publishing Guide

This guide covers how to publish Selfspy to PyPI.

## Prerequisites

1. **PyPI Account**: Create an account at https://pypi.org/
2. **API Token**: Generate an API token at https://pypi.org/manage/account/token/
3. **GitHub Secret**: Add the token as `PYPI_API_TOKEN` in repository secrets

## Publishing Methods

### Method 1: GitHub Release (Automated)

The easiest way to publish is through GitHub releases:

1. Update version in `pyproject.toml`:
   ```toml
   version = "1.0.1"
   ```

2. Commit and push:
   ```bash
   git add pyproject.toml
   git commit -m "chore: bump version to 1.0.1"
   git push
   ```

3. Create a GitHub release:
   ```bash
   gh release create v1.0.1 --title "Release v1.0.1" --notes "Release notes here"
   ```

   Or via GitHub web UI:
   - Go to "Releases" → "Draft a new release"
   - Create tag: `v1.0.1`
   - Title: "Release v1.0.1"
   - Add release notes
   - Click "Publish release"

4. The GitHub Action will automatically:
   - Build the package
   - Publish to PyPI

### Method 2: Manual Publishing

For manual control or testing:

1. Build the package:
   ```bash
   uv build
   ```

2. Publish to Test PyPI (optional):
   ```bash
   uv publish --publish-url https://test.pypi.org/legacy/
   ```

3. Test installation from Test PyPI:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ selfspy
   ```

4. Publish to PyPI:
   ```bash
   uv publish
   ```

   Or with twine:
   ```bash
   pip install twine
   twine upload dist/*
   ```

## Version Numbering

Follow semantic versioning (semver):

- **Major** (1.0.0 → 2.0.0): Breaking changes
- **Minor** (1.0.0 → 1.1.0): New features, backwards compatible
- **Patch** (1.0.0 → 1.0.1): Bug fixes

## Pre-release Checklist

Before publishing a new version:

- [ ] Update version in `pyproject.toml`
- [ ] Update `CHANGELOG.md` with release notes
- [ ] Run tests: `pytest`
- [ ] Build package: `uv build`
- [ ] Test installation locally: `pip install dist/selfspy-*.whl`
- [ ] Verify commands work: `selfspy --version`
- [ ] Update documentation if needed
- [ ] Commit all changes
- [ ] Create git tag: `git tag v1.0.1`
- [ ] Push with tags: `git push --tags`

## Post-release

After publishing:

1. Verify on PyPI: https://pypi.org/project/selfspy/
2. Test installation: `pip install selfspy`
3. Announce release (Twitter, blog, etc.)
4. Update documentation website if applicable

## Troubleshooting

### Build fails

Check that all dependencies are properly specified in `pyproject.toml`:
```bash
uv build --verbose
```

### Upload fails

Verify your PyPI token is set correctly:
```bash
# Check token permissions at https://pypi.org/manage/account/token/
# Ensure PYPI_API_TOKEN secret is set in GitHub
```

### Package not found after publishing

PyPI indexing can take a few minutes. Wait 5-10 minutes and try again:
```bash
pip install --no-cache-dir selfspy
```

## Emergency: Yanking a Release

If a critical bug is discovered:

1. Yank the release on PyPI (doesn't delete, just marks as bad):
   ```bash
   # Via PyPI web interface: Manage → Yank release
   ```

2. Fix the bug and release a patch version immediately

Note: You cannot re-upload the same version number. Always increment the version.

## Resources

- PyPI: https://pypi.org/
- Test PyPI: https://test.pypi.org/
- Packaging guide: https://packaging.python.org/
- Semantic versioning: https://semver.org/
