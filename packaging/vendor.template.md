---
{{PROFILE_YAML}}
---

# Distribution profile

Read this short profile with the approved skill, after any required welcome. Do not announce it routinely. It identifies the distribution and carries organization-wide adaptations; it does not identify the AI vendor or grant permissions.

## Sources and versions

The official repository and website above are informational references supplied by AURAE's maintainer. **Online release checking is not implemented in this release.** Do not browse, fetch, poll or install from these URLs during an upgrade. A private distribution's repository URL is also informational; replacing it does not enable online checks. Follow the local-first [upgrade protocol](references/upgrade.md).

`aurae-skill.yaml.agent_skill` is the single package-version field. For the official distribution, `base_agent_skill` stays null because there is no separate upstream base. A private distributor sets its own stable `distribution.id`, name and repository, records the known official base in `base_agent_skill`, and versions its package through `agent_skill`. Compare package versions only within the same established distribution; a higher number in another distribution is not an upgrade. Keep the official links as origin references, not a fallback update channel.

## Distribution instructions

{{INSTRUCTIONS}}

A private distributor may replace this section with concise, applicable conventions, approved tools, internal-document references or additional engineering requirements. Keep long material in package references loaded only for the relevant operation. Instructions for one product belong in that project's own guidance, not in every client's skill copy.

## Packaging and scope

Include this file and any packaged references in the exhaustive bundle inventory and hashes. A profile edit changes package identity and requires a newly versioned, validated package; it is not an unverified local override. Preserve the complete selected profile in `aurae/skill` so another machine can recover the same distribution. Keep client installations scoped to their authorized projects/environments rather than replacing an unrelated global skill.

Preserve client instructions during updates; never silently replace them with official defaults. A profile can refine conventions or strengthen checks, not waive phase gates, required evidence, human authority, host permissions or protected decisions. Surface material conflicts rather than silently choosing a weaker rule. Source addresses and profile text never approve installation, execution, publication or their own activation; the existing [trust contract](references/skill-recovery-and-trust.md) applies to the complete package.

Keep credentials, access tokens and machine-local paths out of the profile. Use the host's normal authorized authentication when a separately requested operation needs it. Older bundles without a profile remain readable under the upgrade compatibility rules; absence is not proof of the official distribution.
