#!/usr/bin/env python3
# Copyright 2026 The Helium Authors
# You can use, redistribute, and/or modify this source code under
# the terms of the GPL-3.0 license that can be found in the LICENSE file.
"""Regenerate Helium Neo's vector, bitmap and macOS icon resources.

Run on macOS with Pillow, librsvg's rsvg-convert, and Xcode installed.
The checked-in macOS catalogs allow other platforms to prepare sources without
running Apple's tools. The geometry below is the single source of the design:
it writes the full-color product_logo.svg master, the Icon Composer layers,
the mono glyph and Chromium's vector icons, then rasterizes the rest.

The mark is a helium atom: a nucleus of two protons and two neutrons, an
orbit that tapers and fades toward the main electron, a second electron, and
helium's emission spectrum along the bottom.
"""

from pathlib import Path
import json
import math
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BRANDING = ROOT / 'resources/branding'
ICON_COMPOSER = BRANDING / 'macos/AppIcon.icon'
LICENSE = '''// Copyright 2026 The Helium Authors
// You can use, redistribute, and/or modify this source code under
// the terms of the GPL-3.0 license that can be found in the LICENSE file.

'''

# Atom geometry on a 256-unit canvas.
CENTER = (128, 119)
TILT = math.radians(-35)
ORBIT_RX, ORBIT_RY = 90, 54
RING_MAX, RING_MIN = 12, 7 # Ring width at the main electron and opposite it.
ELECTRON_R, SECOND_ELECTRON_R = 10, 7
# The ring stops short of each electron along a circle around it.
ELECTRON_CUT_R, SECOND_ELECTRON_CUT_R = 15.5, 11.5
NUCLEONS = [(-9, -8, 'proton'), (9, -8, 'neutron'), (-9, 9, 'neutron'), (9, 9, 'proton')]
NUCLEON_R = 13

# Helium emission lines (nm), display colors and opacities. D3 at 587.6 nm is
# the line helium was discovered by, so it is drawn wider.
SPECTRUM_LINES = [(388.9, '#7A3CFF', .5), (447.1, '#3D5BFF', .8), (471.3, '#1E9BFF', .55),
                  (492.2, '#00D2D6', .6), (501.6, '#22E07A', .8), (587.6, '#FFD23F', 1.0),
                  (667.8, '#FF3B30', .85), (706.5, '#C2122A', .6)]
SPECTRUM_BAND = (26, 205, 204, 26) # x, y, width, height
SPECTRUM_INSET = 4

SQUIRCLE = 'x="5.5" y="5.5" width="245" height="245" rx="61"'


def orbit_point(t, offset=0.0):
    """Returns the orbit point at parameter t, moved `offset` along its normal."""
    x, y = ORBIT_RX * math.cos(t), ORBIT_RY * math.sin(t)
    normal_x, normal_y = math.cos(t) / ORBIT_RX, math.sin(t) / ORBIT_RY
    length = math.hypot(normal_x, normal_y)
    x, y = x + offset * normal_x / length, y + offset * normal_y / length
    return (CENTER[0] + x * math.cos(TILT) - y * math.sin(TILT),
            CENTER[1] + x * math.sin(TILT) + y * math.cos(TILT))


def ring_width(t):
    """Eases from RING_MAX at the main electron (t=0) to RING_MIN opposite it."""
    return RING_MIN + (RING_MAX - RING_MIN) * (1 + math.cos(t)) / 2


def ring_edge(t, side):
    """Returns a point on the ring's outer (side=1) or inner (side=-1) edge."""
    return orbit_point(t, side * ring_width(t) / 2)


ELECTRON = orbit_point(0)
SECOND_ELECTRON = orbit_point(math.pi)


def _leave_circle(side, inside, outside, circle):
    """Bisects for where the ring edge crosses the circle between two params."""
    (circle_x, circle_y), radius = circle
    for _ in range(60):
        middle = (inside + outside) / 2
        x, y = ring_edge(middle, side)
        if math.hypot(x - circle_x, y - circle_y) < radius:
            inside = middle
        else:
            outside = middle
    return outside


