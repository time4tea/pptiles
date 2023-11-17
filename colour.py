import colorsys
import dataclasses
import re
from typing import Tuple

import cairo


@dataclasses.dataclass(frozen=True)
class HLSColour:
    h: float
    l: float
    s: float
    a: float

    def lighten(self, by: float) -> 'HLSColour':
        return HLSColour(self.h, min(self.l + by, 1.0), self.s, self.a)

    def darken(self, by: float) -> 'HLSColour':
        return HLSColour(self.h, max(self.l - by, 0.0), self.s, self.a)

    def rgb(self) -> 'Colour':
        r, g, b = colorsys.hls_to_rgb(self.h, self.l, self.s)
        return Colour(r, g, b, self.a)

    def apply_to(self, context: cairo.Context):
        self.rgb().apply_to(context)


rgb_expr = re.compile(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")
rgba_expr = re.compile(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")
hsl_expr = re.compile(r"hsl\((\d+),\s+(\d+)%,\s*(\d+)%\)")


@dataclasses.dataclass(frozen=True)
class Colour:
    r: float
    g: float
    b: float
    a: float = 1.0

    def rgba(self) -> Tuple[float, float, float, float]:
        return self.r, self.g, self.b, self.a

    def rgb(self) -> Tuple[float, float, float]:
        return self.r, self.g, self.b

    def hls(self) -> HLSColour:
        h, l, s = colorsys.rgb_to_hls(self.r, self.g, self.b)
        return HLSColour(h, l, s, self.a)

    def darken(self, by: float) -> 'Colour':
        return self.hls().darken(by).rgb()

    def lighten(self, by: float) -> 'Colour':
        return self.hls().lighten(by).rgb()

    def alpha(self, new_alpha: float):
        return Colour(self.r, self.g, self.b, new_alpha)

    @staticmethod
    def _rescale(t):
        return map(lambda v: v / 255.0, t)

    def as_hex(self):
        return "".join([
            "%x" % int(self.r * 256),
            "%x" % int(self.g * 256),
            "%x" % int(self.b * 256),
        ])

    @staticmethod
    def hex(hexcolour: str, alpha=1.0):
        if hexcolour.startswith("#"):
            hexcolour = hexcolour[1:]
        r, g, b = Colour._rescale(tuple(int(hexcolour[i:i + 2], 16) for i in (0, 2, 4)))
        return Colour(r, g, b, alpha)

    @staticmethod
    def from_pil(r, g, b, a=255.0):
        return Colour(*Colour._rescale((r, g, b, a)))

    def apply_to(self, context: cairo.Context):
        context.set_source_rgba(*self.rgba())

    @classmethod
    def from_spec(cls, colour_spec) -> 'Colour':
        m = rgb_expr.match(colour_spec)
        if m is not None:
            return Colour.from_pil(
                int(m.group(1)),
                int(m.group(2)),
                int(m.group(3)),
            )
        m = rgba_expr.match(colour_spec)
        if m is not None:
            return Colour.from_pil(
                int(m.group(1)),
                int(m.group(2)),
                int(m.group(3)),
                float(m.group(4)) * 255
            )
        if colour_spec.startswith("#"):
            hex_spec = colour_spec[1:]
            if len(hex_spec) == 3:
                return Colour.from_pil(
                    int(hex_spec[0]*2, 16),
                    int(hex_spec[1]*2, 16),
                    int(hex_spec[2]*2, 16),
                )
            elif len(hex_spec) == 6:
                return Colour.from_pil(
                    int(hex_spec[0:2], 16),
                    int(hex_spec[2:4], 16),
                    int(hex_spec[4:6], 16),
                )
            elif len(hex_spec) == 8:
                return Colour.from_pil(
                    int(hex_spec[0:2], 16),
                    int(hex_spec[2:4], 16),
                    int(hex_spec[4:6], 16),
                    int(hex_spec[6:8], 16),
                )

        m = hsl_expr.match(colour_spec)
        if m is not None:
            return hsl(
                int(m.group(1)) / 360.0,
                int(m.group(2)) / 100.0,
                int(m.group(3)) / 100.0).rgb()
        print(f"Can't parse {colour_spec}")
        return Colour(1.0, 1.0, 1.0)


def hsl(h, s, l, a=1.0) -> HLSColour:
    return HLSColour(h, l, s, a)


if __name__ == "__main__":
    c = Colour.from_spec("rgb(236,238,204)")
    print(c)
    print(c.as_hex())