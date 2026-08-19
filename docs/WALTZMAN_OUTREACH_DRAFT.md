# Waltzman outreach draft

## Subject

An executable demonstration inspired by *From Minds to Coordination*

## Email

Rand—

I built a small multi-agent simulation inspired by *From Minds to
Coordination*, and I would value your reaction to whether it captures the
mechanism you had in mind.

Twenty-six autonomous AI roles across four countries and a regional institution
decide whether to activate a cross-border early-warning compact. Local pressures
enter through separate channels—laboratory failures, staffing shortages, supply
constraints, legal demands, contested evidence—and by round two the coalition is
stuck: 23 of 26 roles will proceed only conditionally, 3 defer, nobody supports
outright.

Then I did the thing I actually wanted to test. I saved the simulation at that
exact point and continued it four ways. Same agents, same memories, same prior
messages, same world state, same model and prompts, same approval rule. The only
difference is which resource package arrives:

| Continuation | Resources | Audit | Final stances | Approved |
| --- | --- | --- | --- | --- |
| No package | none | absent | 21 defer, 5 conditional | no |
| Partial | 2, verified | verified | 23 conditional, 3 defer | no |
| Complete | 6, verified | verified | 24 conditional, 2 defer | no |
| False claims | 6, claimed | contradicted | 21 defer, 5 conditional | no |

None of them approved. The gate needs 13 outright supporters and no branch
produced a single one.

The negative result is not the interesting part. What changed is *which*
constraint was binding. With no package, 24 of 26 roles named capacity as their
top risk and 14 asked for resources. With the complete verified package,
capacity fell to 9, evidence quality rose to 9, sovereignty to 5, and requests
shifted from resources (3) to safeguards (12). Solving the resource problem did
not unblock coordination—it moved the blockage to legal authority and
evidentiary standards that had been sitting underneath the whole time.

The false-claim branch is the other result I did not expect. Once the simulated
audit contradicted the fabricated manifest, the coalition landed on exactly the
no-package profile: the same 21/5 split, and all 26 roles back to naming
capacity. Claiming resources you cannot substantiate was worth precisely as much
as providing nothing.

The claim is deliberately narrow: this is a synthetic mechanism demonstration,
not evidence about human institutions. It is one scenario with one trajectory
per branch and unseeded model sampling. What I think it does offer is a
substrate where the roles, information paths, decision rules, retained
rationales, and the fork point itself are all inspectable rather than collapsed
into a summary.

Research case:
<https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=case>

My main question is whether this is a faithful minimal operationalization of
your shift from influence on beliefs to influence on the decision environment—
and in particular whether "the intervention worked and revealed the next
constraint" is the shape you would expect. If you have 20 minutes, I would be
glad to walk through it and hear what you would change in the next experiment.

Best,

Brian

## Provenance

Experiment `outbreak_resource_forks_20260810214211`, retained at
`public/waltzman/resource-fork.json` and rendered at `?view=case`.

- 26 agents, `codex/gpt-5.6-luna` at medium reasoning, 160 total model calls,
  observed cost $0 (subscription-included).
- Shared checkpoint digest
  `390dd40850fa118d89c673a37da925f7ab9d85adf31c75cba35fe5fc289e71ad`,
  reached after 56 model calls; all four branches continue from that digest.
- Coalition gate: minimum 13 support, minimum 20 support-or-conditional,
  maximum 2 oppose.
- Shared round-two state before the fork: 23 conditional, 3 defer.

Retained nonclaims carried by the dataset: one retained execution is not a
statistical sample or human-behavior estimate; the packages and resource
mechanics are scenario-authored experiment controls; only the final-round
continuations are checkpoint-paired, and model sampling is not seeded.
