# License selection

Repo Standards supports mixed public, private, open-source, and proprietary repositories.

License choices should be intentional. Repo Standards can help record and apply the choice, but it does not provide legal advice.

If unsure, choose manual review.

## Recommended choices

### Permissive open-source

| License | Notes |
|---|---|
| `MIT` | Simple permissive license commonly used for libraries and apps |
| `Apache-2.0` | Permissive license with explicit patent grant |
| `BSD-2-Clause` | Simple permissive BSD variant |
| `BSD-3-Clause` | Permissive BSD variant with non-endorsement clause |
| `ISC` | Short permissive license similar in effect to MIT |

### File-level copyleft

| License | Notes |
|---|---|
| `MPL-2.0` | File-level copyleft; useful when changes to covered files should remain open |

### Strong copyleft

| License | Notes |
|---|---|
| `GPL-3.0-only` | Strong copyleft license |
| `AGPL-3.0-only` | Strong copyleft with network-use provisions |

### Closed or internal

| Choice | Notes |
|---|---|
| `proprietary` | Private or closed-source repositories |
| `none` / `unlicensed` | No explicit license grant; use with care |
| `other` / `manual review` | Use when the correct license is unclear |

## Wizard behavior

The wizard asks:

```text
Which license should this repository use?
```

Recommended choices:

```text
MIT
Apache-2.0
BSD-2-Clause
BSD-3-Clause
ISC
MPL-2.0
GPL-3.0-only
AGPL-3.0-only
proprietary
none / unlicensed
other / manual review
```

The wizard does not change license terms without explicit user selection.

## Public repositories

Public repositories should normally have an explicit license.

Example:

```yaml
visibility: public
license: Apache-2.0
license_policy:
  source: wizard
  review_required: false
```

If no license decision has been made:

```yaml
visibility: public
license: other
license_policy:
  source: wizard
  review_required: true
  notes: "Manual license review required before publishing."
```

## Private repositories

Private repositories should not accidentally receive open-source licenses.

Example:

```yaml
visibility: private
license: proprietary
license_policy:
  source: wizard
  review_required: false
```

## Migration rule

During migration:

- preserve existing license files unless explicitly changing license
- warn when `.repo-policy.yml` and license files disagree
- require explicit confirmation before creating or replacing a license file
- default uncertain cases to manual review
