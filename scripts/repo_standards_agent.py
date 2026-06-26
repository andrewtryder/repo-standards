#!/usr/bin/env python3
"""Interactive console walkthrough for adopting repo-standards in a target repository."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
STANDARDS_ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from detect_repo_standard import PROFILE_POLICY_TEMPLATES, detect_repo  # noqa: E402
from apply_repo_standards import (  # noqa: E402
    apply_actions,
    apply_formatting,
    build_plan,
    check_rulesync_outputs,
    confirm,
    format_summary_markdown,
    has_license_file,
    infer_github_visibility,
    license_warning_needed,
    load_env_files,
    parse_existing_policy,
    parse_github_remote_slug,
    remove_tracked_coverage_from_index,
    resolve_policy_fields,
    run_assessment,
    run_rulesync,
    summary_to_json,
)

_OUTPUT_STREAM = sys.stdout


def emit(*args, **kwargs) -> None:
    kwargs.setdefault("file", _OUTPUT_STREAM)
    print(*args, **kwargs)


LICENSE_OPTIONS = (
    "MIT",
    "Apache-2.0",
    "BSD-3-Clause",
    "ISC",
    "proprietary",
    "none",
)

ADOPTION_LEVELS: dict[str, str] = {
    "baseline": "Core policy, rules, governance files, and gitignore merge only.",
    "checks": "Baseline plus copied check workflows (semantic PR, AI rules, docs, secret scan).",
    "reusable-ci": "Baseline plus reusable CI workflow from repo-standards (recommended for new repos).",
    "full": "Checks adoption plus optional cleanup of tracked coverage artifacts.",
}


@dataclass
class CliDefaults:
    mode: str | None = None
    profile: str | None = None
    visibility: str | None = None
    license: str | None = None
    adoption_level: str | None = None


@dataclass
class WalkthroughChoices:
    mode: str = "existing"
    profile: str = ""
    visibility: str = ""
    license: str = ""
    adoption_level: str = "baseline"
    workflow_strategy: str = "copied"
    rules_strategy: str = "profile"
    add_license: bool = False
    replace_check_workflows: bool = False
    cleanup_generated_artifacts: bool = False
    migrate_existing_agent_rules: bool = False
    apply_mode: bool = False
    will_run_rulesync: bool = False
    run_assessment: bool = False
    update_existing: bool = False
    force: bool = False
    allow_generated_output_rewrite: bool = False
    format_touched: bool = False
    format_existing_docs: bool = False
    skip_format_generated: bool = False
    confirmed_decisions: list[str] = field(default_factory=list)


def choose(
    prompt: str,
    options: list[tuple[str, str]],
    *,
    default: str | None = None,
    auto_yes: bool = False,
) -> str:
    """Present a numbered menu and return the selected option value."""
    if not options:
        raise ValueError("choose() requires at least one option")

    valid = {value for value, _ in options}
    if default is not None and default not in valid:
        raise ValueError(f"default {default!r} is not among option values")

    if auto_yes:
        selected = default or options[0][0]
        label = next(desc for value, desc in options if value == selected)
        emit(f"{prompt}: {label} (auto)")
        return selected

    emit(f"\n{prompt}")
    default_index: int | None = None
    for index, (value, description) in enumerate(options, start=1):
        marker = " (default)" if value == default else ""
        emit(f"  {index}. {description}{marker}")
        if value == default:
            default_index = index

    while True:
        hint = f" [{default_index}]" if default_index is not None else ""
        try:
            answer = input(f"Choose{hint}: ").strip()
        except EOFError:
            if default is not None:
                return default
            return options[0][0]
        if not answer and default is not None:
            return default
        if answer.isdigit():
            picked = int(answer)
            if 1 <= picked <= len(options):
                return options[picked - 1][0]
        matches = [value for value, _ in options if value == answer]
        if len(matches) == 1:
            return matches[0]
        print("Invalid choice. Enter a number or option value.", file=sys.stderr)


def confirm_or_default(
    prompt: str,
    *,
    default: bool = False,
    auto_yes: bool = False,
) -> bool:
    if auto_yes:
        emit(f"{prompt}: {'yes' if default else 'no'} (auto)")
        return default
    return confirm(prompt, default=default)


def section(title: str) -> None:
    emit(f"\n{'=' * 72}")
    emit(title)
    emit("=" * 72)


def infer_default_mode(repo: Path) -> str:
    if not (repo / ".git").exists():
        return "new"
    return "existing"


def print_detection(detection: dict[str, Any]) -> None:
    emit(f"  Language:            {detection.get('language')}")
    emit(f"  Package manager:     {detection.get('package_manager')}")
    emit(f"  Deployment provider: {detection.get('deployment_provider')}")
    emit(f"  Recommended profile: {detection.get('recommended_profile')}")
    emit(f"  Confidence:          {detection.get('confidence')}")

    evidence = detection.get("evidence") or []
    if evidence:
        emit("\n  Evidence:")
        for item in evidence:
            emit(f"    - {item}")

    manual = detection.get("manual_review") or []
    if manual:
        emit("\n  Manual review notes:")
        for note in manual:
            emit(f"    - {note}")


def step_intro_and_mode(
    repo: Path,
    choices: WalkthroughChoices,
    *,
    auto_yes: bool,
    cli: CliDefaults | None = None,
) -> None:
    section("Step 1: Repository and mode")
    slug = parse_github_remote_slug(repo)
    emit(f"Repository: {repo}")
    emit(f"GitHub remote: {slug or 'not detected'}")
    default_mode = (cli.mode if cli else None) or infer_default_mode(repo)
    choices.mode = choose(
        "Migration mode",
        [
            ("existing", "Existing repository (default for adopted codebases)"),
            ("new", "New repository (greenfield starter)"),
        ],
        default=default_mode,
        auto_yes=auto_yes,
    )
    choices.confirmed_decisions.append(f"Mode: {choices.mode}")


def step_detection(
    repo: Path,
    standards: Path,
    choices: WalkthroughChoices,
    *,
    auto_yes: bool,
    cli: CliDefaults | None = None,
) -> dict[str, Any]:
    section("Step 2: Detection")
    detection = detect_repo(repo, standards)
    print_detection(detection)

    recommended = detection["recommended_profile"]
    profile_default = (cli.profile if cli else None) or recommended
    profile_options = [
        (name, f"{name} ({PROFILE_POLICY_TEMPLATES[name]})")
        for name in sorted(PROFILE_POLICY_TEMPLATES)
    ]
    choices.profile = choose(
        "Profile",
        profile_options,
        default=profile_default,
        auto_yes=auto_yes,
    )
    choices.confirmed_decisions.append(f"Profile: {choices.profile}")
    return detection


def step_visibility(
    repo: Path,
    choices: WalkthroughChoices,
    *,
    auto_yes: bool,
    cli: CliDefaults | None = None,
) -> None:
    section("Step 3: Visibility")
    existing_visibility, _ = parse_existing_policy(repo)
    inferred, gh_source = infer_github_visibility(repo)

    emit("Current analysis:")
    if existing_visibility:
        emit(f"  .repo-policy.yml visibility: {existing_visibility}")
    else:
        emit("  .repo-policy.yml visibility: not set")
    if inferred:
        emit(f"  GitHub inference ({gh_source}): {inferred}")
    else:
        emit(f"  GitHub inference: unavailable ({gh_source})")

    default_visibility = (
        (cli.visibility if cli else None)
        or existing_visibility
        or inferred
        or ("private" if choices.mode == "existing" else "public")
    )
    choices.visibility = choose(
        "Repository visibility for .repo-policy.yml",
        [
            ("public", "Public repository"),
            ("private", "Private repository"),
        ],
        default=default_visibility,
        auto_yes=auto_yes,
    )
    choices.confirmed_decisions.append(f"Visibility: {choices.visibility}")


def step_license(
    repo: Path,
    choices: WalkthroughChoices,
    *,
    auto_yes: bool,
    cli: CliDefaults | None = None,
) -> None:
    section("Step 4: License")
    _, existing_license = parse_existing_policy(repo)
    policy_preview = resolve_policy_fields(
        repo, choices.mode, choices.visibility, None
    )
    default_license = (
        (cli.license if cli else None) or existing_license or policy_preview.license
    )

    has_license = has_license_file(repo)
    emit("Current analysis:")
    if existing_license:
        emit(f"  .repo-policy.yml license: {existing_license}")
    else:
        emit("  .repo-policy.yml license: not set")
    emit(f"  LICENSE file present: {'yes' if has_license else 'no'}")
    emit(
        f"  Suggested default ({policy_preview.license_source}): {default_license}"
    )

    needed, warning = license_warning_needed(
        choices.visibility, default_license, has_license
    )
    if needed:
        emit(f"\n  Warning: {warning}")

    license_menu = [(value, value) for value in LICENSE_OPTIONS]
    choices.license = choose(
        "License for .repo-policy.yml",
        license_menu,
        default=default_license if default_license in LICENSE_OPTIONS else "MIT",
        auto_yes=auto_yes,
    )

    add_default = (
        choices.license == "MIT"
        and not has_license
        and choices.visibility == "public"
    )
    choices.add_license = confirm_or_default(
        "Create LICENSE file from template? (--add-license supports MIT only)",
        default=add_default,
        auto_yes=auto_yes,
    )
    choices.confirmed_decisions.append(f"License: {choices.license}")
    if choices.add_license:
        choices.confirmed_decisions.append("Add LICENSE file: yes")


def step_adoption(
    choices: WalkthroughChoices,
    *,
    auto_yes: bool,
    cli: CliDefaults | None = None,
) -> None:
    section("Step 5: Adoption level")
    emit("Adoption levels:")
    for level, description in ADOPTION_LEVELS.items():
        emit(f"  - {level}: {description}")

    default_level = (
        (cli.adoption_level if cli else None)
        or ("reusable-ci" if choices.mode == "new" else "baseline")
    )
    choices.adoption_level = choose(
        "Adoption level",
        [(level, f"{level} — {desc}") for level, desc in ADOPTION_LEVELS.items()],
        default=default_level,
        auto_yes=auto_yes,
    )
    if choices.adoption_level == "reusable-ci":
        choices.workflow_strategy = "reusable"
    else:
        choices.workflow_strategy = "copied"
    choices.confirmed_decisions.append(f"Adoption level: {choices.adoption_level}")


def build_policy_fields(repo: Path, choices: WalkthroughChoices):
    return resolve_policy_fields(
        repo, choices.mode, choices.visibility, choices.license
    )


def make_plan(
    repo: Path,
    standards: Path,
    choices: WalkthroughChoices,
    policy_fields,
    *,
    for_apply: bool,
) -> Any:
    return build_plan(
        repo,
        standards,
        mode=choices.mode,
        profile=choices.profile,
        workflow_strategy=choices.workflow_strategy,
        rules_strategy=choices.rules_strategy,
        adoption_level=choices.adoption_level,
        update_existing=choices.update_existing,
        force=choices.force,
        allow_generated_output_rewrite=choices.allow_generated_output_rewrite,
        cleanup_generated_artifacts=choices.cleanup_generated_artifacts,
        replace_check_workflows=choices.replace_check_workflows,
        migrate_existing_agent_rules=choices.migrate_existing_agent_rules,
        for_apply=for_apply,
        will_run_rulesync=choices.will_run_rulesync,
        policy_fields=policy_fields,
        format_touched=choices.format_touched,
        format_existing_docs=choices.format_existing_docs,
        add_license=choices.add_license,
    )


def step_plan_preview(
    repo: Path,
    standards: Path,
    choices: WalkthroughChoices,
    policy_fields,
) -> Any:
    section("Step 6: Dry-run preview")
    summary = make_plan(
        repo, standards, choices, policy_fields, for_apply=False
    )
    summary.interactive = True
    summary.confirmed_decisions.extend(choices.confirmed_decisions)
    emit(format_summary_markdown(summary))
    return summary


def step_risky_decisions(
    summary: Any, choices: WalkthroughChoices, *, auto_yes: bool
) -> None:
    section("Step 7: Risky operations")
    has_replaceable = any(
        wf.get("classification") == "replaceable-check"
        for wf in summary.workflow_classifications
    )

    if not has_replaceable and not summary.tracked_generated_artifacts and not summary.existing_generated_outputs:
        emit("No risky operations detected for this repository.")
        return

    if has_replaceable:
        if confirm_or_default(
            "Replace check-only workflows?",
            default=False,
            auto_yes=auto_yes,
        ):
            choices.replace_check_workflows = True
            choices.confirmed_decisions.append("Replace check-only workflows")

    if summary.tracked_generated_artifacts:
        if confirm_or_default(
            "Remove tracked generated artifacts from git index?",
            default=False,
            auto_yes=auto_yes,
        ):
            choices.cleanup_generated_artifacts = True
            choices.confirmed_decisions.append(
                "Remove tracked coverage from git index"
            )

    if summary.existing_generated_outputs:
        if confirm_or_default(
            "Migrate existing generated agent rules into Rulesync source?",
            default=False,
            auto_yes=auto_yes,
        ):
            choices.migrate_existing_agent_rules = True
            choices.confirmed_decisions.append(
                "Migrate existing generated agent rules"
            )


def step_apply_decision(
    choices: WalkthroughChoices, *, auto_yes: bool, cli_apply: bool
) -> None:
    section("Step 8: Apply changes")
    if cli_apply:
        choices.apply_mode = True
        emit("Apply mode enabled via --apply.")
        choices.confirmed_decisions.append("Apply mode: --apply flag")
        return

    if confirm_or_default(
        "Write changes to the repository? (No = dry-run only)",
        default=False,
        auto_yes=auto_yes,
    ):
        choices.apply_mode = True
        choices.confirmed_decisions.append("Apply mode: confirmed")
    else:
        choices.apply_mode = False
        choices.confirmed_decisions.append("Apply mode: dry-run only")


def step_post_apply_decisions(
    choices: WalkthroughChoices, *, auto_yes: bool
) -> None:
    if not choices.apply_mode:
        choices.will_run_rulesync = False
        choices.run_assessment = False
        return

    section("Step 9: Rulesync")
    choices.will_run_rulesync = confirm_or_default(
        "Run Rulesync after applying?",
        default=True,
        auto_yes=auto_yes,
    )
    if choices.will_run_rulesync:
        choices.confirmed_decisions.append("Run Rulesync")

    section("Step 10: Assessment")
    choices.run_assessment = confirm_or_default(
        "Run standards assessment after applying?",
        default=False,
        auto_yes=auto_yes,
    )
    if choices.run_assessment:
        choices.confirmed_decisions.append("Run final assessment")


def execute_apply(
    repo: Path,
    standards: Path,
    choices: WalkthroughChoices,
    policy_fields,
    summary_path: Path,
) -> tuple[Any, int]:
    summary = make_plan(
        repo,
        standards,
        choices,
        policy_fields,
        for_apply=choices.apply_mode,
    )
    summary.apply_mode = choices.apply_mode
    summary.interactive = True
    summary.confirmed_decisions.extend(choices.confirmed_decisions)

    if choices.apply_mode:
        blocks = summary.by_type("BLOCK")
        if blocks:
            print("Error: blocked actions prevent apply.", file=sys.stderr)
            for item in blocks:
                print(f"  BLOCK {item.path}: {item.detail}", file=sys.stderr)
            return summary, 1

        apply_actions(summary, standards, repo)
        apply_formatting(
            summary,
            repo,
            language=summary.detection.get("language", ""),
            apply_mode=True,
            skip_format=choices.skip_format_generated,
            format_touched=choices.format_touched,
            format_existing_docs=choices.format_existing_docs,
        )

        if summary.cleanup_generated_artifacts and summary.tracked_generated_artifacts:
            remove_tracked_coverage_from_index(
                repo, summary.tracked_generated_artifacts
            )

        if choices.will_run_rulesync:
            summary.rulesync_ran = True
            ok, output = run_rulesync(repo)
            summary.rulesync_output = output
            if ok:
                summary.rulesync_result = "passed"
                check_rulesync_outputs(summary, repo)
            else:
                summary.rulesync_result = "failed"
                print("Warning: Rulesync failed.", file=sys.stderr)
                if output:
                    print(output, file=sys.stderr)
        else:
            summary.rulesync_result = "skipped"

        if choices.run_assessment:
            summary.assessment_ran = True
            code, output = run_assessment(repo, standards)
            summary.assessment_detail = output
            summary.assessment_result = "passed" if code == 0 else f"exit {code}"
            emit("\nAssessment output:")
            emit(output)
        else:
            summary.assessment_result = "skipped"
    else:
        summary.rulesync_result = "skipped (dry-run)"
        summary.assessment_result = "skipped (dry-run)"

    summary_path.write_text(format_summary_markdown(summary), encoding="utf-8")
    return summary, 0 if summary.rulesync_result != "failed" else 1


def step_summary(summary: Any, summary_path: Path, choices: WalkthroughChoices) -> None:
    section("Step 11: Summary and next steps")
    emit(f"Migration summary written to: {summary_path}")
    if choices.apply_mode:
        emit("\nSuggested next steps:")
        emit("  git status")
        emit("  git add .")
        emit('  git commit -m "chore(standards): adopt repo standards"')
        if summary.assessment_result not in {"passed", "skipped", "skipped (dry-run)"}:
            emit("\nReview assessment failures before committing.")
    else:
        emit("\nDry-run complete. Re-run with --apply or confirm apply in the walkthrough to write changes.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Interactive walkthrough for adopting repo-standards in a target repository."
        )
    )
    parser.add_argument(
        "--repo",
        required=True,
        type=Path,
        help="Path to the target repository.",
    )
    parser.add_argument(
        "--standards",
        type=Path,
        default=STANDARDS_ROOT,
        help=f"Path to repo-standards root (default: {STANDARDS_ROOT}).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes after the walkthrough (still prompts unless --yes).",
    )
    parser.add_argument(
        "--yes",
        "--non-interactive",
        dest="auto_yes",
        action="store_true",
        help="Accept recommended defaults without interactive prompts.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON summary at the end.",
    )
    parser.add_argument(
        "--summary-file",
        type=Path,
        default=None,
        help="Migration summary path (default: <repo>/.repo-standards-migration-summary.md).",
    )
    parser.add_argument(
        "--mode",
        choices=("new", "existing"),
        default=None,
        help="Override migration mode (non-interactive default).",
    )
    parser.add_argument("--profile", default=None, help="Override detected profile.")
    parser.add_argument(
        "--adoption-level",
        choices=("baseline", "checks", "reusable-ci", "full"),
        default=None,
        help="Override adoption level.",
    )
    parser.add_argument(
        "--visibility",
        choices=("public", "private"),
        default=None,
        help="Override repository visibility.",
    )
    parser.add_argument(
        "--license",
        choices=LICENSE_OPTIONS,
        default=None,
        help="Override license for .repo-policy.yml.",
    )
    parser.add_argument(
        "--skip-rulesync",
        action="store_true",
        help="Do not run Rulesync after applying changes.",
    )
    return parser.parse_args()


def main() -> int:
    global _OUTPUT_STREAM

    args = parse_args()
    repo = args.repo.resolve()
    standards = args.standards.resolve()

    if args.json:
        _OUTPUT_STREAM = sys.stderr

    if not repo.is_dir():
        print(f"Error: --repo must be an existing directory: {repo}", file=sys.stderr)
        return 1
    if not standards.is_dir():
        emit(
            f"Error: --standards must be an existing directory: {standards}",
            file=sys.stderr,
        )
        return 1
    if not args.auto_yes and not sys.stdin.isatty():
        emit(
            "Error: interactive mode requires a TTY. Use --yes for non-interactive mode.",
            file=sys.stderr,
        )
        return 1

    load_env_files(standards, repo)
    choices = WalkthroughChoices()
    auto_yes = args.auto_yes
    cli = CliDefaults(
        mode=args.mode,
        profile=args.profile,
        visibility=args.visibility,
        license=args.license,
        adoption_level=args.adoption_level,
    )

    emit("Repo Standards Agent")
    emit("Interactive walkthrough for adopting repo-standards.\n")

    step_intro_and_mode(repo, choices, auto_yes=auto_yes, cli=cli)
    step_detection(repo, standards, choices, auto_yes=auto_yes, cli=cli)
    step_visibility(repo, choices, auto_yes=auto_yes, cli=cli)
    step_license(repo, choices, auto_yes=auto_yes, cli=cli)
    step_adoption(choices, auto_yes=auto_yes, cli=cli)

    policy_fields = build_policy_fields(repo, choices)
    summary = step_plan_preview(repo, standards, choices, policy_fields)
    step_risky_decisions(summary, choices, auto_yes=auto_yes)

    if auto_yes:
        choices.apply_mode = bool(args.apply)
        choices.will_run_rulesync = choices.apply_mode and not args.skip_rulesync
        choices.run_assessment = False
        if choices.apply_mode:
            choices.confirmed_decisions.append("Apply mode: --apply with --yes")
        if args.skip_rulesync:
            choices.confirmed_decisions.append("Rulesync skipped: --skip-rulesync")
    else:
        step_apply_decision(choices, auto_yes=auto_yes, cli_apply=args.apply)
        step_post_apply_decisions(choices, auto_yes=auto_yes)
        if args.skip_rulesync:
            choices.will_run_rulesync = False
            choices.confirmed_decisions.append("Rulesync skipped: --skip-rulesync")

    summary_path = args.summary_file or (
        repo / ".repo-standards-migration-summary.md"
    )
    summary, exit_code = execute_apply(
        repo, standards, choices, policy_fields, summary_path
    )
    step_summary(summary, summary_path, choices)

    if args.json:
        print(json.dumps(summary_to_json(summary), indent=2, sort_keys=True))

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
