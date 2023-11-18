import math

import cairo

from colour import Colour
from drawing import saved
from image import to_pillow


size = 1024

surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
ctx = cairo.Context(surface)
ctx.scale(size / 4096, size / 4096)

face = cairo.ToyFontFace("Roboto Condensed Italic", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)


ctx.set_font_size(200)
text_colour = Colour.from_spec("#5d60be")
halo_colour = Colour.from_spec("rgba(255,255,255,128)")

text = "Hello"

x = 2000
y = 2000


rotation = 45

with saved(ctx):
    ctx.translate(x, y)

    matrix = cairo.Matrix(
        xx=200 * (math.cos(math.radians(rotation))),
        xy=200 * (math.sin(math.radians(rotation))),
        yx=200 * (-math.sin(math.radians(rotation))),
        yy=200 * (math.cos(math.radians(rotation))),
    )

    ctx.set_font_face(face)
    ctx.set_font_size(200)
    ctx.set_font_matrix(matrix)
    scaled = ctx.get_scaled_font()
    glyphs = scaled.text_to_glyphs(0, 0, text)

    ctx.glyph_path(glyphs[0])

    ctx.set_line_width(20)
    # ctx.set_dash([40,40])
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    halo_colour.apply_to(ctx)
    ctx.stroke()

    ctx.move_to(0,0)
    text_colour.apply_to(ctx)
    ctx.show_text(text)


img = to_pillow(surface)
img.show()