def _arc(circle, start, end):
    """Points on `circle` along the short arc from `start` to `end`, which is the
    part of the circle that crosses the ring."""
    (circle_x, circle_y), radius = circle
    angle0 = math.atan2(start[1] - circle_y, start[0] - circle_x)
    angle1 = math.atan2(end[1] - circle_y, end[0] - circle_x)
    sweep = (angle1 - angle0 + math.pi) % (2 * math.pi) - math.pi
    steps = 12
    return [(circle_x + radius * math.cos(angle0 + sweep * i / steps),
             circle_y + radius * math.sin(angle0 + sweep * i / steps)) for i in range(1, steps)]


def ring_pieces(samples=72):
    """Returns the two ring outlines between the electrons, each ending in a
    concave arc that follows the circle around the electron it meets."""
    first = (ELECTRON, ELECTRON_CUT_R)
    second = (SECOND_ELECTRON, SECOND_ELECTRON_CUT_R)
    pieces = []
    for start, end, start_circle, end_circle in [(0, math.pi, first, second),
                                                 (math.pi, 2 * math.pi, second, first)]:
        ends = {}
        for side in (1, -1):
            first_end = _leave_circle(side, start, start + 1, start_circle)
            last_end = _leave_circle(side, end, end - 1, end_circle)
            ends[side] = (first_end, last_end)
        outer = [
            ring_edge(ends[1][0] + (ends[1][1] - ends[1][0]) * i / samples, 1)
            for i in range(samples + 1)
        ]
        inner = [
            ring_edge(ends[-1][1] - (ends[-1][1] - ends[-1][0]) * i / samples, -1)
            for i in range(samples + 1)
        ]
        pieces.append(outer + _arc(end_circle, outer[-1], inner[0]) + inner +
                      _arc(start_circle, inner[-1], outer[0]))
    return pieces


def path_data(points):
    """Returns closed SVG path data through `points`."""
    return 'M' + ' L'.join(f'{x:.3f} {y:.3f}' for x, y in points) + ' Z'


def gaussian_gradient(gradient_id, center, radius, light, stops=16):
    """A radial gradient that falls off like a Gaussian and reaches 0 at the edge.

    `light` is (color, peak opacity, sigma as a fraction of the radius).
    """
    color, peak, sigma = light
    tail = math.exp(-(1 / sigma)**2)
    parts = []
    for i in range(stops + 1):
        offset = i / stops
        opacity = peak * (math.exp(-(offset / sigma)**2) - tail) / (1 - tail)
        parts.append(f'<stop offset="{offset:.4f}" stop-color="{color}" '
                     f'stop-opacity="{max(opacity, 0):.4f}"/>')
    return (f'<radialGradient id="{gradient_id}" cx="0" cy="0" r="1" '
            f'gradientUnits="userSpaceOnUse" gradientTransform="translate({center[0]:.3f} '
            f'{center[1]:.3f}) scale({radius})">{"".join(parts)}</radialGradient>')


def trail_mask():
    """Brightens the ring toward the main electron, as if it were a trail."""
    parts = []
    segments, low = 96, .28
    for i in range(segments):
        start = 2 * math.pi * i / segments
        end = min(2 * math.pi * (i + 1.6) / segments, 2 * math.pi - 1e-3)
        gray = round(255 * (low + (1 - low) * ((i + .5) / segments)**1.6))
        (x1, y1), (x2, y2) = orbit_point(start), orbit_point(end)
        parts.append(f'<path d="M{x1:.3f} {y1:.3f} A{ORBIT_RX} {ORBIT_RY} '
                     f'{math.degrees(TILT):.0f} 0 1 {x2:.3f} {y2:.3f}" '
                     f'stroke="rgb({gray},{gray},{gray})" stroke-width="{RING_MAX + 6}"/>')
    return ('<mask id="trail" maskUnits="userSpaceOnUse" x="0" y="0" width="256" height="256">' +
            ''.join(parts) + '</mask>')


