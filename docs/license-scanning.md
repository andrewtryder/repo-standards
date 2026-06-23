# Dependency License Scanning

## Overview

Dependency license scanning is an optional quality gate that helps ensure your repository complies with open-source license requirements. It's not required by the repository standards but can be valuable for maintaining compliance.

## Why Consider License Scanning

License scanning helps you:

- Identify potential license conflicts between dependencies
- Ensure compliance with your organization's open-source policy
- Avoid accidentally including incompatible licenses
- Maintain transparency about your dependencies

## Not Required

License scanning is **not required** by the repository standards. It's an optional enhancement for repositories that need to manage license compliance.

## Node.js Tools

For Node.js repositories, consider using:

### license-checker

```bash
npm install -g license-checker
```

Generate a license report:

```bash
license-checker --production --out licenses.json
```

Or view a summary:

```bash
license-checker --production
```

### Other Options

- `npm-license-files` - Check for license files in dependencies
- `license-checker-cli` - Alternative to license-checker
- Custom scripts using `npm ls` and license metadata

## Python Tools

For Python repositories, consider using:

### pip-licenses

```bash
pip install pip-licenses
```

Generate a license report:

```bash
pip-licenses --format=json > licenses.json
```

Or view a summary:

```bash
pip-licenses --format=table
```

### Other Options

- `license-metadata` - Extract license information from packages
- `pip-licenses` - Most popular option for Python
- Custom scripts using `pip show` and license metadata

## Integration with CI

You can add license scanning as a CI check:

```yaml
# .github/workflows/license-scan.yml
name: License Scan
on: [pull_request, push]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: npm ci  # or pip install -r requirements.txt
      - name: Run license checker
        run: npm run license-check  # or pip-licenses
```

## Best Practices

1. **Run regularly**: Add license scanning to your CI pipeline
2. **Review reports**: Periodically review license reports for conflicts
3. **Document exceptions**: If you need to use a license-incompatible dependency, document why
4. **Keep dependencies updated**: Updated dependencies may have different licenses
5. **Use SPDX identifiers**: Prefer SPDX-compliant license identifiers for clarity

## Alternatives

If license scanning is not suitable for your repository:

- Manually review dependencies during code review
- Use package manager built-in license information
- Rely on manual compliance checks

## Resources

- [license-checker](https://www.npmjs.com/package/license-checker)
- [pip-licenses](https://github.com/soberhock/pip-licenses)
- [SPDX License List](https://spdx.org/licenses/)