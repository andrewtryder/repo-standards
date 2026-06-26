# Governance model

Repo Standards makes repository governance explicit. The wizard should ask governance questions before creating or modifying policy files.

## Core questions

| Question | Why it matters |
|---|---|
| Is the repository public or private? | Drives license and community defaults |
| Which license should it use? | Prevents accidental license changes |
| Will more than one developer maintain it? | Drives CODEOWNERS and branch protection recommendations |
| Are outside contributors expected? | Drives issue templates and contribution docs |
| Are GitHub Discussions enabled? | Determines whether README and contributor docs should mention Discussions |
| Are issue templates needed? | Controls `.github/ISSUE_TEMPLATE/` recommendations |
| Is a security policy needed? | Controls `SECURITY.md` recommendation |
| Is CODEOWNERS recommended? | Supports review routing |

## GitHub Discussions

If GitHub Discussions are enabled for a repository, mention them in the README and contribution docs.

Recommended purposes:

- support
- design discussions
- contributor Q&A
- community/general
- manual review

Recommended policy shape:

```yaml
governance:
  discussions: enabled
  discussions_purpose: contributor-q-and-a
```

If Discussions are not enabled, direct users to issues, pull requests, or another support channel.

```yaml
governance:
  discussions: disabled
```

## Solo-maintained repositories

Solo-maintained repositories can use a lighter governance posture:

- PR template recommended
- issue templates optional
- CODEOWNERS optional
- Discussions optional
- branch protection still recommended for important repositories

## Multi-developer repositories

Multi-developer repositories should consider:

- CODEOWNERS
- branch protection
- required status checks
- PR template
- issue templates
- clear contribution docs
- Discussions for design or contributor Q&A when appropriate

## Repository policy

Governance decisions should be recorded in `.repo-policy.yml` where practical.

Example:

```yaml
visibility: public
license: Apache-2.0

governance:
  contributing: required
  pull_request_template: required
  issue_templates: recommended
  security_policy: required
  codeowners: recommended
  discussions: enabled
  discussions_purpose: contributor-q-and-a
```

## Migration summary

The wizard should also write governance choices into `.repo-standards-migration-summary.md` so reviewers can see which choices were made and why.