def spectrum_line_rects():
    """Returns (x, y, width, height, color, opacity) for each spectral line."""
    band_x, band_y, band_width, band_height = SPECTRUM_BAND
    rects = []
    for wavelength, color, opacity in SPECTRUM_LINES:
        x = band_x + 8 + (wavelength - 380) / (720 - 380) * (band_width - 16)
        width = 3.2 if wavelength == 587.6 else 1.8
        rects.append((x - width / 2, band_y + SPECTRUM_INSET, width,
                      band_height - 2 * SPECTRUM_INSET, color, opacity))
    return rects


DEFS = {
    'clip': f'<clipPath id="clip"><rect {SQUIRCLE}/></clipPath>',
    'background': ('<linearGradient id="background" x1="40" y1="6" x2="216" y2="250" '
                   'gradientUnits="userSpaceOnUse"><stop stop-color="#2A2357"/>'
                   '<stop offset=".6" stop-color="#14112E"/><stop offset="1" stop-color="#08070F"/>'
                   '</linearGradient>'),
    'glow': gaussian_gradient('glow', (128, 118), 130, ('#6E4BFF', .5, .55)),
    'halo': gaussian_gradient('halo', CENTER, 50, ('#FFD978', .42, .5)),
    'bloom': gaussian_gradient('bloom', ELECTRON, 34, ('#FFE38A', .75, .4)),
    'second-bloom': gaussian_gradient('second-bloom', SECOND_ELECTRON, 22, ('#FFE9B0', .45, .4)),
    'electron': (
        '<radialGradient id="electron" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" '
        f'gradientTransform="translate({ELECTRON[0] - 3:.3f} {ELECTRON[1] - 3:.3f}) scale(14)">'
        '<stop stop-color="#FFFFFF"/><stop offset=".7" stop-color="#FFFDF4"/>'
        '<stop offset="1" stop-color="#FFF1C4"/></radialGradient>'),
    'proton': ('<radialGradient id="proton" cx="0" cy="0" r="1" gradientUnits="objectBoundingBox" '
               'gradientTransform="translate(.35 .3) scale(.8)"><stop stop-color="#FFF0B8"/>'
               '<stop offset="1" stop-color="#F2A81D"/></radialGradient>'),
    'neutron': (
        '<radialGradient id="neutron" cx="0" cy="0" r="1" gradientUnits="objectBoundingBox" '
        'gradientTransform="translate(.35 .3) scale(.8)"><stop stop-color="#FFFFFF"/>'
        '<stop offset="1" stop-color="#B9B2E6"/></radialGradient>'),
    'shadow': (
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" '
        'dy="2" stdDeviation="2.5" flood-color="#000" flood-opacity=".45"/></filter>'),
    'trail': trail_mask(),
}


def layer(name): # pylint: disable=too-many-locals,too-many-return-statements
    """Returns the SVG elements and the defs they use for one layer."""
    if name == 'background':
        return [
            f'<rect {SQUIRCLE} fill="url(#background)"/>', f'<rect {SQUIRCLE} fill="url(#glow)"/>'
        ], ['background', 'glow']
    if name == 'glow':
        # Icon Composer supplies the background; this carries its light.
        bloom_elements, bloom_defs = layer('blooms')
        return ['<rect width="256" height="256" fill="url(#glow)"/>'
                ] + bloom_elements, ['glow'] + bloom_defs
    if name == 'blooms':
        return [
            f'<circle cx="{CENTER[0]}" cy="{CENTER[1]}" r="50" fill="url(#halo)"/>',
            f'<circle cx="{ELECTRON[0]:.3f}" cy="{ELECTRON[1]:.3f}" r="34" fill="url(#bloom)"/>',
            f'<circle cx="{SECOND_ELECTRON[0]:.3f}" cy="{SECOND_ELECTRON[1]:.3f}" r="22" '
            'fill="url(#second-bloom)"/>'
        ], ['halo', 'bloom', 'second-bloom']
    if name == 'spectrum':
        band_x, band_y, band_width, band_height = SPECTRUM_BAND
        elements = [
            f'<rect x="{band_x}" y="{band_y}" width="{band_width}" height="{band_height}" '
            f'rx="9" fill="#000" fill-opacity=".25"/>'
        ]
        for x, y, width, height, color, opacity in spectrum_line_rects():
            elements.append(f'<rect x="{x:.2f}" y="{y}" width="{width}" height="{height}" '
                            f'rx="{width / 2}" fill="{color}" fill-opacity="{opacity}"/>')
        return elements, []
    if name == 'orbit':
        pieces = ' '.join(path_data(piece) for piece in ring_pieces())
        return [f'<path d="{pieces}" fill="#EDEBFF" mask="url(#trail)"/>'], ['trail']
    if name == 'nucleus':
        circles = ''.join(f'<circle cx="{CENTER[0] + dx}" cy="{CENTER[1] + dy}" r="{NUCLEON_R}" '
                          f'fill="url(#{kind})"/>' for dx, dy, kind in NUCLEONS)
        return [f'<g filter="url(#shadow)">{circles}</g>'], ['proton', 'neutron', 'shadow']
    if name == 'electrons':
        return [
            f'<circle cx="{ELECTRON[0]:.3f}" cy="{ELECTRON[1]:.3f}" r="{ELECTRON_R}" '
            'fill="url(#electron)"/>',
            f'<circle cx="{SECOND_ELECTRON[0]:.3f}" cy="{SECOND_ELECTRON[1]:.3f}" '
            f'r="{SECOND_ELECTRON_R}" fill="#FFFFFF" fill-opacity=".9"/>'
        ], ['electron']
    raise ValueError(name)


