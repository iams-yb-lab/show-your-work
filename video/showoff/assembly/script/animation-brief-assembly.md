You are acting as the technical director, Blender artist, and animation engineer for a polished research-presentation animation.

<context>
I already have a Blender scene containing the real CAD geometry of my temperature-controller PCB and its components. The scene has already been successfully rendered with realistic materials and lighting.

The geometry is the source of truth. This is a real research board, not a conceptual reconstruction. Preserve the actual PCB geometry, component positions, proportions, silkscreen, and overall design.

This animation will be embedded into a my research presentation. The visual target is premium technical product cinematography: realistic, clean, elegant, physically believable, and visually dynamic without becoming flashy or distracting.
</context>

<task>
Create and implement the FIRST animation scene.

Do not merely describe how I could make it. Work directly on the Blender project and create the animation, using Blender Python/scripts where useful.

The scene should tell the visual story of the PCB being assembled from an empty board into the completed temperature controller.

Target duration: approximately 15–20 seconds.

The finished animation should feel like a professional hardware product reveal rather than a literal factory pick-and-place simulation.
</task>

<storyboard>
The animation should progress approximately as follows. Treat these timings as artistic guidance rather than rigid frame boundaries if a slightly different timing produces substantially better motion.

1. OPENING — BARE PCB
Begin with only the bare PCB visible.

The board should initially be presented at an attractive oblique angle rather than simply lying flat facing the camera.

Use a smooth cinematic camera movement and/or board rotation to bring the PCB toward the center of the composition.

Allow the viewer enough time to recognize the empty PCB before assembly begins.

Lighting should already establish the board as a premium product render.

2. PASSIVES
Introduce the small passive components first.

Do not animate every resistor and capacitor with a slow individual entrance. Organize related passives into sensible groups or waves and stagger their arrivals so the board rapidly begins to populate.

Their motion can originate above the PCB with subtle variation in height and timing.

Use smooth acceleration/deceleration. Components should settle precisely into their real final CAD positions.

The effect should communicate assembly while remaining visually clean and fast.

3. LARGER SUPPORTING COMPONENTS
After the small passives, introduce larger supporting components such as connectors, headers, terminal blocks, trimmers, capacitors, and other visibly larger parts.

Use somewhat more pronounced motion than the tiny passives.

Allow different groups to arrive with slightly different timing/direction so the sequence feels intentionally choreographed rather than mechanically identical.

All components must end at their exact real positions and orientations.

4. ADC HERO INTRODUCTION
Treat the ADC as an important component rather than just another object.

Identify the ADC from the actual project/board rather than guessing from visual appearance alone.

Shift the camera smoothly toward its region of the PCB.

Give the ADC a short individual introduction: bring it into frame from above with a controlled descent and possibly a subtle rotation, then have it settle precisely onto its pads.

The motion should make the viewer naturally understand that this component is important.

Do not add explanatory text into the Blender render yet; the PowerPoint can provide labels separately.

5. TEC DRIVER HERO INTRODUCTION
Introduce the TEC driver separately after the ADC.

Identify the actual driver from the project.

Use another deliberate camera movement so the viewer's attention moves naturally from the ADC section toward the driver section.

Give the driver its own controlled entrance and landing.

Make this visually distinct from the ADC introduction while maintaining the same cinematic language.

6. TEENSY / CONTROLLER MODULE FINALE
The Teensy/controller module should be the final major component installed.

Build anticipation by allowing a brief moment after the ADC and driver have landed.

Move the camera into an angle where the Teensy landing will read clearly.

Bring the entire Teensy module into the scene from above. Give it a smooth, substantial descent appropriate for its larger physical size.

A tiny controlled overshoot or settling motion is acceptable if it improves the feeling of weight, but keep it sophisticated rather than cartoonish.

It must finish exactly at its real mounted location.

7. FINAL HERO SHOT
After the Teensy lands, transition smoothly into a completed-board hero shot.

Pull the camera back enough to reveal the entire assembled PCB.

Let the final composition settle for roughly 1–2 seconds so it can potentially transition into the next scene later.

The final appearance should match or improve upon the quality of the existing still renders.
</storyboard>

<animation_language>
Favor cinematic product-animation motion:

- smooth camera arcs
- controlled push-ins and pull-backs
- subtle changes in viewing angle
- clean ease-in/ease-out
- staggered component motion
- strong visual hierarchy
- physically plausible movement
- restrained depth of field
- subtle motion blur where appropriate

