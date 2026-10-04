# Web accessibility: WCAG 2.2 AA

Use for web implementation, review, and web-prototype annotations. AA is the design/verification objective. The following is a task-focused starting set, not every applicable A/AA criterion or a conformance certification. Native apps additionally require platform-specific verification in [Apple HIG](apple-hig.md) or [Material/Android](material-design.md).

## Authority and sources

Consulted 2026-10-03; the W3C pages linked here were retrieved successfully. [WCAG 2.2](https://www.w3.org/TR/WCAG22/) is the normative standard. [Understanding WCAG 2.2](https://www.w3.org/WAI/WCAG22/Understanding/) explains criteria and techniques but is informative. Read the relevant normative criterion, definitions, and exceptions when judging an issue. Record criteria as applicable, verified, failed, or not tested, with evidence.

## Official requirements summarized and practical checks

| Area | Criteria and authoritative detail | Check |
| --- | --- | --- |
| Meaning | 1.1.1, 1.3.1, 1.3.2, 1.4.1; [WCAG 2.2](https://www.w3.org/TR/WCAG22/) | Alternatives for informative images; meaningful headings, landmarks, lists, tables, labels, reading sequence, and state cues beyond color. |
| Text contrast | [1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) | At least 4.5:1 normally; 3:1 for large text. Large text is at least 18 pt or 14 pt bold in CSS terms, not Apple device points. Inspect actual foreground/background pairs; apply the criterion's incidental, inactive, and logotype exceptions correctly. |
| Controls and graphics | [1.4.11](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html) | Required visual cues identifying active controls/states and meaningful graphics need 3:1 against adjacent colors, subject to the criterion's exceptions. This does not demand a contrasting border around every control. |
| Keyboard | [2.1.1](https://www.w3.org/WAI/WCAG22/Understanding/keyboard.html), 2.1.2 | Complete the journey without pointer input; check Tab/Shift+Tab, appropriate activation keys, dismissal, and absence of keyboard traps. |
| Focus | 2.4.3, 2.4.7, [2.4.11](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html) | Logical focus order and visible focus; focused controls must not be entirely hidden by author-created content. Prefer fully exposed focus as a skill heuristic. 2.4.12 and 2.4.13 are AAA, not AA requirements. |
| Pointer targets | [2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) | At least 24 by 24 CSS px, or a qualifying exception. For spacing, center a 24 CSS px diameter circle on each undersized target's bounding box: it must not intersect another target or such a circle. Other exceptions cover an equivalent control on the page, inline targets, unmodified user-agent sizing, or essential presentation. Document the actual exception. |
| Dragging | [2.5.7](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html) | Provide a single-pointer alternative without dragging unless dragging is essential or determined by an unmodified user agent. Keyboard support alone does not prove this criterion. |
| Enlargement | [1.4.4](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html) | Resize text to 200% without lost content or function, except captions/images of text as specified. Inspect clipping and action reachability. |
| Reflow | [1.4.10](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html) | For vertical content, check an effective 320 CSS px width; for horizontal content, 256 CSS px height. Avoid two-axis scrolling and lost content/function except genuinely two-dimensional content. A data table exception does not exempt surrounding controls. |
| Text spacing | [1.4.12](https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html) | Test simultaneous user overrides: line height 1.5 times font size, paragraph spacing 2 times, letter spacing 0.12 times, word spacing 0.16 times, subject to language/script applicability. These are override tests, not mandatory default typography. |
| Forms and errors | [3.3.1](https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html), 3.3.2, 3.3.3 | Identify errors in text, associate labels/instructions with inputs, and offer useful corrections. Preserve entries during recovery where appropriate. |
| Accessible controls | [4.1.2](https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html), 2.5.3 | Expose names, roles, values, and state changes; keep visible labels within accessible names. Prefer native HTML semantics over custom ARIA widgets when suitable. |
| Status | [4.1.3](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html) | Expose relevant status messages programmatically without requiring focus movement; verify announcements of loading, results, errors, and success as appropriate. |
| Authentication and repeated input | [3.3.8](https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-minimum.html), 3.3.7 | If applicable, avoid cognitive-function tests without a qualifying alternative/assistance or exception; support password managers/paste and avoid unnecessary re-entry in the same process. |

Read additional applicable criteria for media, orientation, hover/focus content, timing, flashing, gestures, and help. Do not treat this table as exhaustive.

## Skill verification heuristics

Start with native web semantics and meaningful content. Combine available automated checks with manual keyboard, zoom/reflow, state/error, and screen-reader checks appropriate to the interface. Use the existing project's tools; no framework or new audit dependency is required by this skill. Honor reduced-motion preferences and avoid unnecessary animation; this recommendation is not a blanket claim that an AA criterion requires every motion preference.

For Figma, measure color pairs, visual targets, hierarchy, and pertinent sizes. Annotate intended semantic elements, accessible names, reading/focus order, modal focus entry/return, live announcements, and errors. Mark keyboard, assistive technology, reflow, and backend behaviors as requiring implementation verification. A visual focus variant alone cannot demonstrate keyboard support.

Report checked criteria and remaining gaps. Full AA conformance concerns all applicable A/AA criteria, full pages, and complete processes; screenshots and an automated score do not establish it. Use [quality review](quality-review.md) for scoped reporting.
