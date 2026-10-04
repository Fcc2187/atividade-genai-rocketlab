---
name: interface-craft
description: "Use when designing, prototyping in Figma MCP, implementing, or reviewing product interfaces for web, iOS, or Android, including visual direction, interaction states, design systems, and accessibility. Does not apply to backend-only work or standalone artwork."
---

# Interface Craft

Create useful, accessible interfaces with an identity chosen for the product. Adapt interaction to the platform; share intent and brand across platforms without forcing identical screens. This skill supplies a method and references, not a framework, brand, component kit, or MCP connection. Communicate and write microcopy in the user/product language.

## Choose the mode and references

| User intent | Mode | Delivery |
| --- | --- | --- |
| Design editable screens or flows in Figma | Prototype | Native editable nodes, relevant states, visual foundations, supported interactions or flow annotations |
| Build or change the interface in a project | Implementation | Rendered interface in the chosen stack, working states and appropriate project checks |
| Inspect an existing interface | Review | Located findings, evidence, impact, and corrections only within the authorized scope |

Read references when they affect the task, rather than loading the whole package:

- [Visual direction](references/visual-direction.md): new identity, composition, content, or a visual restart.
- [Apple HIG](references/apple-hig.md): iOS conventions and native accessibility; selected principles for web.
- [Material Design 3](references/material-design.md): Android conventions, adaptation, and semantic tokens; selected principles for web.
- [Web accessibility](references/web-accessibility.md): web WCAG 2.2 AA design and verification, including annotations for web prototypes.
- [Figma workflow](references/figma-workflow.md): any Figma prototype or edit.
- [Quality review](references/quality-review.md): review mode and verification before completing any mode.

## Work from the brief to evidence

1. State the understood task and success criterion briefly. Use available audience, primary task, real content, platform, stack, constraints, and artifacts. Ask only about missing information that materially changes a decision; reuse answers and existing authorization. Limit work to the requested screen, flow, or review.
2. Distinguish functional contracts from visual references. Preserve an approved brand or system when continuity is requested. For a visual restart, read requirements and APIs without using the old interface or discarded references as composition models. Preserve functionality unless its change is requested.
3. Select a deliberate direction. Offer two or three alternatives only when identity is open and comparison helps. Explain composition, typography, density, color, imagery, and behavior through the primary task. Familiar controls can support an original composition; decorative effects need a purpose.
4. Resolve hierarchy, navigation, the primary action, and relevant states before polish. Choose tables, lists, cards, and charts by the information. Include loading, empty, error, validation, success, unavailability, and recovery when applicable. Label synthetic content. Represent actual contracts; do not invent metrics, API behavior, processing progress, or user research.
5. Define semantic color, type, spacing, radius, border, and motion tokens. Add components and variants for real reuse and states. Account for long content, text enlargement, reduced motion, and pertinent sizes. Add themes or libraries only when needed. Implement in the user's stack, following repository conventions, or execute the Figma reference workflow.
6. Inspect rendered output and the main journey, fix concrete defects, and rerun affected checks. Report the artifact/link, decisions, verified states and conditions, and remaining limits. A successful command is evidence for that command, not visual quality or complete accessibility.

## Platform and evidence boundaries

Respect user instructions, functional constraints, and accessibility commitments. Within those limits, preserve approved identity and apply platform conventions. Explain contextual conflicts rather than blending Apple and Material appearances by obligation.

Use web semantics and WCAG 2.2 AA for web; Apple conventions and VoiceOver/text scaling for iOS; Material/Android conventions and TalkBack/font scaling for Android. Keep CSS px, Apple pt, and Android dp/sp in their own contexts. Verify current official documentation for version-dependent decisions. Label official guidance, skill heuristics, consultation dates, and inaccessible sources.

A prototype demonstrates only supported, inspected interactions. Annotate focus order, accessible names, roles, announcements, and behaviors still requiring code verification. Screenshots do not establish API operation, keyboard support, performance, or WCAG conformance. Discover Figma capabilities locally and use installed official Figma skills when available; never invent tools, parameters, links, IDs, or successful mutations. This skill does not install or authenticate MCP servers.
