---
name: swift-api-design-guidelines
description: "Apply Swift API Design Guidelines to name, label, and document Swift APIs. Covers argument label rules (prepositional phrase rule, grammatical phrase rule, first-label omission), mutating/nonmutating pair naming (-ed/-ing participle pattern, form- prefix, sort/sorted, formUnion/union), side-effect naming (noun for pure, verb for mutating), documentation comment structure (summary by declaration kind, O(1) complexity rule), clarity at call site, role-based naming, protocol naming (-able/-ible/-ing), default arguments over method families, casing conventions, and terminology. Use when designing new Swift APIs, reviewing naming and argument labels, writing documentation comments, or refactoring for call site clarity."
---

# Swift API Design Guidelines

Apply the Swift API Design Guidelines when naming types, methods, properties, parameters, and argument labels. Targets Swift 6.3. For language features and syntax, see `swift-language`. For concurrency patterns, see `swift-concurrency`. For mixed requests, answer the API naming portion briefly, then route Swift type-system details to `swift-language` and lint configuration to `swiftlint` instead of implementing those sibling domains here.

## Contents

- [Argument Label Rules](#argument-label-rules)
- [Side-Effect Naming](#side-effect-naming)
- [Mutating and Nonmutating Pairs](#mutating-and-nonmutating-pairs)
- [Documentation Comments](#documentation-comments)
- [Clarity and Naming](#clarity-and-naming)
- [Fluent Usage and Protocols](#fluent-usage-and-protocols)
- [General Conventions](#general-conventions)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Argument Label Rules

Argument labels determine how a call site reads. Apply these rules in order.

### When to omit the first argument label

**Grammatical phrase rule.** When the first argument forms a grammatical phrase with the base name, omit the label. Move any leading words from what would be the label into the base name instead.

```swift
// GOOD — reads as "add subview y"
view.addSubview(y)

// BAD — redundant label breaks the phrase
view.add(subview: y)
```

**Value-preserving type conversions.** When an initializer performs a value-preserving (widening) conversion, omit the first argument label.

```swift
// GOOD — widening conversion, no label
let value = Int64(someUInt32)
let str = String(someCharacter)

// Narrowing or lossy conversions keep a label
let approx = Int64(truncating: someDecimal)
let str = String(describing: someObject)
```

**Indistinguishable arguments.** When all arguments cannot be usefully distinguished, omit all labels.

```swift
// GOOD — arguments are peers
let smaller = min(x, y)
zip(sequence1, sequence2)
```

### When to use a prepositional label

**Prepositional phrase rule.** When the first argument completes a prepositional phrase with the base name, label it with the preposition.

```swift
// GOOD — "remove boxes having length 12"
x.removeBoxes(havingLength: 12)

// GOOD — "fade from red"
view.fade(from: red)

// GOOD — "relative path from root"
path.relativePath(from: root)
```

**Exception — abstraction boundary.** When the first two arguments represent parts of a single abstraction, fold the preposition into the base name so each component gets its own label.

```swift
// GOOD — x and y are parts of a single abstraction (a point)
a.moveTo(x: b, y: c)

// BAD — preposition attaches to first arg, leaving y unlabeled
a.move(toX: b, y: c)
```

### Default: label everything else

When no special rule above applies, label the argument.

```swift
// GOOD
array.split(maxSplits: 2)
button.setTitle("OK", for: .normal)
controller.dismiss(animated: true)
array.sorted(by: >)
```

### Argument label decision table

| Situation | Rule | Example |
|-----------|------|---------|
| First arg completes grammatical phrase | Omit label, merge words into base name | `addSubview(y)` |
| Value-preserving init conversion | Omit first label | `Int64(someUInt32)` |
| Arguments are indistinguishable peers | Omit all labels | `min(x, y)` |
| First arg completes prepositional phrase | Label with preposition | `fade(from: red)` |
| First two args form a single abstraction | Fold preposition into base name | `moveTo(x: b, y: c)` |
| Everything else | Label it | `split(maxSplits: 2)` |

For extended examples and edge cases, see [references/argument-labels-and-parameters.md](references/argument-labels-and-parameters.md).

## Side-Effect Naming

Name functions and methods by their side effects.

### Functions with side effects — imperative verbs

When a function mutates state, name it as an imperative verb phrase.

```swift
// Mutates — imperative verb
array.sort()
array.append(newElement)
list.remove(at: index)
timer.invalidate()
```

### Functions without side effects — nouns or adjective phrases

When a function returns a result without mutating anything, name it as a noun phrase, adjective phrase, or read as a description of what it returns.

```swift
// Pure — noun/description
let d = point.distance(to: origin)
let area = rect.intersection(other)
let line = text.trimmingCharacters(in: .whitespaces)
```

### Boolean properties and methods

Boolean properties and methods read as assertions about the receiver.

```swift
// GOOD — reads as "line is empty"
line.isEmpty
set.contains(element)
url.isFileURL

// BAD — not an assertion
line.empty       // verb? adjective?
set.includes     // incomplete phrase
```

For more examples, see [references/side-effects-and-mutating-pairs.md](references/side-effects-and-mutating-pairs.md).

## Mutating and Nonmutating Pairs

When an operation has both mutating and nonmutating variants, name them as a pair.

### Verb-described operations — -ed/-ing suffix

When the operation is naturally described by a verb:
- **Mutating:** imperative verb (`sort`, `append`, `reverse`)
- **Nonmutating:** past participle `-ed` or present participle `-ing`

Default to `-ed` (past participle) when the phrase naturally describes the returned value. Use `-ing` (present participle) only when the `-ed` form is ungrammatical or describes the direct object rather than the returned receiver or result. A direct object is a clue to check the grammar, not the rule by itself.

| Mutating | Nonmutating | Why |
|----------|-------------|-----|
| `sort()` | `sorted()` | `-ed` — "a sorted array" |
| `reverse()` | `reversed()` | `-ed` — "a reversed collection" |
| `sortLines()` | `sortedLines()` | `-ed` — "sorted lines" describes the result |
| `append(y)` | `appending(y)` | `-ing` — `appended` does not describe the returned receiver clearly |
| `stripNewlines()` | `strippingNewlines()` | `-ing` — direct-object pattern from the guidelines |

### Noun-described operations — form- prefix

When the operation is naturally described by a noun:
- **Nonmutating:** the noun itself (`union`, `intersection`)
- **Mutating:** `form` prefix (`formUnion`, `formIntersection`)

```swift
// Nonmutating — returns new value
let combined = a.union(b)

// Mutating — modifies in place
a.formUnion(b)
```

### Factory methods — make- prefix

Factory methods that create a new value start with `make`.

```swift
let iterator = collection.makeIterator()
let buffer = parser.makeBuffer()
```

In mixed routing answers, briefly validate existing `make...` factory names before handing off unrelated type-system or linting details to sibling skills.

### Pair decision table

| Operation described by | Mutating name | Nonmutating name | Example pair |
|------------------------|---------------|-------------------|-------------|
| Verb (default) | verb | verb + `-ed` | `sort()` / `sorted()` |
| Verb (`-ed` is ungrammatical) | verb | verb + `-ing` | `stripNewlines()` / `strippingNewlines()` |
| Noun | `form` + Noun | noun | `formUnion(b)` / `union(b)` |

For the full -ed/-ing decision tree and expanded naming patterns, see [references/side-effects-and-mutating-pairs.md](references/side-effects-and-mutating-pairs.md).

## Documentation Comments

Every public declaration must have a documentation comment.

### Summary rules by declaration kind

| Declaration | Summary describes |
|-------------|-------------------|
| Function / method | What it does and what it returns |
| Subscript | What it accesses |
| Initializer | What it creates |
| Type / property / variable | What it **is** |

Write summaries as a single sentence fragment, beginning with a verb (for actions) or a noun phrase (for entities), ending in a period.

```swift
/// Returns the element at the specified index.
func element(at index: Int) -> Element { ... }

/// The number of elements in the collection.
var count: Int { ... }

/// Creates a new array with the given elements.
init(_ elements: some Sequence<Element>) { ... }

/// Accesses the element at the specified position.
subscript(index: Int) -> Element { ... }
```

### Symbol markup

Use standard symbol markup after the summary when relevant:

- `- Parameter name:` for individual parameters
- `- Parameters:` block for multiple parameters
- `- Returns:` for the return value
- `- Throws:` for errors thrown
- `- Complexity:` for algorithmic complexity

```swift
/// Removes and returns the element at the specified position.
///
/// - Parameter index: The position of the element to remove.
/// - Returns: The removed element.
/// - Complexity: O(*n*), where *n* is the length of the collection.
mutating func remove(at index: Int) -> Element { ... }
```

### O(1) complexity rule

Document the complexity of any computed property that is not O(1). Callers assume properties are O(1) by default. If a property does more than constant-time work, state the complexity explicitly.

```swift
/// The total weight of all items.
///
/// - Complexity: O(*n*), where *n* is the number of items.
var totalWeight: Double {
    items.reduce(0) { $0 + $1.weight }
}
```

For documentation patterns and examples, see [references/conventions-and-special-rules.md](references/conventions-and-special-rules.md).

## Clarity and Naming

Clarity at the point of use is the most important goal. Every design decision serves the person reading a call site.

**Clarity over brevity.** Longer names are acceptable when they remove ambiguity. Do not abbreviate.

```swift
// GOOD
employees.remove(at: position)

// BAD — ambiguous: remove the element? remove at position?
employees.remove(position)
```

**Include words needed to avoid ambiguity.** If omitting a word makes the call site unclear, keep it.

```swift
// GOOD — "at" clarifies the argument's role
friends.remove(at: index)

// BAD — is "index" the element to remove or the position?
friends.remove(index)
```

**Omit needless words.** Do not repeat type information already available from the context.

```swift
// GOOD
allViews.remove(cancelButton)

// BAD — "Element" repeats the type
allViews.removeElement(cancelButton)
```

**Name variables and parameters by role, not type.** Use the entity's role in the current context, not its type name.

```swift
// GOOD — describes the role
var greeting: String
func add(_ observer: NSObject, for keyPath: String)

// BAD — names the type
var string: String
func add(_ object: NSObject, for string: String)
```

**Compensate for weak type information.** When a parameter type is `Any`, `AnyObject`, or a fundamental type like `Int` or `String`, add role-clarifying words to the name.

```swift
// GOOD — role is clear despite weak types
func addObserver(_ observer: NSObject, forKeyPath path: String)

// BAD — what does "string" mean here?
func add(_ object: NSObject, for string: String)
```

For extended naming examples and patterns, see [references/naming-and-clarity.md](references/naming-and-clarity.md).

## Fluent Usage and Protocols

**Call sites read as grammatical English.** Prefer names that form grammatical phrases at the point of use.

```swift
// GOOD — reads fluently
x.insert(y, at: z)          // "x, insert y at z"
x.subviews.remove(at: i)    // "x's subviews, remove at i"
x.makeIterator()             // "x, make iterator"

// BAD — ungrammatical
x.insert(y, position: z)
x.subviews.remove(i)
```

**Initializer first argument.** The first argument to an initializer should not form a phrase continuing the type name.

```swift
// GOOD
let foreground = Color(red: 32, green: 64, blue: 128)

// BAD — "Color with red" reads awkwardly
let foreground = Color(havingRGBValuesRed: 32, green: 64, blue: 128)
```

**Protocol naming conventions:**

| Protocol describes | Naming pattern | Examples |
|--------------------|----------------|----------|
| What something **is** | Noun | `Collection`, `IteratorProtocol` |
| A **capability** | `-able`, `-ible`, or `-ing` suffix | `Equatable`, `Hashable`, `Sendable` |

## General Conventions

**Casing.** Types and protocols use `UpperCamelCase`. Everything else uses `lowerCamelCase`. Acronyms that are commonly all-caps in American English appear uniformly upper- or lower-cased based on position.

```swift
var utf8Bytes: [UTF8.CodeUnit]
var isRepresentableAsASCII = true
var userSMTPServer: SMTPServer
```

**Methods and properties over free functions.** Prefer methods and properties. Use free functions only when:
1. There is no obvious `self` — `min(x, y)`
2. The function is an unconstrained generic — `print(value)`
3. The function syntax is established domain notation — `sin(x)`

**Default arguments over method families.** Prefer a single method with default parameters over a family of methods that differ only in which parameters they accept. Place defaulted parameters at the end. Parameters with default values should always have argument labels — defaulted parameters are usually omitted at call sites, so their labels must be clear when they do appear.

```swift
// GOOD — labeled with defaults
func decode(_ data: Data, encoding: String.Encoding = .utf8) -> String?

// BAD — method family
func decode(_ data: Data) -> String?
func decode(_ data: Data, encoding: String.Encoding) -> String?
```

**Overload safety.** Methods may share a base name when they operate in different type domains or when their meaning is clear from context. Avoid return-type-only overloads that cause ambiguity at the call site.

For casing edge cases, overload patterns, and tuple/closure naming, see [references/conventions-and-special-rules.md](references/conventions-and-special-rules.md).

## Common Mistakes

| Mistake | Correction |
|---|---|
| Ambiguous or missing labels | Make the call read grammatically, such as `remove(at:)`. |
| Wrong mutating/nonmutating form | Use imperative verbs for mutation and a grammatical `-ed`/`-ing` or noun form for copies. |
| Names describe types or implementation | Name roles and semantic effects. |
| Public API lacks purpose or complexity docs | Add a concise summary and document non-O(1) properties. |
| `form` or factory prefixes are misapplied | Reserve `form` for noun operations; use `make` for factories. |
| Type information is repeated | Remove words already clear from the declaration and context. |
| Overloads differ only by return type | Add a semantic name or parameter distinction. |
| Tuple or closure components are positional | Label public components and closure parameters. |

## Review Checklist

### Argument Labels
- [ ] First argument follows the correct label rule (grammatical phrase, prepositional, conversion, or labeled)
- [ ] Prepositional labels do not incorrectly group independent arguments
- [ ] Value-preserving conversion initializers omit the first label
- [ ] All non-special-case arguments have labels

### Naming Semantics
- [ ] Mutating methods use imperative verb form
- [ ] Nonmutating methods use -ed/-ing or noun form
- [ ] Mutating/nonmutating pairs follow the correct pattern (verb pair or noun/form-noun pair)
- [ ] Boolean properties read as assertions (`isEmpty`, `isValid`, `contains`)
- [ ] Variables and parameters are named by role, not type

### Documentation
- [ ] Every public declaration has a doc comment
- [ ] Summaries are single sentence fragments ending in a period
- [ ] Summaries describe the correct thing per declaration kind (action, access, creation, entity)
- [ ] Non-O(1) computed properties document their complexity
- [ ] Parameters, return values, and thrown errors are documented with symbol markup

### Conventions
- [ ] Types and protocols use UpperCamelCase; everything else uses lowerCamelCase
- [ ] Acronyms are uniformly cased based on position
- [ ] Default arguments are preferred over method families
- [ ] Overloads do not differ only in return type
- [ ] Protocol names follow the noun (is-a) or suffix (capability) convention

## References

- Naming clarity, role-based naming, weak-type compensation, and terminology: [references/naming-and-clarity.md](references/naming-and-clarity.md)
- Argument label edge cases, parameter naming, and default argument strategy: [references/argument-labels-and-parameters.md](references/argument-labels-and-parameters.md)
- Side-effect naming examples, -ed/-ing decision tree, form- prefix patterns, and factory methods: [references/side-effects-and-mutating-pairs.md](references/side-effects-and-mutating-pairs.md)
- Casing edge cases, complexity documentation, overload safety, tuple/closure naming, and free function exceptions: [references/conventions-and-special-rules.md](references/conventions-and-special-rules.md)
