# FielDev: what this program is

FielDev is a **modelling program**: fields, shapes, materials, editing -- for people who make game assets. **It is not a game engine.**

## The rule (the user has said it again and again; on 2026-10-26: "THIS IS AN ENGINE LEVEL FEATURE. ENGINES DO THIS. THIS IS NOT AN ENGINE. THIS IS A MODELLING PROGRAM. FOCUS ON THE MODELLING, DONT TRY TO ADD YOUR OWN VERSION OF ENGINE LEVEL TASKS.")

**Never build anything an engine does.** Engines make level-of-detail meshes, collision meshes, streaming a world in at runtime, instancing and scatter lists, scene and prefab files, navigation meshes, and the like. Before you add any feature, ask what it *does*: a field operation on the model (cutting it into pieces, a blend, a material as a field, a check you look at while modelling) belongs here; a job that the engine does at runtime does not -- whatever the feature is called, and however much of it "could be derived from the field". Cutting a model into pieces is modelling; loading the pieces at runtime is the engine's.

* What belongs here is the **model**: fields and the arithmetic on them, shapes, terrain / levels / props / kits as things to *model*, materials (as fields, and by drag and drop), editing in the viewport and in the script, and checks that help *while modelling* (a seam check, a slope colouring).
* Export is a plain export of the model (`export_mesh`): the model, its materials, its unit. No pipelines around it.
* Stay in fields as long as possible: a mesh is made only to show a model or to write it to a file.

## Everything is reachable from the context menu (the user, 2026-10-26: "EVERYTHING IS ALWAYS AVAILABLE FROM THE CONTEXT MENU")

Every feature must be reachable from the right-click context menu (primitives, operations, materials, exports, checks). A feature that exists only as a function you type in a script is **not finished** and must never be listed or reported as done. A feature is done when (1) its menu entry exists and writes the call into the script, (2) the entry was checked (the menu dump lists it, the text it writes runs), and (3) the docs say where it is in the menu. Add the entry in the same batch as the function (`python/fieldev/menu_catalog.py`: PRIMITIVES and OPERATIONS).

## An armature drags in real time, and a branch is part of it (the user: "so that you can drag it around in real time"; a branch must "ACTIVELY GET INCORPORATED INTO THE ARMATURE FROM THE START")

An armature has to be dragged around in real time: while a node is dragged every sweep of it is drawn natively from the numbers of its nodes (`_sweep_*`, `_sweep_branches`), and a change is never answered by meshing a field then (that is seconds).  That drawing is only a quick picture for the hand: **the mesh that stays, and is exported, is the mesh of the field** -- for a sweep with blended branches the last level of the render is the field (`Shape::hasBlendedSweep`), the blend that `export_mesh` writes (`smooth_union` of the sweeps), made by the application from the formula of that field (`Shape::blendedSweepMesh`): that mesh may not take longer than about 5 seconds (the user: "anything above like 5 seconds is unacceptable"), and a time like the 33 to 55 s that the general mesher of libfive needed is a thing to remove, not a limit to report.  A branch is not a second tube united with the first, and a picture that stays is never the quick one.  A change that makes dragging a node slower than the native drawing is wrong, whatever else it gains: do not call it a trade-off, do not decide it away.

## Other standing rules of the user

* Never push, publish or open a pull request without his word for that step in his latest message.
* Say plainly that nothing was seen in a real window or on Windows: tests here run only in a virtual display with software rendering.
* When he cannot be asked, decide, and write the decision and the alternative down (`docs/gamedev-decisions.md`).
