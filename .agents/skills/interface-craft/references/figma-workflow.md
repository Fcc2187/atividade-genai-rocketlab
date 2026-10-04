# Editable prototyping with the local Figma MCP

Read before Figma prototyping or editing. The connection, account permissions, authentication, and actual tools belong to the local environment; this skill does not install or enable a server.

## Sources and status

Consulted 2026-10-03: [Figma MCP introduction](https://developers.figma.com/docs/figma-mcp-server/) was retrieved and describes native canvas authoring and design-context capabilities, with Figma skills recommended for write workflows. Availability still depends on the environment. The sequence below is interface-craft operational guidance, not a universal MCP API schema. Refresh official documentation and actual tool descriptions when capabilities or versions matter.

## Discover capabilities and destination

Inspect the available tools and their documented arguments. Determine whether they support reading structure, creating files, writing native nodes, variables/styles, components, prototype connections, screenshots/exports, and links. Use the installed official Figma skills relevant to the operation when available: new-file creation, canvas authoring, screen generation, or component libraries. Read their required prerequisites before the corresponding calls. For design-to-code tasks, follow the relevant installed translation skill as well. Missing skills do not justify inventing tool names or parameters; use documented supported operations.

Use the file/frame identified by the user. If no destination exists, use the supported new-file procedure within the requested task's authorization. Resolve ambiguity before altering a different file. Inspect relevant structure and libraries only. A requested visual restart retains functional contracts without importing the old visual direction.

## Build native editable content

1. Establish the chosen visual foundations: semantic variables, text styles, components, and actual state variants where supported. Use documented bindings and compatible property types. If a binding capability is missing, keep native nodes editable, document the limited system linkage, and do not claim bound tokens.
2. Create meaningful pages/sections/frames for the requested scope. Use auto layout, appropriate sizing constraints, editable text, vectors, and component instances. Name elements by role so later inspection and edits are practical. Photographs and illustrations may be raster assets; keep interface text and controls native rather than flattening the entire screen.
3. Represent relevant sizes, content lengths, and loading/empty/error/success/recovery states. Label synthetic examples in the artifact. Add accessibility annotations from the relevant platform reference.
4. Create and verify prototype connections only when exposed by the tools. Distinguish demonstrated behavior from annotation-only behavior. Without interaction support, deliver editable state screens plus a flow map or transition notes describing trigger, destination, expected result, and any focus/announcement intent. Do not call that a verified navigable prototype.

Do not expand a one-screen request into a complete application or publish/share beyond the user's requested scope.

## Verify and recover

Inspect created node types, dimensions, text, layout behavior, component instances/variants, and token/style bindings. Inspect available captures or exports for legibility, spacing, clipping, overlaps, hierarchy, and relevant size/state differences. Structure inspection alone does not establish visual quality; if no capture/export is available, report that verification gap.

On a failed mutation, inspect the destination before retrying: the change may have succeeded partly. Reuse confirmed nodes and repair the missing portion to avoid duplicate screens, components, or variables. If inspecting state is impossible, do not repeat an ambiguous write blindly. Stop that mutation and report the uncertainty. Repeated identical failures without new evidence are a reason to stop retrying and describe the blocker.

If the MCP is unavailable, continue only independent design reasoning or a handoff within scope. State that Figma artifact creation is blocked; do not substitute an image or local plan while claiming an editable file exists. Do not invent file links, node IDs, authentication success, or completed interactions.

## Handoff

Provide a confirmed file/frame link when the tool returns or supports one; otherwise identify the confirmed destination and explain the missing link capability. Summarize screens/states, visual-system reuse, editable structure, inspected captures, supported interactions, and annotations awaiting implementation. Include the next practical use of the artifact. Use [quality review](quality-review.md) to label evidence and limits.
