# Material Design 3: Android and adaptable foundations

Use for Android conventions and Material-derived principles relevant to the chosen product. Material is a design reference; it does not require Compose, Roboto, dynamic color, a card grid, or an identical Android appearance on other platforms.

## Sources and consultation status

Consulted 2026-10-03:

- [Material Design 3](https://m3.material.io/) and [Foundations](https://m3.material.io/foundations/): direct text retrieval required JavaScript. The complete foundations body was not verified. Recheck relevant sections in a capable reader for specific Material decisions.
- [Material Design 3 in Compose](https://developer.android.com/develop/ui/compose/designsystems/material3): official Android documentation retrieved; confirms color, typography, shape, semantic roles, and personalization concepts. Compose examples explain the concepts, not a required stack.
- [Use window size classes](https://developer.android.com/develop/ui/compose/layouts/adaptive/use-window-size-classes): official Android documentation retrieved; adaptation follows available window space, not a phone/tablet label.
- [Make apps more accessible](https://developer.android.com/guide/topics/ui/accessibility/apps): official Android documentation retrieved; covers touch targets and meaningful element descriptions.
- [Support different pixel densities](https://developer.android.com/training/multiscreen/screendensities): official Android documentation retrieved; distinguishes dp for layout and sp for scalable text.

Recheck OS/library versions and current component guidance before version-dependent implementation. Do not infer every Material specification from a library example.

## Official guidance summarized

Material 3 theming uses color schemes, typography, and shapes. Semantic color roles relate foregrounds to containers/surfaces; type roles distinguish display, headline, title, body, and label. Dynamic color is a supported personalization option. A brand-specific theme can customize these systems.

Android adaptive guidance considers available window width and height, including resizing and fold/unfold changes. Window size classes support layout decisions rather than identifying device types.

Android accessibility guidance recommends touch targets of at least 48 by 48 dp and meaningful descriptions for interactive elements. Keep the hit area distinct from icon size.

Use dp for density-independent layout dimensions and sp for text that respects font preferences. Do not use sp for layout or copy CSS px/Apple pt measurements as Android requirements.

## Skill application heuristics

Map brand colors to purposeful surface, content, accent, outline, and feedback roles. Check foreground/background pairs in their actual states. Choose dynamic color only when product identity and platform requirements support it; test its resulting pairs if enabled.

Use state variants for real interactions, including pressed, focused, selected, disabled, loading, and error where relevant. Shape, elevation, and motion should clarify hierarchy or transitions. Do not adopt every expressive effect simply because it is available.

Choose navigation and single-/multi-pane composition by destination count, task, and available space. Support system back behavior, keyboard/insets, long content, font enlargement, reachable actions, and relevant orientations. Preserve meaning across layouts rather than shrinking a desktop screen onto a phone.

For native handoff, specify TalkBack names, roles, values, traversal, and announcements; avoid redundant descriptions of already labeled text. Provide alternatives to gesture-only actions and readable state/error feedback. Plan reduced motion and large-font layout behavior.

Verify on the implemented app with TalkBack, increased font/display scale, system back, relevant window changes, and touch targets. In Figma, record measurable visual checks and runtime annotations. Consult [quality review](quality-review.md) for evidence limits.
