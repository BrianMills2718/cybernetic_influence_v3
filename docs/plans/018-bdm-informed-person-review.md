---
doc_role: implementation_plan
authority: bounded_design
status: completed
created: 2026-07-25
updated: 2026-07-25
---

# Slice 18: BDM-informed person review

## Outcome

An analyst who authors a scenario can inspect and directly edit what the model
assumes about each person before approving the scenario. The same typed person
model is available to conversational revisions. It is expressed as descriptive
statements such as “Alice is skeptical of official sources,” never as hidden
commands telling Alice what action to take.

This is a PoC authoring and review slice. It makes the current person assumptions
tractable and establishes the contract needed by a later live-authored-person
slice. The existing authored reference workflows remain scripted and zero-cost;
this slice does not claim their actions vary because of the person profile.

## Source and landscape disposition

Landscape disposition: `linked`.

The person vocabulary is informed by Vincent Petit’s 2019 UNICEF
*Behavioural Drivers Model*. The BDM is used as a behavior-specific checklist,
not a complete psychological theory or causal blueprint. Its own limitations
say that the drivers are entangled, not all matter in every situation, and their
importance and causality require contextual evidence.

The existing V3 ontology remains authoritative:

- internal descriptions and retained beliefs belong to a concrete person;
- perceived social conditions belong to the person and may be wrong;
- actual relationships, information deliveries, incentives, policies,
  mechanisms, resources, and physical constraints remain external world state;
- analytical boundaries remain execution-inert views.

## Target artifact

For the canonical information-campaign example, the draft review shows a card
for the campaign operator and recipient. Each card exposes:

- label and position;
- one concise “Person is…” disposition;
- memories;
- values;
- goals;
- beliefs;
- decision tendencies;
- perceived social conditions;
- current state;
- described capabilities;
- described limitations.

Every statement is directly editable. Saving a card validates and persists one
new draft revision without a provider call, invalidates any earlier approval,
refreshes the compiled preview, and leaves a visible conversation entry.

## Boundary table

| Target behavior | Source/state | Owning operation | Contract | Acceptance |
|---|---|---|---|---|
| Generated people contain reviewable behavioral assumptions | User request and retained prior draft | Structured authoring call | `PersonDraft.behavioral_profile` | Provider schema requires the profile keys |
| Old retained drafts remain readable | Missing profile in an older proposal | Domain-model defaults | `BehavioralProfileDraft` | Legacy fixture validates with empty profile lists |
| Human edits a person without LLM spend | Current draft revision and submitted person | `DraftAuthoringService.edit_person` | `PUT /api/authoring/drafts/{draft_id}/people/{person_id}` | Revision advances once, attempt count and observed cost do not change |
| Stale or malformed edits do not overwrite state | Optimistic revision and typed request | Draft store and API | `DraftPersonEditRequest` | Stale edit returns 409; invalid edit returns 422 |
| Review remains understandable | Current proposal | Existing authoring screen | Person cards below proposal summary and before maps | Rendered user can read, expand, edit, and save a person |

## Person contract

`position`, `disposition`, and `memories` remain compatible with Slice 17.
`behavioral_profile` adds typed lists:

```text
values
goals
beliefs
decision_tendencies
social_perceptions
current_state
capabilities
limitations
```

The producer-facing schema requires every list to be present. Empty lists are
allowed when a category is not relevant; the prompt tells the authoring model
not to manufacture exhaustive detail. The strict stored proposal forbids
unknown fields. Older proposals receive empty lists through domain defaults.

Statements are scenario assumptions, not psychometric measurements. A described
capability does not create an interface, permission, credential, or successful
effect. A social perception is a person’s belief, not proof that the external
norm or relationship exists.

## Critical flow

1. The analyst describes a scenario or opens a retained draft.
2. The authoring model returns the typed scenario and person profiles.
3. The review shows concise person cards before spatial and interaction maps.
4. The analyst expands a card and edits declarative statements directly.
5. Save calls the typed person-edit endpoint with the current draft revision.
6. The API validates the complete person and proposal, advances the revision,
   removes approval, and returns the retained draft.
7. The UI refreshes the same proposal, cards, and compiled maps.
8. A later chat message receives the edited proposal as prior state and may
   revise the same fields.

## Failure behavior

- No valid proposal: person cards remain absent; diagnostics remain primary.
- Empty required scalar or invalid person ID: reject with 422 and preserve the
  prior draft.
- Stale revision or reused edit ID with different content: reject with 409.
- Preview compilation failure after an edit: reject the edit; never retain an
  unpreviewable replacement.
- Network failure: retain the unsaved values in the browser and show the error.

## Acceptance and disproof

Pass when:

- a structured fixture and a real authoring draft expose the new profile;
- a direct card edit produces one retained revision with no new LLM attempt or
  observed provider cost;
- a subsequent chat revision receives and preserves or intentionally changes
  the edited fields;
- the rendered desktop flow shows readable cards, direct fields, save feedback,
  and the maps below them;
- focused and full repository tests pass.

Disproof:

- users must edit JSON;
- the UI presents perceived norms as external facts;
- descriptive capabilities grant runtime interfaces or authority;
- direct edits silently call an LLM;
- old retained drafts become unreadable;
- the scripted reference result is described as psychologically caused.

## Deferred

- autonomous LLM execution of authored people;
- evidence-weighted or empirically calibrated driver strengths;
- per-statement provenance and confidence;
- a universal personality taxonomy or all Level 2 BDM drivers;
- intervention recommendation or automatic psychological causal claims.

The promotion trigger for live authored people is a reviewed profile whose
contents can be passed through the existing observation/interface boundary and
whose decision trace can identify the retained context it used without turning
descriptions into procedural commands.

## Implementation evidence

- The provider-facing JSON Schema requires all eight behavioral-profile
  categories and rejects blank statements.
- `draft_f399326758a6/revision/1/attempt/1` used OpenRouter Sol with medium
  reasoning and native JSON Schema to produce two complete person profiles.
- The direct revision of Elena Brooks advanced the retained draft once with no
  trace ID and no additional observability record. A subsequent OpenRouter
  Terra revision preserved that direct edit while adding only the requested
  value to Mikhail Orlov.
- After prompt tightening, `draft_b251a6e7207d/revision/1/attempt/1` produced
  only in-world dispositions, beliefs, current states, capabilities, and
  limitations; it did not describe either person as a model, template role, or
  trace component.
- Focused authoring tests, the full Python regression, focused strict typing,
  JavaScript syntax checking, the deployment-script syntax check, and the
  production graph build passed.
- A rendered desktop review showed the conversation, concise two-person review
  cards, expandable direct-edit controls, and the configured-interaction map in
  one authoring flow.

The existing broad `api.py` type check still reports its pre-existing
scenario-preview narrowing errors. No new error is in the changed authoring
models, service, store, or focused tests.
