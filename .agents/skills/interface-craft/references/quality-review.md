# Quality review and evidence by delivery mode

Read for interface review and before concluding prototype or implementation work. Review only the requested artifact and relevant journey; do not broaden into a whole-product rebuild.

## Basis and sources

The review method is interface-craft guidance derived from the approved specification, 2026-10-03; it is not an official scoring system. Supporting sources consulted 2026-10-03: [WCAG 2.2](https://www.w3.org/TR/WCAG22/) and [Understanding WCAG 2.2](https://www.w3.org/WAI/WCAG22/Understanding/) for web accessibility, and [Figma MCP documentation](https://developers.figma.com/docs/figma-mcp-server/) for available artifact types. These pages were retrieved. For native source summaries and their limitations, read [Apple HIG](apple-hig.md) or [Material/Android](material-design.md).

## Inspect the relevant journey

- **Task and content:** can the user identify the purpose, perform the primary action, interpret the result, and recover? Are capabilities and example data honestly represented?
- **Composition:** inspect rendered output for hierarchy, readability, alignment, spacing, density, unintended clipping/overlap, and contrast. Check real or representative content, not only short ideal labels.
- **Adaptation:** inspect relevant widths/window sizes, long content, text enlargement, keyboard/insets, and safe areas where applicable. Verify that rearrangement preserves task and meaning.
- **States and interaction:** follow the main path and applicable loading, empty, error, validation, success, disabled, and recovery states. Check focus, feedback, and transitions only where the artifact can demonstrate them.
- **System coherence:** check approved brand continuity or the requested new direction, semantic tokens, repeated components, and actual variants. Avoid a full-library requirement for a small deliverable.
- **Accessibility:** use the web or native reference. Record checks, failures, applicability, and behaviors that remain untested. A pleasing screenshot is not evidence of assistive-technology operation.

## Match the claim to the mode

| Mode | Evidence to gather | Limits to state |
| --- | --- | --- |
| Prototype | Confirmed destination/nodes; editable text and native controls; instances and supported token links; size/state captures; demonstrated prototype routes | Annotation-only behavior; missing MCP capabilities; no proof of APIs, keyboard, runtime performance, or complete WCAG conformance |
| Implementation | Rendered interface; exercised journey/states; pertinent project checks; manual keyboard and web/native accessibility checks; relevant adaptive conditions | Environments and devices not tested; mocked/unavailable services; applicable criteria not verified; automated checks cover only what they detect |
| Review | Reproducible finding at a specific frame, screen, element, or code location; conditions, impact, and evidence | Inspection scope; inability to reproduce or access runtime; proposed fixes versus authorized and verified changes |

Use the repository's established checks when implementing. Choose additional tests only when they verify material behavior or risk; do not add a testing stack merely to satisfy this skill. A build or lint pass supports compilation or static checks, not visual approval. Fix defects within authorized scope and repeat affected checks; broaden only when a new issue justifies it.

## Deliver findings and completion evidence

For a review finding, provide: location, user impact, observed behavior/evidence, expected behavior and relevant criterion/source, severity, and a concrete correction. Prioritize blocked tasks, lost information, and accessibility barriers before polish. Distinguish preference from defect and uncertainty from confirmed failure. Apply corrections only when requested or otherwise within existing authorization.

Conclude with the artifact or confirmed link, decisions relevant to the brief, verified states and conditions, remaining limits, and the next practical step. If an artifact cannot be created or inspected, report the blocked or incomplete portion directly. Never fabricate successful verification, user research, measurements, or remote tests.
