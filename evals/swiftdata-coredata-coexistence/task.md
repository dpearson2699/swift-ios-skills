# Existing Store Adoption Plan

## Problem/Feature Description

A mature Core Data app wants to introduce SwiftData screens while the existing
stack remains active. The persisted model includes a renamed field and a value
type used for addresses. The team wants a short migration and coexistence note,
not a rewrite of its full Core Data stack.

Explain the ownership boundary and the store and schema alignment work required
before both paths can safely operate on the same data.

## Output Specification

Create `swiftdata-coexistence-plan.md` containing the routing decision, store
configuration, model-alignment checklist, rename handling, and a careful note
about persisted Codable value types.
