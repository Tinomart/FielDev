# FielDev: what this program is

FielDev is a **modelling program**: fields, shapes, materials, editing -- for people who make game assets. **It is not a game engine.**

## The rule (the user has said it again and again; on 2026-10-26: "THIS IS AN ENGINE LEVEL FEATURE. ENGINES DO THIS. THIS IS NOT AN ENGINE. THIS IS A MODELLING PROGRAM. FOCUS ON THE MODELLING, DONT TRY TO ADD YOUR OWN VERSION OF ENGINE LEVEL TASKS.")

**Never build anything an engine does.** Engines make level-of-detail meshes, collision meshes, chunks and streaming, instancing and scatter lists, scene and prefab files, navigation meshes, and the like. Before you add any feature, ask: *would an engine do this?* If yes, do not build it -- however convenient it looks, and however much of it "could be derived from the field".

* What belongs here is the **model**: fields and the arithmetic on them, shapes, terrain / levels / props / kits as things to *model*, materials (as fields, and by drag and drop), editing in the viewport and in the script, and checks that help *while modelling* (a seam check, a slope colouring).
* Export is a plain export of the model (`export_mesh`): the model, its materials, its unit. No pipelines around it.
* Stay in fields as long as possible: a mesh is made only to show a model or to write it to a file.

## Other standing rules of the user

* Never push, publish or open a pull request without his word for that step in his latest message.
* Say plainly that nothing was seen in a real window or on Windows: tests here run only in a virtual display with software rendering.
* When he cannot be asked, decide, and write the decision and the alternative down (`docs/gamedev-decisions.md`).