Keep the PCB readable throughout the animation.

Use dynamic camera movement, but never move the camera merely for spectacle. Every camera movement should direct attention toward the component currently being introduced.

The animation should feel expensive and intentional.

Use keyframed deterministic motion for component assembly unless simulation provides a clear visual advantage. Precision of the final component placement is more important than physical simulation.
</animation_language>

<visual_style>
Preserve the realistic visual language of the existing render.

Target:
professional electronics product photography
+
high-end engineering visualization
+
subtle cinematic presentation.

Prioritize realistic material response, metal/plastic distinction, PCB solder-mask appearance, contact metals, believable shadows, good separation between components, and physically coherent lighting.

Do not redesign the actual electronics.

Do not hallucinate additional components.

Do not simplify or relocate real components merely to make the shot prettier.

If an imported CAD asset has a known geometry/material defect, preserve the underlying engineering geometry unless fixing the rendering/import artifact can be done safely without changing the actual design.
</visual_style>

<camera>
Use one continuous cinematic sequence where practical rather than a collection of unrelated cuts.

Cuts are allowed only where they substantially improve clarity.

Avoid:
- excessive spinning
- extreme wide-angle distortion
- rapid handheld-style movement
- camera motion that makes the PCB difficult to understand
- dramatic movement that competes with the technical content

The viewer should always maintain a spatial understanding of the board.
</camera>

<implementation>
Inspect the existing Blender project before changing it.

Understand:
- object hierarchy
- component naming
- object origins
- parent/child relationships
- current materials
- camera
- lighting
- render engine
- existing scene scale
- whether CAD-imported components consist of multiple child meshes

Create a maintainable animation setup.

Where useful, use Blender Python to:
- identify and group component objects
- preserve final transforms
- create assembly-start transforms
- generate keyframes
- apply easing
- stagger component timing
- animate camera targets
- organize animation controls

For multi-part component models, animate them as one logical component rather than allowing individual submeshes to separate.

Preserve the original completed-board transforms so the final animation state exactly reconstructs the real board.

Do not destructively alter the only copy of important source geometry. Use sensible collections, parenting, empties, duplicated scene data, scripts, or another maintainable structure where appropriate.

Choose a sensible presentation frame rate and resolution. The eventual target is a high-quality 16:9 PowerPoint presentation video.

Use the NVIDIA RTX 4070 / CUDA or OptiX-compatible Cycles rendering path where appropriate for final rendering, but keep iteration renders substantially cheaper so we can tune the animation quickly.
</implementation>

<workflow>
First inspect the scene and determine how the imported CAD objects are structured.

Then implement the animation.

During implementation, prioritize getting the complete motion sequence working before spending large amounts of render time on final-quality frames.

Use inexpensive viewport or low-sample preview renders while iterating.

If you encounter an implementation detail that can be resolved by inspecting the files or Blender scene, inspect it and proceed rather than asking me.

Make routine artistic and technical decisions yourself.

Only ask me a question if two genuinely different interpretations would materially change the resulting animation and the answer cannot be inferred from the existing project.
</workflow>

<scope>
Work on this first PCB assembly scene only.

Do not begin creating later Red Pitaya scenes, wiring scenes, experimental-setup scenes, PowerPoint slides, or unrelated assets.

You may structure the Blender project so later scenes can reuse the completed board, but do not implement those later scenes yet.

Deliver the requested scene at the scope intended.
</scope>

<communication>
Keep progress messages brief.

Before beginning, give me a concise description of the animation structure you intend to implement, then start working.

While working, only update me when you reach a meaningful milestone, discover an important issue, or materially change direction.

When finished, tell me:
- what you implemented
- where the Blender file/scripts are
- how to preview the animation quickly
- how to start a final render
- any remaining visual issues worth fixing

Do not spend the response explaining Blender concepts unless I ask.
</communication>

<success_criteria>
The task is successful when:

The animation begins with the real bare PCB.

Passives populate first in attractive staggered waves.

Larger components follow.

The ADC receives an individual cinematic introduction.

The TEC driver receives an individual cinematic introduction.

The Teensy/controller module is the final major installation.

Every object ends exactly at its real completed-board transform.

The camera dynamically guides attention without harming readability.

The completed board ends in a strong hero composition.

The animation looks suitable for a serious research presentation rather than a generic AI animation.

The project remains maintainable enough for us to iterate on timing, camera movement, and materials afterward.
</success_criteria>