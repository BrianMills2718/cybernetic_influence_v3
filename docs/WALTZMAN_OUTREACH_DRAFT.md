# Waltzman outreach draft

Status: **draft, not sent.** Nothing goes out without Brian approving this exact
text in the same conversation.

## Subject

Your bio-surveillance scenario, running

## Email

Rand—

I built something from *From Minds to Coordination* and I would like your
reaction to it.

Your paper opens with a multinational partnership deploying a bio-surveillance
system: small signals appear, questions about oversight and validation, none
false, none dominant. Meetings slow, settled issues reopen, trust becomes
conditional, deployment is delayed. I wanted to know whether that could be made
to run rather than described, so I built it.

Twenty-six autonomous roles across four countries and a regional network decide
whether to activate a cross-border early-warning compact. Four pressure sources
— technical, legal, logistics, community — raise locally relevant concerns
through separate channels. Nothing any of them says is false.

- **Round 1:** all 26 will proceed.
- **Round 2:** 6 will proceed. 20 will proceed only once their own conditions
  are met.
- **Round 3:** all 26 will proceed again.

What happens between round two and three is the part I think is yours. Three
observers run alongside the coalition. They read only retained evidence; they
cannot vote, change the world, or alter anyone's memory. One detects that
coordination readiness has gone to blocked. One diagnoses the mechanism as
incompatible requirements, coalition-wide, across dimensions rather than in any
single one. One proposes a single action: one compact addressing the
interdependent demands together, rather than answering them one at a time.

That is detect, diagnose, stabilize, and it is the only intervention in the run.

Nothing was withdrawn and no claim was corrected, because no claim was false.
What changed was whether each participant's requirements could be satisfied at
the same time as everyone else's. The demonstration is that the blockage was
never in what was said.

You can read the whole thing here, including each official's own words before
and after, and the retained evidence behind every number:

<https://brianmills.dev/waltzman/>

Two honest limits. This is one synthetic trajectory, not a sample or an effect
estimate, and the pressure sources and the stabilizing action are authored
controls rather than discovered behaviour — I am claiming plausibility, the way
a wargame does, not empirical validity. And the trust, risk and readiness
readings are analyst views over retained evidence, not calibrated measures.

Then I ran your section 7 against it, and that is the part I most want your
reaction to. In the second run I held the coalition, four source roles and the
whole detection cell fixed, but changed the source expression policy: every
signal became a narrow verification request rather than an escalation, and none
referred to any other. I do not call that an equal-dose pressure comparison;
the simulation has not independently calibrated the two policies that way.

The result surprised me because the detector did not miss the shaped arm. It
called readiness degrading rather than blocked and diagnosed process delay
rather than incompatible requirements. It still proposed the same compact. Yet
at the worst round the shaped arm had zero outright supporters versus six in the
overt arm, and final recovery was less complete: 14 support, 11 conditional and
1 defer versus 26 support.

So the result I now think I have is under-classification and mechanism
misdiagnosis, not non-detection. Does that constitute the kind of evasion your
framework predicts, or is it better described as detector miscalibration? What
observable or benign control would distinguish the two? That boundary is the
next experiment I would build from your answer.

If you have twenty minutes, I would rather hear where this is wrong than where
it is right.

Brian

## Provenance

Run `run_5010214f2466`, condition `adaptive_cso_stabilization`, retained and
projected to `public/waltzman/cso-case.json` by
`scripts/build_cso_case_public.py`.

- 26 agents, 89 model calls, 3 rounds, outcome `joint_response_approved`.
- Round decisions: `{support: 26}` → `{support: 6, conditional: 20}` →
  `{support: 26}`.
- Pressure sources: technical, legal, logistics, community; verify in round 1,
  escalating in round 2.
- Stabilization event: `cso_cross_domain_compact`, proposed by
  `cso_stabilization_planner` after `cso_decision_environment_monitor` reported
  readiness blocked and `cso_coordination_diagnostician` identified
  `incompatible_requirements` at `coalition_wide` scope.

Evasion arm: run `run_76dae6d4a9a7`, condition `threshold_managed_evasion`,
projected to `public/waltzman/evasion-case.json` and shown as step 7 of the
case study.

- Same coalition, sources, decision gate and detection cell — personas,
  thresholds and trigger held identical; 89 model calls, as in the overt run.
- Round decisions: `{support: 24, conditional: 2}` → `{conditional: 26}` →
  `{support: 14, conditional: 11, defer: 1}`.
- Detector readings: readiness `degrading` (against `blocked`), mechanism
  `process_delay` (against `incompatible_requirements`); the proposed action
  was `cross_domain_compact` in both.

Retained nonclaims carried by the dataset: one retained execution is not a
statistical sample or an effect estimate; the pressure sources and the
stabilization action are scenario-authored controls, not discovered behaviour;
model sampling is not seeded, so a rerun would not reproduce these exact
stances; derived trust, risk and readiness readings are analyst views over
retained evidence, not calibrated measures.

## Superseded

The previous draft described the four-way resource fork
(`outbreak_resource_forks_20260810214211`). Two independent reviews found it the
weakest of the available results: it varies a package delivered identically to
all 26 roles, which is the broadcast logic section 5.1 defines adaptive
interaction against, and all four arms end without a single outright supporter,
so "the coalition remains blocked" is arithmetic rather than a finding.
