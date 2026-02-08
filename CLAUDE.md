Write docs for types of users.
1. **Developer**: A software engineer who will be working on the codebase, implementing features, fixing bugs, and maintaining the project.
2. **Project Manager**: A non-technical stakeholder responsible for overseeing the project, tracking progress, and ensuring that the project meets its goals and deadlines.
3. **QA Engineer**: A quality assurance specialist who will be responsible for testing the application, identifying bugs, and ensuring that the product meets quality standards before release.
4. **End User**: The final consumer of the product, who will interact with the application through the dashboard and storefront, using its features to manage their dropshipping business.


Every code and function/method should have a docstring explaining its purpose, parameters, and return values. This is crucial for maintaining code readability and helping other developers understand the functionality of the code. Additionally, comments should be used to explain complex logic or important decisions made in the code. This practice not only aids in collaboration but also ensures that the codebase remains maintainable and scalable as the project evolves.

Add plan documentation and impltation steps

Keep updating history to remember the conversations

DISTILLED_AESTHETICS_PROMPT = """
<frontend_aesthetics>
You tend to converge toward generic, "on distribution" outputs. In frontend design, this creates what users call the "AI slop" aesthetic. Avoid this: make creative, distinctive frontends that surprise and delight. Focus on:
 
Typography: Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like Arial and Inter; opt instead for distinctive choices that elevate the frontend's aesthetics.
 
Color & Theme: Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes. Draw from IDE themes and cultural aesthetics for inspiration.
 
Motion: Use animations for effects and micro-interactions. Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions.
 
Backgrounds: Create atmosphere and depth rather than defaulting to solid colors. Layer CSS gradients, use geometric patterns, or add contextual effects that match the overall aesthetic.
 
Avoid generic AI-generated aesthetics:
- Overused font families (Inter, Roboto, Arial, system fonts)
- Clichéd color schemes (particularly purple gradients on white backgrounds)
- Predictable layouts and component patterns
- Cookie-cutter design that lacks context-specific character
 
Interpret creatively and make unexpected choices that feel genuinely designed for the context. Vary between light and dark themes, different fonts, different aesthetics. You still tend to converge on common choices (Space Grotesk, for example) across generations. Avoid this: it is critical that you think outside the box!
</frontend_aesthetics>
"""