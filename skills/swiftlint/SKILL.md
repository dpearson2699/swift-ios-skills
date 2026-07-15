---
name: swiftlint
description: "Configures and enforces SwiftLint in Swift projects using build tool plugins, run scripts, and CI. Covers .swiftlint.yml configuration, disabled_rules, opt_in_rules, only_rules, analyzer_rules, baselines, autocorrect, swiftlint:disable suppressions, reporter formats (sarif, json, checkstyle), strict and lenient modes, SwiftLintBuildToolPlugin via SimplyDanny/SwiftLintPlugins, swift package plugin swiftlint, Xcode run script phases, CI integration, multiple configuration files, and rollout strategies for existing codebases. Use when setting up SwiftLint, configuring lint rules, suppressing warnings, creating baselines, choosing between build tool plugin and run script, or integrating SwiftLint into CI."
---

# SwiftLint

SwiftLint enforces Swift style and conventions by linting source files against a configurable rule set. This skill covers setup, configuration, rule selection, suppression, CI integration, and rollout strategy.

SwiftLint is a **style enforcement tool**, not a style guide. For underlying Swift naming and design conventions, see `swift-api-design-guidelines`. For architecture patterns, see `swift-architecture`.

## Contents

- [Recommended Setup](#recommended-setup)
- [Configuration](#configuration)
- [Rule Selection Strategy](#rule-selection-strategy)
- [Suppressions](#suppressions)
- [Baselines](#baselines)
- [Autocorrect](#autocorrect)
- [CI Integration](#ci-integration)
- [Integration Decision Tree](#integration-decision-tree)
- [Multiple Configurations](#multiple-configurations)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

---

## Recommended Setup

**Default: build tool plugin via `SimplyDanny/SwiftLintPlugins`.**

Add the plugin package to `Package.swift` or via Xcode's package dependencies:

```swift
// Package.swift
dependencies: [
  .package(url: "https://github.com/SimplyDanny/SwiftLintPlugins", from: "<reviewed-version>")
]
```

For SwiftPM targets, apply the plugin:

```swift
.target(
    name: "MyApp",
    plugins: [.plugin(name: "SwiftLintBuildToolPlugin", package: "SwiftLintPlugins")]
)
```

For Xcode projects without a `Package.swift`, add the package dependency in the project settings, then enable the plugin under the target's Build Phases or the package's plugin trust dialog.

The build tool plugin runs SwiftLint automatically on every build. No run script required.

> **First build**: Xcode prompts to trust the plugin. Select "Trust & Enable All" for the SwiftLintPlugins package.

For alternatives (run scripts, command plugin, Homebrew CLI), see [references/plugins-run-scripts-and-integrations.md](references/plugins-run-scripts-and-integrations.md).

## Configuration

Create `.swiftlint.yml` at the project root. SwiftLint loads the main configuration from the invocation or plugin working directory, then can merge the nearest nested `.swiftlint.yml` for each file when configs are discovered automatically. Passing `--config` overrides automatic discovery and disables nested-config lookup.

```yaml
# .swiftlint.yml — conservative starter config
disabled_rules:
  - trailing_whitespace
  - todo

opt_in_rules:
  - empty_count
  - closure_spacing
  - force_unwrapping
  - sorted_imports
  - vertical_whitespace_opening_braces
  - private_swiftui_state
  - unhandled_throwing_task
  - accessibility_label_for_image

included:
  - Sources
  - Tests

excluded:
  - .build
  - DerivedData
  - "**/.build"
  - "**/Generated"

line_length:
  warning: 140
  error: 200

type_body_length:
  warning: 300
  error: 500

file_length:
  warning: 500
  error: 1000
```

Key configuration options:

| Key | Purpose |
|-----|---------|
| `disabled_rules` | Turn off default-enabled rules |
| `opt_in_rules` | Turn on rules not enabled by default |
| `only_rules` | Use _only_ the listed rules (mutually exclusive with `disabled_rules`/`opt_in_rules`) |
| `analyzer_rules` | Rules requiring compiler logs (run via `swiftlint analyze`) |
| `baseline` | Path to an existing baseline file used to suppress known violations |
| `write_baseline` | Path where SwiftLint should write a new baseline file |
| `included` | Paths to lint (default: current directory) |
| `excluded` | Paths to skip |
| `strict` | Elevate all warnings to errors |
| `lenient` | Downgrade all errors to warnings |
| `allow_zero_lintable_files` | Suppress the error when no Swift files are found |
| `reporter` | Output format: `xcode` (default), `json`, `checkstyle`, `sarif`, `csv`, `emoji`, etc. |

For full configuration details including severity tuning, environment-variable interpolation, and nested/remote configs, see [references/adoption-and-configuration.md](references/adoption-and-configuration.md).

## Rule Selection Strategy

SwiftLint ships with three rule categories:

1. **Default rules** — enabled automatically, cover widely accepted conventions
2. **Opt-in rules** — disabled by default, enable selectively via `opt_in_rules`
3. **Analyzer rules** — require compiler logs, enabled via `analyzer_rules`

Browse the full categorized list at <https://realm.github.io/SwiftLint/rule-directory.html>.

**Recommended approach for new projects:**

1. Start with defaults. Run `swiftlint rules` to see which rules are enabled.
2. Disable rules that conflict with your team's established conventions.
3. Add opt-in rules one at a time. Review violations before committing each addition.
4. Do not use `only_rules` unless you have a specific reason to start from zero.

**Recommended approach for existing codebases:**

1. Start with the default rule set.
2. Create a baseline (see [Baselines](#baselines)) to suppress all existing violations.
3. Run the same strict, baseline-aware command used by CI and fix every new violation.
4. Re-run until green before enabling another rule or starting the next cleanup batch.
5. Burn down baseline violations incrementally without accepting baseline growth.

Do not transcribe or memorize the rule directory. Look up rule identifiers and configuration options at the official rule directory when needed.

## Suppressions

Suppress SwiftLint for specific lines when a rule produces a false positive or when the violation is intentional and reviewed.

```swift
// swiftlint:disable:next force_cast
let view = object as! UIView

let legacy = try! JSONDecoder().decode(T.self, from: data) // swiftlint:disable:this force_try

// swiftlint:disable:previous large_tuple
```

Disable for a region:

```swift
// swiftlint:disable cyclomatic_complexity
func complexRouter(...) { ... }
// swiftlint:enable cyclomatic_complexity
```

Disable all rules (use sparingly):

```swift
// swiftlint:disable all
// ... generated or legacy code ...
// swiftlint:enable all
```

**Policy:**
- Prefer targeted single-rule suppressions over `all`.
- Always re-enable after the region ends.
- For generated code, prefer `excluded` paths in `.swiftlint.yml` over inline suppressions.
- For test targets with different tolerance, use a child configuration (see [Multiple Configurations](#multiple-configurations)).

For full suppression syntax, see [references/rules-suppressions-and-baselines.md](references/rules-suppressions-and-baselines.md).

## Baselines

Baselines let you adopt SwiftLint in an existing codebase without fixing every legacy violation first.

**Create a baseline:**

```sh
swiftlint --write-baseline .swiftlint.baseline
```

This records all current violations. Future runs compare against this baseline and only report new violations.

**Use the baseline:**

```sh
swiftlint --baseline .swiftlint.baseline
```

In CI, pass `--baseline` so only new violations fail the build. Burn down the baseline over time by fixing legacy violations and regenerating.

For baseline workflows and rollout strategy, see [references/rules-suppressions-and-baselines.md](references/rules-suppressions-and-baselines.md).

## Autocorrect

SwiftLint can fix some violations automatically:

```sh
swiftlint --fix
# or the legacy alias:
swiftlint --autocorrect
```

**Warnings:**

- **Never run `--fix` as a pre-compile build phase.** Auto-fixes modify source files. If run automatically on every build, this creates an unpredictable edit-build loop and can mask real issues.
- Run `--fix` manually or in a dedicated CI step, then review the diff.
- Not all rules support autocorrect. Check `swiftlint rules` — the "Correctable" column shows which rules can auto-fix.
- Always commit or stash before running `--fix`.

## CI Integration

CI is the primary enforcement surface. A CI check ensures no one merges code that increases the violation count.

**Recommended CI pattern:**

```yaml
# GitHub Actions example
- name: Lint
  run: |
    brew install swiftlint
    swiftlint --strict --reporter sarif > swiftlint.sarif
```

Key CI options:

| Flag | Effect |
|------|--------|
| `--strict` | Exits non-zero on warnings (not just errors) |
| `--reporter sarif` | GitHub Advanced Security compatible output |
| `--reporter json` | Machine-readable output |
| `--reporter checkstyle` | Jenkins/SonarQube compatible |
| `--baseline .swiftlint.baseline` | Only fail on new violations |

For SARIF upload to GitHub code scanning, add `github/codeql-action/upload-sarif` after the lint step.

After any configuration, baseline, or rule change, run the exact CI lint command
locally or in a validation job. On a nonzero exit, inspect and fix the new
violations, then rerun the same command until it passes; do not regenerate the
baseline merely to hide the failure.

For full CI recipes and reporter details, see [references/plugins-run-scripts-and-integrations.md](references/plugins-run-scripts-and-integrations.md).

## Integration Decision Tree

Choose how to run SwiftLint based on project shape:

| Scenario | Recommended integration |
|----------|------------------------|
| SwiftPM package or Xcode project with `Package.swift` | Build tool plugin via `SwiftLintPlugins` |
| SwiftPM project needing CLI flags (`--fix`, `--baseline`) | Command plugin: `swift package plugin swiftlint` |
| Xcode project without SwiftPM, team uses Homebrew | Run script build phase |
| CI/CD pipeline | Homebrew or Docker install, run `swiftlint` directly |
| Pre-commit hook | Homebrew install + `.pre-commit-config.yaml` or git hook script |

The build tool plugin is preferred for local development because it requires no PATH configuration, pins the SwiftLint version via package resolution, and runs automatically on build.

For detailed setup instructions for each integration, see [references/plugins-run-scripts-and-integrations.md](references/plugins-run-scripts-and-integrations.md).

## Multiple Configurations

SwiftLint supports layered configuration files. A `.swiftlint.yml` in a subdirectory inherits from and overrides the parent config.

Common patterns:

- **Relaxed test config**: place a `.swiftlint.yml` in `Tests/` that disables `force_unwrapping` and raises `file_length`
- **Strict module config**: place a stricter `.swiftlint.yml` in a shared module directory
- **Remote config**: use `parent_config` with an HTTPS URL to pull a shared team config (caching supported)

```yaml
# Tests/.swiftlint.yml — child config
disabled_rules:
  - force_unwrapping
  - force_try

file_length:
  warning: 800
```

You can also pass multiple configs on the CLI:

```sh
swiftlint --config .swiftlint.yml --config .swiftlint-extra.yml
```

Later configs override earlier ones for overlapping keys.

For nested config resolution, remote configs, and CLI multi-config details, see [references/adoption-and-configuration.md](references/adoption-and-configuration.md).

## Common Mistakes

1. **Running `--fix` in a build phase.** Auto-fixing on every build creates unpredictable source modifications. Run `--fix` manually.

2. **Using `only_rules` without understanding the implication.** This disables all rules except those listed. Most teams should use `disabled_rules` + `opt_in_rules` instead.

3. **Suppressing with `// swiftlint:disable all` and forgetting to re-enable.** This silently disables all linting for the rest of the file.

4. **Not pinning the SwiftLint version.** Different versions have different default rules. Use the build tool plugin (version pinned via SPM) or pin in your `Brewfile` / CI config.

5. **Excluding too broadly.** Excluding `Tests/` entirely means test code gets no linting. Use a child config with relaxed rules instead.

6. **Ignoring the toolchain mismatch.** SwiftLint must be built with (or compatible with) the same Swift toolchain used to compile your project. Mismatches cause parsing errors. See [references/plugins-run-scripts-and-integrations.md](references/plugins-run-scripts-and-integrations.md) for multi-toolchain guidance.

7. **Adopting too many opt-in rules at once in a large codebase.** This creates an overwhelming number of violations. Add rules incrementally and use baselines.

8. **Not configuring `included` paths.** Without `included`, SwiftLint scans the working directory recursively, which may pick up vendored or generated code.

## Review Checklist

- [ ] `.swiftlint.yml` exists at the project root with explicit `included`/`excluded` paths
- [ ] SwiftLint version is pinned (via SPM plugin resolution, Brewfile, or CI config)
- [ ] Build tool plugin is enabled for each target that should be linted
- [ ] CI runs `swiftlint --strict` (or with `--baseline` for incremental adoption)
- [ ] Baseline does not grow unintentionally, and CI is green before the next
      rule or cleanup batch
- [ ] No `--fix` / `--autocorrect` in build phases
- [ ] Inline suppressions target specific rules, not `all`
- [ ] Inline suppressions include a comment explaining why
- [ ] Test targets have appropriate config (relaxed rules via child config, not excluded entirely)
- [ ] Autocorrect changes are reviewed in a separate commit
- [ ] New opt-in rules are added one at a time with team consensus

## References

- [references/adoption-and-configuration.md](references/adoption-and-configuration.md) — Installation paths, `.swiftlint.yml` deep dive, severity tuning, environment variables, nested/remote configs, rollout strategy
- [references/plugins-run-scripts-and-integrations.md](references/plugins-run-scripts-and-integrations.md) — Build tool plugin, command plugin, run scripts, CI recipes, multi-toolchain guidance, VS Code, Fastlane, Docker, pre-commit
- [references/rules-suppressions-and-baselines.md](references/rules-suppressions-and-baselines.md) — Default vs opt-in vs analyzer rules, suppression syntax, baseline workflows, false-positive handling
- [references/rule-reference.md](references/rule-reference.md) — Bundled exhaustive rule index for local lookup; verify current details with `swiftlint rules` or the official rule directory
- [references/custom-rules-and-analyze.md](references/custom-rules-and-analyze.md) — Regex custom rules, Swift custom rules (brief), `swiftlint analyze`, compiler-log workflow
- [SwiftLint documentation](https://realm.github.io/SwiftLint/) — Official docs
- [SwiftLint rule directory](https://realm.github.io/SwiftLint/rule-directory.html) — Full categorized rule list
- [SimplyDanny/SwiftLintPlugins](https://github.com/SimplyDanny/SwiftLintPlugins) — Recommended plugin package
