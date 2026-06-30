# Changelog

## [1.4.0](https://github.com/andrewtryder/repo-standards/compare/v1.3.0...v1.4.0) (2026-06-30)


### Features

* **apply:** add Release Please to standards migrations ([dde225b](https://github.com/andrewtryder/repo-standards/commit/dde225b5b126264629f888e395a1f30962dfac35))
* **apply:** add Release Please to standards migrations ([e7a95bb](https://github.com/andrewtryder/repo-standards/commit/e7a95bb02672901364a64204a7c02d9344d7968d))
* **standards:** detect fly deployments ([e5705b1](https://github.com/andrewtryder/repo-standards/commit/e5705b12fec3cdba27c5e7ca2db9885216b27a64))
* **standards:** improve adoption workflow ([#35](https://github.com/andrewtryder/repo-standards/issues/35)) ([6bbab0a](https://github.com/andrewtryder/repo-standards/commit/6bbab0a4b861ed3981250cebd7e5e8f80d931d8f))
* **standards:** improve adoption workflow and dependency separation ([97971b9](https://github.com/andrewtryder/repo-standards/commit/97971b9d11bcf329ba97a179abcfe99f78a3a620))
* **standards:** separate runtime and dev dependencies ([57f77a4](https://github.com/andrewtryder/repo-standards/commit/57f77a455370eef3ca53db891e5566888206b420))

## [1.3.0](https://github.com/andrewtryder/repo-standards/compare/v1.2.0...v1.3.0) (2026-06-27)


### Features

* **standards:** add V1.0 wizard and fixture harness ([#31](https://github.com/andrewtryder/repo-standards/issues/31)) ([7ec739b](https://github.com/andrewtryder/repo-standards/commit/7ec739b23b8286992228f594366a9bcb90f88682))

## [1.2.0](https://github.com/andrewtryder/repo-standards/compare/v1.1.0...v1.2.0) (2026-06-26)


### Features

* **standards:** add file-type code quality standards ([03eb56d](https://github.com/andrewtryder/repo-standards/commit/03eb56ddddfc7892a4f630d13bf78e5b2d8f436b))

## [1.1.0](https://github.com/andrewtryder/repo-standards/compare/v1.0.0...v1.1.0) (2026-06-24)


### Features

* **detection:** add optional GitHub Models advisor ([db344e6](https://github.com/andrewtryder/repo-standards/commit/db344e6a0ef7b86c8cb09bc76327356e0e8bb174))
* **detection:** add optional GitHub Models advisor ([bab428a](https://github.com/andrewtryder/repo-standards/commit/bab428a19c0bdae38be4dd181e728b8e403ab89a))
* **standards:** add explicit license creation option ([114e9d0](https://github.com/andrewtryder/repo-standards/commit/114e9d0b9bb429850d0a6089f768da9ed94ba4e5))
* **standards:** add explicit license creation option ([3b5934e](https://github.com/andrewtryder/repo-standards/commit/3b5934e4544a3f957281d309e5ba398abad89a92))


### Bug Fixes

* **ci:** test add-license block on empty temp repo ([c759196](https://github.com/andrewtryder/repo-standards/commit/c7591963defd41c561c554f9494556cd725a78c8))
* **standards:** lowercase add-license summary flag ([93042fd](https://github.com/andrewtryder/repo-standards/commit/93042fd4fb886a08de9596f5518acb6c6f199f29))
* **standards:** support private migrations and formatting ([88615c1](https://github.com/andrewtryder/repo-standards/commit/88615c153a18d82170ed27f23099cb98ffaf2220))

## 1.0.0 (2026-06-23)


### Features

* **standards:** add interactive migration workflow ([f5bd3a1](https://github.com/andrewtryder/repo-standards/commit/f5bd3a1a08505c6b757c4ddc4369a510a27b9932))
* **standards:** add interactive migration workflow ([e5c7713](https://github.com/andrewtryder/repo-standards/commit/e5c771339544db93d943d3b477f3a43a0a62e024))
* **standards:** add safe apply script ([5f3caa2](https://github.com/andrewtryder/repo-standards/commit/5f3caa232a41560598f9b4ede3a7e6aee5df4e4e))
* **standards:** add safe apply script ([a1c342a](https://github.com/andrewtryder/repo-standards/commit/a1c342aba903f9a81873789f23feabfe6b1a1520))


### Bug Fixes

* **docs:** repoint github-models-migration link to detection.md ([bff0343](https://github.com/andrewtryder/repo-standards/commit/bff03435760c5bcb393adf5104e3b4477b0b7495))
* **standards:** harden migrated workflow templates ([991cdac](https://github.com/andrewtryder/repo-standards/commit/991cdac92dd531fe1af59836c4b978237248c884))
* **standards:** harden migrated workflow templates ([ffdb6f8](https://github.com/andrewtryder/repo-standards/commit/ffdb6f86eb81ddda2c7c6b9e388a721338e6e7a5))
* **standards:** harden migration apply workflow ([e77ab11](https://github.com/andrewtryder/repo-standards/commit/e77ab110a3bc7f4259532cd81bd32997a16cf4aa))

## [Unreleased]

### Added

- Add LICENSE (MIT)
- Add SECURITY.md with vulnerability reporting policy
- Add CODE_OF_CONDUCT.md (Contributor Covenant v2.1)
- Add GitHub issue templates (bug report, feature request)
- Add pull request template
- Add CODEOWNERS

## v1.3 — 2026-06-23

- Repository health baseline (`.gitignore`, `.editorconfig`, `.env.example`, `SECURITY.md`, issue templates, ADRs)
- Governance templates (`CONTRIBUTING.md`, PR template, MIT and proprietary license templates)
- Repo-policy `visibility`, `license`, and `governance` fields on all profile templates
- Assessor v3 refinements (coverage deletion as cleanup, antigravity memories handling, state-based scoring)
- Workflow fixes (node reusable CI conditional setup-node and format check, manifest release-please, pinned TruffleHog)
- Assessments directory README and gitignore for regenerated outputs
