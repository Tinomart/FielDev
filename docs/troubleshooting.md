# Troubleshooting

| Symptom | Likely cause and what to do |
|---|---|
| **FielDes closed by itself** | A crash leaves a report in `%LOCALAPPDATA%\FielDes\FielDes\crash` (a text file with the exception and the places the program was at): send it with the script that was open. |
| **The viewport is empty** | Only top-level *expression statements* that evaluate to shapes are drawn; an assignment alone is not (it only appears in the model tree — click its eye). Check the region (`view.set_bounds`) contains the shape, and that it is not hidden (`# hidden:` lines, the eye). A model outside the render region is greyed in the tree. |
| **Thin parts are missing or ragged** | The resolution is too coarse for the thinnest feature. Raise `view.set_resolution` (a wall wants about three samples across it), or give that one body a resolution of its own (`custom_resolution`). |
| **Meshing takes minutes** | The resolution is too fine for the region. Press `Esc` to cancel the render, lower `view.set_resolution`, or shrink `view.set_bounds` to the part you are looking at. |
| **A traceback in the output pane** | The script's own error; the offending line is underlined. What ran before the error is still shown. |
| **`FileNotFoundError` for a relative path** | Relative paths are relative to the script's folder. Save the script first (an unsaved script has no folder), or use an absolute path. |
| **A part is 1000× too small or large** | Units: STL, OBJ, PLY and OFF carry none and are read as millimetres: pass `file_units='m'` (or `'in'`). 3MF, FBX, DXF and glTF say what they are. See [Units](meshes.md#importing-meshes). |
| **The import looks stale after editing the mesh file** | Imported files are watched and re-read when saved by another program. If it does not happen, press **⟳ Reimport** on the import, or give `import_model` another `rev=`. |
| **A strange result that goes away when the cache is deleted** | `clear_caches()` forgets the in-memory ones, **Settings → Clear the caches** the ones on disk: do that, and report it. |
| **The program does not start ("missing DLL")** | Use the portable folder as a whole (the DLLs next to `FielDes.exe`), not the exe alone. The folder includes the MSVC runtime; if you still see the error, install the *Microsoft Visual C++ 2015–2022 Redistributable (x64)*. |
| **"FielDes cannot load its Python library"** | `FielDes.exe` looks for `runtime\python3` and `python\fieldes` around itself. Keep the folder structure intact (see [Building](building.md#the-portable-folder)). |

## Reading the timing

Start FielDes from a terminal with `FIELDES_TIMING=1` to see where render and analysis time goes on stderr
(the lines start with `[fieldes]` and `[bar-render]`).

## Reporting

Please report problems with the script, the output pane text and (for an import) the mesh file if you may
share it: [CONTRIBUTING](../CONTRIBUTING.md).
