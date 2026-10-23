'''
Writes docs/reference.md: every function and class of the FielDev library, with its signature and its
documentation, from the library itself.  Run it after changing a docstring:

    python scripts/gen_reference.py

(needs the built fieldev.dll: set FIELDEV_DIR to the folder holding it).
'''
import importlib, inspect, os, sys, textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'python'))

MODULES = [
    ('shapes', 'Primitive shapes', 'fieldev.stdlib.shapes'),
    ('csg', 'Combining shapes (CSG)', 'fieldev.stdlib.csg'),
    ('transforms', 'Moving, rotating, scaling, deforming', 'fieldev.stdlib.transforms'),
    ('text', 'Text', 'fieldev.stdlib.text'),
    ('importing', 'Importing models', 'fieldev.stdlib.importing'),
    ('mesh_import', 'Triangle meshes', 'fieldev.stdlib.mesh_import'),
    ('materials', 'Materials of an export', 'fieldev.stdlib.materials'),
    ('rigging', 'Skeletons of an export', 'fieldev.stdlib.rigging'),
    ('uvmaps', 'UV maps', 'fieldev.stdlib.uvmaps'),
    ('texturing', 'Baked textures', 'fieldev.stdlib.texturing'),
    ('pngfile', 'PNG files', 'fieldev.stdlib.pngfile'),
    ('exporting', 'Exporting files', 'fieldev.stdlib.exporting'),
    ('handles', 'Handles: editing shapes by dragging', 'fieldev.stdlib.handles'),
    ('instances', 'Linked copies', 'fieldev.stdlib.instances'),
    ('symmetries', 'Symmetry', 'fieldev.stdlib.symmetries'),
    ('points', 'Points and surfaces', 'fieldev.stdlib.points'),
    ('curves', 'Lines and curves: 1D shapes made of points', 'fieldev.stdlib.curves'),
    ('profile', 'Profiles and extrusions', 'fieldev.stdlib.profile'),
    ('characters', 'Characters: armatures made of points', 'fieldev.stdlib.characters'),
    ('armature', 'Armatures: armatures, a character, a skeleton', 'fieldev.stdlib.armature'),
    ('feature_model', 'Feature models', 'fieldev.stdlib.feature_model'),
    ('references', 'Reference images', 'fieldev.stdlib.references'),
    ('measure', 'Measuring a body', 'fieldev.stdlib.measure'),
    ('fields', 'Fields', 'fieldev.stdlib.fields'),
    ('regression', 'Regressions and data', 'fieldev.stdlib.regression'),
    ('surfaces', 'Surfaces and offsets', 'fieldev.stdlib.surfaces'),
    ('selection', 'Selecting surfaces', 'fieldev.stdlib.selection'),
    ('fieldargs', 'Telling fields from numbers', 'fieldev.stdlib.fieldargs'),
    ('shape', 'The shape class', 'fieldev.shape'),
    ('run_progress', 'Progress of a long step', 'fieldev.run_progress'),
    ('content_cache', 'Caching', 'fieldev.stdlib.content_cache'),
    ('render_cache', 'Keeping rendered meshes (render cache)', 'fieldev.stdlib.render_cache'),
    ('custom_resolution', 'A resolution of its own for one body', 'fieldev.stdlib.custom_resolution'),
    ('app', 'FielDev apps: the inputs of a script', 'fieldev.app'),
]


def signature(obj):
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return '(...)'


def doc_of(obj):
    d = inspect.getdoc(obj) or ''
    return d.strip()


def describe(name, obj, level='###'):
    out = []
    kind = 'class' if inspect.isclass(obj) else 'function'
    out.append('%s `%s%s`' % (level, name, signature(obj) if kind == 'function' else ''))
    d = doc_of(obj)
    out.append('')
    out.append(d if d else '*(no description yet)*')
    out.append('')
    if kind == 'class':
        for mname, m in inspect.getmembers(obj):
            if mname.startswith('_') or not callable(m):
                continue
            if getattr(m, '__qualname__', '').split('.')[0] != obj.__name__:
                continue
            out.append('#### `%s.%s%s`' % (name, mname, signature(m)))
            out.append('')
            out.append(doc_of(m) or '*(no description yet)*')
            out.append('')
    return out


def main():
    lines = ['# Library reference', '',
             'Every public function and class of the FielDev library, generated from its docstrings',
             '(`python scripts/gen_reference.py`).  `from fieldev import *` brings all of them in.', '']
    lines.append('Contents: ' + ' | '.join('[%s](#%s)' % (title, title.lower().replace(' ', '-').replace(':', '')
                                                          .replace(',', '').replace('(', '').replace(')', ''))
                                             for _, title, _ in MODULES))
    lines.append('')
    seen = set()
    for short, title, modname in MODULES:
        mod = importlib.import_module(modname)
        lines.append('## ' + title)
        lines.append('')
        intro = inspect.getdoc(mod)
        if intro:
            lines.append(intro)
            lines.append('')
        names = list(mod.__all__) if modname == 'fieldev.app' else [n for n in dir(mod) if not n.startswith('_')]
        for n in sorted(names):
            obj = getattr(mod, n)
            if not (inspect.isfunction(obj) or inspect.isclass(obj)):
                continue
            if getattr(obj, '__module__', None) != modname or (modname, n) in seen:
                continue
            seen.add((modname, n))
            lines.extend(describe(('app.' + n) if modname == 'fieldev.app' else n, obj))
    with open(os.path.join(ROOT, 'docs', 'reference.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines).rstrip() + '\n')
    print('wrote docs/reference.md:', len(seen), 'entries')


if __name__ == '__main__':
    main()
