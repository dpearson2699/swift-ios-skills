# Adoption and Configuration

Detailed guidance on installing SwiftLint, configuring `.swiftlint.yml`, and rolling out linting in existing codebases.

## Contents

- [Installation Paths](#installation-paths)
- [Configuration File Discovery](#configuration-file-discovery)
- [Configuration Deep Dive](#configuration-deep-dive)
- [Severity Tuning](#severity-tuning)
- [Environment Variable Interpolation](#environment-variable-interpolation)
- [Nested and Child Configurations](#nested-and-child-configurations)
- [Remote Configuration](#remote-configuration)
- [Rollout Strategy for Existing Codebases](#rollout-strategy-for-existing-codebases)

---

## Installation Paths

| Method | When to use |
| -------- | ------------- |
| **SwiftLintPlugins SPM package** | Default for any project with `Package.swift`. Pins version automatically. |
| **Homebrew** (`brew install swiftlint`) | CI runners, pre-commit hooks, standalone CLI usage. |
| **Mint** (`mint install realm/SwiftLint`) | Teams using Mint for tool management. |
| **CocoaPods** (`pod 'SwiftLint'`) | Legacy projects already using CocoaPods. Binary is at `${PODS_ROOT}/SwiftLint/swiftlint`. |
| **Pre-built binary** | Download from [GitHub releases](https://github.com/realm/SwiftLint/releases). Useful for controlled CI environments. |

The build tool plugin (via `SwiftLintPlugins`) is recommended over all other local integration methods. See the plugins and integrations reference linked from SKILL.md for setup details.

## Configuration File Discovery

SwiftLint treats the top-level `.swiftlint.yml` as the main configuration, then optionally merges the nearest nested `.swiftlint.yml` found while walking up from an individual file.

- If no config is found, SwiftLint uses its built-in defaults.
- A project root config applies to all files unless a nested config refines it for a subtree.
- At most one nested `.swiftlint.yml` is merged for any given file.
- Passing `--config` overrides automatic discovery entirely and disables nested-config lookup.

Working directory behavior:
- The build tool plugin uses the topmost `.swiftlint.yml` within the package/project directory as its working directory, and falls back to the package/project root if no config file is found there.
- Run scripts use `${SRCROOT}` or the Xcode build setting for the working directory.
- CLI invocations use the shell's current directory.

## Configuration Deep Dive

### Rule control keys

```yaml
# Enable defaults minus these:
disabled_rules:
  - trailing_whitespace
  - todo

# Add these on top of defaults:
opt_in_rules:
  - empty_count
  - closure_spacing
  - sorted_imports
  - vertical_whitespace_opening_braces
  - contains_over_filter_count
  - first_where
  - last_where
  - modifier_order
```

`only_rules` is mutually exclusive with `disabled_rules` and `opt_in_rules`. Use it only when you want to start from an empty rule set and explicitly list every rule:

```yaml
only_rules:
  - line_length
  - force_cast
  - force_try
```

### Analyzer rules

Analyzer rules require passing compiler logs to SwiftLint. They are not included in default or opt-in sets:

```yaml
analyzer_rules:
  - unused_import
  - unused_declaration
```

See the custom rules and analyze reference linked from SKILL.md.

### Path control

```yaml
included:
  - Sources
  - Tests

excluded:
  - .build
  - DerivedData
  - Carthage
  - Pods
  - "**/Generated"
  - "**/Snapshots"
```

`included` and `excluded` support glob patterns. Paths are relative to the config file's directory.

### Reporter

```yaml
reporter: xcode    # default — Xcode-compatible warnings/errors
# reporter: json
# reporter: sarif
# reporter: checkstyle
# reporter: csv
# reporter: emoji
# reporter: github-actions-logging
```

Use `sarif` for GitHub code scanning integration. Use `json` for custom tooling. Use `github-actions-logging` for inline PR annotations without SARIF upload.

### Global modifiers

```yaml
strict: true       # all warnings become errors
# lenient: true    # all errors become warnings (useful during initial adoption)
allow_zero_lintable_files: true  # don't error when no .swift files are found (useful in CI)
```

## Severity Tuning

Most rules accept `warning` and `error` thresholds:

```yaml
line_length:
  warning: 140
  error: 200
  ignores_comments: true
  ignores_urls: true
  ignores_interpolated_strings: true

type_body_length:
  warning: 300
  error: 500

file_length:
  warning: 500
  error: 1000
  ignore_comment_only_lines: true

function_body_length:
  warning: 50
  error: 100

cyclomatic_complexity:
  warning: 10
  error: 20
  ignores_case_statements: true

nesting:
  type_level: 2
  function_level: 3

identifier_name:
  min_length:
    warning: 2
    error: 1
  max_length:
    warning: 50
    error: 60
  excluded:
    - id
    - x
    - y
    - i
    - j
    - to
```

Check available configuration keys for any rule with `swiftlint rules <rule_name>` or the [rule directory](https://realm.github.io/SwiftLint/rule-directory.html).

## Environment Variable Interpolation

Configuration values can reference environment variables:

```yaml
included:
  - ${PROJECT_DIR}/Sources

excluded:
  - ${PROJECT_DIR}/Generated
```

This is useful when SwiftLint is invoked from different working directories (e.g., run scripts vs CLI).

## Nested and Child Configurations

SwiftLint supports both explicit parent/child config chaining and automatic nested configs.

### Explicit local parent/child configs

Use `child_config` and `parent_config` to layer configs deliberately:

```yaml
# .swiftlint.yml
child_config: .swiftlint-strict.yml
parent_config: Base/.swiftlint-base.yml
```

`child_config` refines the current config with higher priority. `parent_config` provides lower-priority defaults.

### Automatic nested configs

A `.swiftlint.yml` in a subdirectory can also act as a nested child config for files in that subtree:

```text
MyProject/
├── .swiftlint.yml          # root config
├── Sources/
│   └── .swiftlint.yml      # stricter config for production code (optional)
└── Tests/
    └── .swiftlint.yml      # relaxed config for test code
```

Example child config for tests:

```yaml
# Tests/.swiftlint.yml
disabled_rules:
  - force_unwrapping
  - force_try
  - force_cast

file_length:
  warning: 800
  error: 1500

function_body_length:
  warning: 100
  error: 200
```

Rule state from parent and child configs is merged. A child config only overrides the parent when it explicitly states the opposite for the same rule. For example, a parent `disabled_rules` entry still applies unless the child opt-ins that same rule, and a parent opt-in still applies unless the child disables it.

For `included` and `excluded`, SwiftLint applies special merge behavior: paths are resolved relative to each config file, child `excluded` entries can remove parent `included` entries, and child `included` entries can re-include paths excluded by the parent.

Nested configs are only used when SwiftLint discovers configs automatically. If you pass `--config`, nested discovery is disabled.

### CLI multi-config

Pass multiple configs via CLI. Later configs override earlier ones:

```sh
swiftlint --config .swiftlint.yml --config .swiftlint-strict.yml
```

## Remote Configuration

Pull a shared team configuration using `parent_config` with an HTTPS URL:

```yaml
parent_config: https://example.com/team-swiftlint.yml
remote_timeout: 2           # seconds, default is 2
remote_timeout_if_cached: 1  # seconds, used when a cached version exists
```

Remote configs are cached locally. If the fetch fails or times out, the cached version is used. If no cache exists and the fetch fails, SwiftLint fails with an error.

**Caution:** Remote configs introduce a network dependency. Ensure CI runners can reach the URL, or use a local copy as a fallback.

## Rollout Strategy for Existing Codebases

Adopting SwiftLint in an existing project without disrupting the team:

### Phase 1: Baseline

1. Install SwiftLint with defaults (or your team's starter config).
2. Run once to see the violation landscape: `swiftlint --reporter json | python3 -m json.tool | head -50`
3. Generate a baseline: `swiftlint --write-baseline .swiftlint.baseline`
4. Commit the baseline and config only after the baseline-aware CI command passes.

**Exit gate:** configuration and baseline are committed, and the exact
baseline-aware lint command used by CI is green.

### Phase 2: Stop the bleeding

1. CI enforces `swiftlint --strict --baseline .swiftlint.baseline` — no new violations allowed.
2. The build tool plugin shows warnings locally (developers see issues as they edit).
3. Do not enable `--fix` in CI or build phases.

**Exit gate:** CI remains green with zero new violations.

### Phase 3: Incremental cleanup

1. Pick a rule with many baseline violations. Fix violations in a dedicated PR.
2. Regenerate the baseline after each cleanup PR.
3. Add opt-in rules one at a time once the team is comfortable.
4. Move toward removing the baseline entirely as violations are cleaned up.

**Exit gate:** the baseline shrinks or remains intentionally stable, and CI
passes before the next cleanup batch or rule is added.

### Phase 4: Mature enforcement

1. Baseline is empty or removed.
2. `--strict` in CI, build tool plugin in local builds.
3. New opt-in rules go through team review before enabling.
4. Consider analyzer rules for high-value checks like `unused_import`.

**Exit gate:** strict lint passes without a baseline.
