#!/usr/bin/env bash
set -euo pipefail

REPO="${REPO:-andrewtryder/repo-standards}"
DESCRIPTION="Reusable GitHub repository standards: CI/CD workflows, governance, AI/editor rules, migration assessment, and deployment guidance."
HOMEPAGE="https://andrewtryder.github.io/repo-standards/"

TOPICS=(
  github-actions
  repository-standards
  standards
  ci-cd
  documentation
  devops
  python
  typescript
  governance
  dependabot
  release-please
  developer-experience
  best-practices
  rulesync
  repository-templates
  migration
  code-quality
)

cmd=(gh repo edit "$REPO" --description "$DESCRIPTION" --homepage "$HOMEPAGE")
for topic in "${TOPICS[@]}"; do
  cmd+=(--add-topic "$topic")
done

if [[ "${1:-}" == "--apply" ]]; then
  "${cmd[@]}"
  echo "Updated metadata for $REPO"
else
  echo "# Review before running:"
  printf '%q ' "${cmd[@]}"
  echo
  echo
  echo "Run with --apply to execute."
fi
