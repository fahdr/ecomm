# Project Instructions

## Documentation Requirements

When creating or modifying features, always produce documentation for these four audiences:

1. **Developer** — implementation details, API contracts, architecture decisions. Target: engineers building and maintaining the code.
2. **Project Manager** — feature scope, progress milestones, dependencies. Target: non-technical stakeholders tracking delivery.
3. **QA Engineer** — test plans, edge cases, acceptance criteria. Target: testers validating quality before release.
4. **End User** — workflows, UI behavior, feature guides. Target: merchants using the dashboard and storefront.

Place per-service docs in `<service>/docs/` (e.g., `trendscout/docs/DEVELOPER.md`). Place cross-cutting architecture docs in `plan/`.

## Code Quality

- Every function, method, and class MUST have a docstring covering purpose, parameters, and return values.
- Add inline comments only for complex logic or non-obvious decisions — do not comment self-explanatory code.

## Workflow Rules

These apply to every task:

1. **Plan first** — add implementation steps to `plan/` or the relevant service's `docs/IMPLEMENTATION_STEPS.md` before writing code.
2. **Write comprehensive tests** — every feature or fix must include tests. Follow the schema-based test isolation pattern (see memory).
3. **Update docs** — after any code change, update all affected documentation (developer, PM, QA, end-user).
4. **Update memory** — record key decisions, patterns, and lessons learned in the auto-memory directory.

## UX Validation

When building or modifying UI, manually trace the user's journey:

1. Identify every interactive element (button, input, link, toggle) on the affected page.
2. Determine the intent of each element — what should happen when a user interacts with it?
3. Trace the full flow: what screen comes next? What data changes? What feedback does the user see?
4. Verify the flow end-to-end by checking the relevant backend endpoints and frontend state.

### Accessibility & Contrast Checks

Always verify text remains readable against its background:
- Never place dark text on a dark background or light text on a light background.
- Test both light and dark themes when the app supports theme switching.
- Use sufficient color contrast (WCAG AA minimum: 4.5:1 for normal text, 3:1 for large text).

## Frontend Aesthetics

Avoid generic "AI slop" design. Every frontend should feel intentionally crafted.

### Typography
- Choose distinctive, beautiful fonts. **Never default to** Inter, Roboto, Arial, or system fonts.
- Vary font choices across services — do not reuse the same font (e.g., Space Grotesk) everywhere.

### Color & Theme
- Commit to a cohesive palette using CSS variables.
- Use dominant colors with sharp accents — avoid timid, evenly-distributed palettes.
- Draw inspiration from IDE themes, cultural aesthetics, and real-world brand identities.
- **Never use** the cliched purple-gradient-on-white pattern.

### Motion & Animation
- Use CSS-only animations where possible; use the Motion library (framer-motion) in React.
- Focus on high-impact moments: a well-orchestrated page load with staggered `animation-delay` creates more delight than scattered micro-interactions.

### Backgrounds & Depth
- Create atmosphere with layered CSS gradients, geometric patterns, or contextual effects.
- Never default to flat solid-color backgrounds when depth would improve the design.

### Anti-Patterns to Avoid
- Overused font families (Inter, Roboto, Arial, system fonts, Space Grotesk)
- Cliched color schemes (purple gradients, generic blue-and-white)
- Predictable component layouts that look like every other AI-generated UI
- Cookie-cutter designs that ignore the service's specific context and personality

### e2e tests
1. Always create or update e2e test for every new change and test
2. While designing the tests refer to the UX validation guideline in CLAUDE.md and design in e2e so that we are covering all parts the code both frontend and backend
3. Make sure to seed data where eer necessary so that the e2e tests can be designed more thoroughly
4. Run e2e tests with less workers so that we do not crash the system. Use makefile to run the tests in the background so that we can read output from log file