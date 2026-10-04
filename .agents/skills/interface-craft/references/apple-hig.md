# Apple HIG: iOS conventions and accessibility

Use for iOS work and relevant Apple interaction principles. For multiplatform work, share the product's identity and task while adapting navigation and controls. These notes do not prescribe an Apple appearance for web or Android.

## Sources and consultation status

Consulted 2026-10-03:

- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/): direct text retrieval required JavaScript; official indexed excerpts exposed hierarchy, harmony, and consistency.
- [Design principles](https://developer.apple.com/design/human-interface-guidelines/design-principles): direct text retrieval required JavaScript; no detailed summary attributed to this page.
- [Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility): direct text retrieval required JavaScript; official indexed excerpts supported text enlargement and Dynamic Type.
- [Buttons](https://developer.apple.com/design/human-interface-guidelines/buttons): official indexed excerpts supported the hit-region and custom press-state guidance below; full page not retrieved.
- [Branding](https://developer.apple.com/design/human-interface-guidelines/branding): official indexed excerpts supported restrained brand color and accessible custom type.
- [Scaling fonts automatically](https://developer.apple.com/documentation/uikit/scaling-fonts-automatically): official indexed content supported Dynamic Type, semantic text styles, and scaling custom fonts; direct body retrieval was unavailable.

These are source-limited summaries, not a complete or version-specific HIG audit. Reopen relevant current documentation in a capable reader when target OS, component behavior, or exact values matter. Record any continuing limitation rather than inventing guidance.

## Official guidance summarized

- Establish a hierarchy that distinguishes controls and foreground content; keep elements coherent with their context and consistent with platform conventions across sizes.
- Use brand color deliberately. A custom brand typeface should remain legible and support accessibility settings.
- Dynamic Type lets people choose text size. Semantic text styles support scaling; custom fonts need corresponding scaling support.
- Apple's button guidance gives a general hit-region target of at least 44 by 44 pt for iOS-context buttons. The interactive region may exceed the visible icon. Custom buttons need a perceptible press state. This is Apple guidance, not a WCAG AA CSS-pixel requirement.

## Skill application heuristics

Preserve system behaviors for navigation/back, sheets, pickers, and dismissal where appropriate to the supported OS. Choose a tab structure for peer destinations and a hierarchy for drill-down tasks; decide from the task rather than from a fixed layout template. Confirm component details against current HIG before specifying version-sensitive styling.

Design with safe areas, software keyboard, orientation, reachable primary actions, and text expansion in mind. Avoid fixed-height text containers that clip at accessibility sizes. Use recognizable platform controls where they already satisfy the task; custom visual identity does not require rebuilding every control.

For native handoff, specify meaningful VoiceOver labels, roles, values, grouped content, reading order, state announcements, and alternatives to gesture-only actions. Represent selected/error states with more than color. Plan reduced-motion behavior and meaningful loading/recovery states. These are skill review prompts, not claims that a mockup validates native behavior.

Verify the implemented main journey with VoiceOver, increased text sizes including accessibility categories, relevant system accessibility settings, safe-area/keyboard conditions, and supported device/window sizes. For Figma, measure visual properties and annotate runtime requirements. Use [quality review](quality-review.md) to distinguish verified behavior from design intent.