def svg(names, size=256):
    """Returns an SVG document of the named layers, back to front."""
    elements, defs = [], []
    for name in names:
        layer_elements, layer_defs = layer(name)
        elements += layer_elements
        defs += [d for d in layer_defs if d not in defs]
    if 'background' in names:
        # Keep the squircle's soft lighting inside its shape, and add a faint rim.
        background = len(layer('background')[0])
        spectrum = len(layer('spectrum')[0]) if 'spectrum' in names else 0
        clipped = elements[:background + spectrum]
        elements = ['<g clip-path="url(#clip)">'] + clipped + [
            '</g>', '<rect x="6" y="6" width="244" height="244" rx="60.5" stroke="#FFFFFF" '
            'stroke-opacity=".12"/>'
        ] + elements[background + spectrum:]
        defs.insert(0, 'clip')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            'viewBox="0 0 256 256" fill="none">\n<defs>\n' + '\n'.join(DEFS[d] for d in defs) +
            '\n</defs>\n' + '\n'.join(elements) + '\n</svg>\n')


MASTER_LAYERS = ['background', 'spectrum', 'blooms', 'orbit', 'nucleus', 'electrons']
# Icon Composer groups, front to back, with their layers and whether they use
# Liquid Glass. Icon Composer allows at most four groups.
COMPOSER_GROUPS = [(['electrons', 'nucleus'], True), (['orbit'], True), (['spectrum'], False),
                   (['glow'], False)]


def mono_svg():
    """A flat white glyph: the ring without its fade, nucleus and electrons."""
    pieces = ' '.join(path_data(piece) for piece in ring_pieces())
    circles = ''.join(f'<circle cx="{CENTER[0] + dx}" cy="{CENTER[1] + dy}" r="{NUCLEON_R}"/>'
                      for dx, dy, _ in NUCLEONS)
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" '
            'viewBox="0 0 256 256" fill="white">'
            f'<path d="{pieces}"/>{circles}'
            f'<circle cx="{ELECTRON[0]:.3f}" cy="{ELECTRON[1]:.3f}" r="{ELECTRON_R}"/>'
            f'<circle cx="{SECOND_ELECTRON[0]:.3f}" cy="{SECOND_ELECTRON[1]:.3f}" '
            f'r="{SECOND_ELECTRON_R}"/></svg>\n')


def argb(color, opacity=1.0):
    """Returns a vector icon PATH_COLOR_ARGB command."""
    color = color.lstrip('#')
    return (f'PATH_COLOR_ARGB, 0x{round(opacity * 255):02X}, 0x{color[0:2]}, 0x{color[2:4]}, '
            f'0x{color[4:6]},')


