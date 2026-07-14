# SwiftData Cloud Sync Model Review

## Problem/Feature Description

An iOS app is enabling cloud sync for an existing SwiftData model. The model
uses a uniqueness constraint for an email address, a required owner
relationship with a restrictive delete rule, and an image blob stored directly
on the record. A teammate proposes making every scalar property optional to
make the schema sync.

Review the model and provide a corrected sketch plus a rollout checklist.

## Output Specification

Create `swiftdata-cloud-schema-review.md` with the incompatible model features,
a concise corrected model outline, and the required capability and deployment
considerations.