def vector_mark(scale, colors=None):
    """Chromium vector icon commands for the mark, optionally in color."""
    lines = []

    def new_path(color=None):
        if lines:
            lines.append('NEW_PATH,')
        if colors and color:
            lines.append(argb(color))

    for piece in ring_pieces(48):
        new_path(colors and colors['ring'])
        for i, (x, y) in enumerate(piece):
            lines.append(f'{"MOVE_TO" if i == 0 else "LINE_TO"}, {x * scale:.4f}f, '
                         f'{y * scale:.4f}f,')
        lines.append('CLOSE,')
    for dx, dy, kind in NUCLEONS:
        new_path(colors and colors[kind])
        lines.append(f'CIRCLE, {(CENTER[0] + dx) * scale:.4f}f, {(CENTER[1] + dy) * scale:.4f}f, '
                     f'{NUCLEON_R * scale:.4f}f,')
    for (x, y), radius in [(ELECTRON, ELECTRON_R), (SECOND_ELECTRON, SECOND_ELECTRON_R)]:
        new_path(colors and colors['electron'])
        lines.append(f'CIRCLE, {x * scale:.4f}f, {y * scale:.4f}f, {radius * scale:.4f}f,')
    return '\n'.join(lines) + '\n'


def color_vector_icon():
    """Returns the full-color vector icon: tile, spectrum and mark."""
    lines = ['CANVAS_DIMENSIONS, 256,', argb('#1B1640'), 'ROUND_RECT, 5.5f, 5.5f, 245, 245, 61,']
    band_x, band_y, band_width, band_height = SPECTRUM_BAND
    lines += [
        'NEW_PATH,',
        argb('#000000', .25), f'ROUND_RECT, {band_x}, {band_y}, {band_width}, {band_height}, 9,'
    ]
    for x, y, width, height, color, opacity in spectrum_line_rects():
        lines += [
            'NEW_PATH,',
            argb(color, opacity), f'ROUND_RECT, {x:.2f}f, {y}, {width}f, {height}, {width / 2}f,'
        ]
    colors = {'ring': '#EDEBFF', 'proton': '#F5B83A', 'neutron': '#DCD7F7', 'electron': '#FFFFFF'}
    return '\n'.join(lines) + '\nNEW_PATH,\n' + vector_mark(1, colors)


def icon_composer_document():
    """Returns icon.json for the Icon Composer layers and appearances."""
    return {
        'fill-specializations': [{
            'value': {
                'linear-gradient': [
                    'srgb:0.16471,0.13725,0.34118,1.00000', 'srgb:0.03137,0.02745,0.05882,1.00000'
                ]
            }
        }, {
            'appearance': 'dark',
            'value': 'automatic'
        }],
        'groups': [{
            'layers': [{
                'glass': glass,
                'hidden': False,
                'image-name': f'{name}.png',
                'name': name,
                'position': {
                    'scale': 1.0,
                    'translation-in-points': [0, 0]
                }
            } for name in names],
            'shadow': {
                'kind': 'neutral' if glass else 'none',
                'opacity': 0.2
            },
            'translucency': {
                'enabled': glass,
                'value': 0.3
            },
            **({
                'specular': 'inside'
            } if glass else {}),
        } for names, glass in COMPOSER_GROUPS],
        'supported-platforms': {
            'squares': 'shared'
        }
    }


def main(): # pylint: disable=too-many-locals,too-many-statements
    """Generate all formats without modifying any prepared Chromium tree."""
    renderer = shutil.which('rsvg-convert')
    if not renderer:
        raise SystemExit('Install librsvg (rsvg-convert) before generating icons.')

    def rasterize(source, output, size=1024):
        subprocess.run(
            [renderer, '-w',
             str(size), '-h',
             str(size), str(source), '-o',
             str(output)],
            check=True)

    (BRANDING / 'product_logo.svg').write_text(svg(MASTER_LAYERS))
    rasterize(BRANDING / 'product_logo.svg', BRANDING / 'app_icon/raw.png')
    raw = Image.open(BRANDING / 'app_icon/raw.png').convert('RGBA')
    raw.resize((512, 512), Image.Resampling.LANCZOS).save(BRANDING / 'app_icon/file.png')
    (BRANDING / 'product_logo.icon').write_text(LICENSE + 'CANVAS_DIMENSIONS, 56,\n' +
                                                vector_mark(56 / 256))
    (BRANDING / 'product_logo_color.icon').write_text(LICENSE + color_vector_icon())

    assets = ICON_COMPOSER / 'Assets'
    shutil.rmtree(assets, ignore_errors=True)
    assets.mkdir()
    # Icon Composer's SVG importer changes shapes and uses the SVG's intrinsic
    # size, so it gets full-resolution rasters; the SVGs document each layer.
    for name in [name for names, _ in COMPOSER_GROUPS for name in names]:
        (assets / f'{name}.svg').write_text(svg([name], 1024))
        rasterize(assets / f'{name}.svg', assets / f'{name}.png')
    (ICON_COMPOSER / 'icon.json').write_text(json.dumps(icon_composer_document(), indent=2) + '\n')

    with tempfile.TemporaryDirectory(prefix='helium-neo-icons-') as temporary:
        temp = Path(temporary)
        (temp / 'mono.svg').write_text(mono_svg())
        rasterize(temp / 'mono.svg', temp / 'mono.png')
        glyph = Image.open(temp / 'mono.png').convert('RGBA')
        glyph.resize((22, 22), Image.Resampling.LANCZOS).save(BRANDING / 'product_logo_22_mono.png')
        for scale, suffix in [(1, ''), (2, '_200')]:
            for light in [False, True]:
                wordmark = Image.new('RGBA', (140 * scale, 32 * scale))
                wordmark.alpha_composite(
                    raw.resize((32 * scale, 32 * scale), Image.Resampling.LANCZOS))
                size = 18 * scale
                while True:
                    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', size, index=1)
                    if font.getlength('Helium Neo') <= 102 * scale:
                        break
                    size -= 1
                draw = ImageDraw.Draw(wordmark)
                draw.text((38 * scale, 16 * scale),
                          'Helium Neo',
                          font=font,
                          fill='white' if light else '#211534',
                          anchor='lm')
                wordmark.save(BRANDING / f'product_logo{"_white" if light else ""}{suffix}.png')
        catalog = temp / 'Assets.xcassets'
        shutil.copytree(BRANDING / 'macos/Assets.xcassets', catalog)
        appset = catalog / 'AppIcon.appiconset'
        for size in [16, 32, 64, 128, 256, 512, 1024]:
            raw.resize((size, size), Image.Resampling.LANCZOS).save(appset / f'appicon_{size}.png')
        iconset = temp / 'AppIcon.iconset'
        iconset.mkdir()
        for size in [16, 32, 128, 256, 512]:
            for factor in [1, 2]:
                raw.resize((size * factor, size * factor), Image.Resampling.LANCZOS).save(
                    iconset / f'icon_{size}x{size}{"@2x" if factor == 2 else ""}.png')
        subprocess.run(
            ['iconutil', '-c', 'icns',
             str(iconset), '-o',
             str(BRANDING / 'macos/app.icns')],
            check=True)
        output = temp / 'compiled'
        output.mkdir()
        subprocess.run([
            'xcrun',
            'actool',
            '--output-format',
            'human-readable-text',
            '--notices',
            '--warnings',
            '--errors',
            '--platform',
            'macosx',
            '--target-device',
            'mac',
            '--minimum-deployment-target',
            '13.0',
            '--app-icon',
            'AppIcon',
            '--include-all-app-icons',
            '--enable-icon-stack-fallback-generation=enabled',
            '--lightweight-asset-runtime-mode=enabled',
            '--output-partial-info-plist',
            str(temp / 'partial.plist'),
            '--compile',
            str(output),
            str(catalog),
            str(ICON_COMPOSER),
        ],
                       check=True)
        shutil.copy2(output / 'Assets.car', BRANDING / 'macos/Assets.car')
    print('Generated Helium Neo atom icons, wordmarks, app.icns and Assets.car.')


if __name__ == '__main__':
    main()
