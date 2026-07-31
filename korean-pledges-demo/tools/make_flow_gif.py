"""Generate assets/korean_pledges_flow.gif — the animated decision story.

Storyboard (matches the style of assets/attribution_flow.gif: dark surface,
monospace chips, sequential build):
  1. title: decision: distance_metric
  2. the mahalanobis option card + "theory: shape-aware -> assumed best"
  3. amber chip: proposed_by: claude_code (methodology)
  4. the evidence: retention bars grow (68/218 vs 161/218), over-rejection tag
  5. red strike + excluded tag
  6. indigo chip: excluded_by: oliver (validation) . 2026-06-11
  7. green line: euclidean -> adopted by the manuscript
  8. serif caption: theory proposed; evidence and a human ruled.

Deterministic output. Side effect: writes ../../assets/korean_pledges_flow.gif.
Run from korean-pledges-demo/:  uv run --with pillow python tools/make_flow_gif.py
(Pillow is needed only for asset regeneration, not for the demo itself.)
Colors for the two bars were checked with a palette validator against the
#111625 surface (CVD and normal-vision separation, contrast >= 3:1); the
excluded bar is deliberately low-chroma status grey, reinforced by the
strike, the red tag, and direct labels.
"""

from __future__ import annotations

from pathlib import Path

# Pillow is a regeneration-only dependency (run via `uv run --with pillow`),
# deliberately not installed in the demo venv.
from PIL import Image, ImageDraw, ImageFont  # pyright: ignore[reportMissingImports]

W, H = 640, 360
BG = "#111625"
INK = "#e2e8f0"
MUTED = "#94a3b8"
AMBER = "#d97706"
AMBER_TXT = "#fbbf24"
INDIGO = "#6366f1"
INDIGO_TXT = "#a5b0f9"
RED = "#ef4444"
GREEN_TXT = "#4ade80"
BAR_ACCEPTED = "#a5b0f9"
BAR_EXCLUDED = "#5f6b80"
BAR_TRACK = "#1e2637"

MONO = "/System/Library/Fonts/Menlo.ttc"
SERIF_ITALIC = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"

OUT = Path(__file__).resolve().parents[2] / "assets" / "korean_pledges_flow.gif"


def get_font(size: int, serif: bool = False) -> ImageFont.FreeTypeFont:
    """Load a sized font (side-effect free; fonts are system files)."""
    return ImageFont.truetype(SERIF_ITALIC if serif else MONO, size)


def ease(t: float) -> float:
    """Ease-out cubic on t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def fade(step: int, start: int, span: int = 10) -> float:
    """Opacity in [0, 1] for an element appearing at `start`."""
    return ease((step - start) / span)


def draw_chip(
    im: Image.Image,
    xy: tuple[int, int],
    text: str,
    color: str,
    text_color: str,
    alpha: float,
    font: ImageFont.FreeTypeFont,
) -> None:
    """Composite one rounded outline chip with `alpha` onto `im`."""
    if alpha <= 0:
        return
    pad_x, pad_y = 10, 5
    tw = int(font.getlength(text))
    th = int(font.size)
    w, h = tw + 2 * pad_x, th + 2 * pad_y
    layer = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((1, 1, w + 1, h + 1), radius=8, outline=color, width=2)
    d.text((2 + pad_x, 1 + pad_y - 1), text, font=font, fill=text_color)
    layer.putalpha(layer.getchannel("A").point(lambda a: int(a * alpha)))
    im.alpha_composite(layer, (xy[0], xy[1]))


def draw_text(
    im: Image.Image,
    xy: tuple[int, int],
    text: str,
    fill: str,
    alpha: float,
    font: ImageFont.FreeTypeFont,
    anchor: str | None = None,
) -> None:
    """Composite one text run with `alpha` onto `im`."""
    if alpha <= 0:
        return
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text(xy, text, font=font, fill=fill, anchor=anchor)
    layer.putalpha(layer.getchannel("A").point(lambda a: int(a * alpha)))
    im.alpha_composite(layer)


def render_frame(step: int) -> Image.Image:
    """Render one frame of the storyboard (pure function of `step`)."""
    im = Image.new("RGBA", (W, H), BG)
    f13 = get_font(13)
    f12 = get_font(12)
    f11 = get_font(11)
    f10 = get_font(10)
    fcap = get_font(14, serif=True)

    # 1 - title
    draw_text(im, (W // 2, 26), "decision: distance_metric", INK, fade(step, 0), f13, "mm")

    # 2 - option card
    a_card = fade(step, 8)
    if a_card > 0:
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle((150, 52, 490, 84), radius=8, outline="#475569", width=2)
        d.text((170, 60), "mahalanobis — shape-aware distance", font=f12, fill=INK)
        layer.putalpha(layer.getchannel("A").point(lambda a: int(a * a_card)))
        im.alpha_composite(layer)
    draw_text(
        im, (W // 2, 100), "theory: adapts to cluster shape → assumed best",
        MUTED, fade(step, 12), f10, "mm",
    )

    # 3 - proposed_by chip
    draw_chip(
        im, (176, 114), "proposed_by: claude_code (methodology)",
        AMBER, AMBER_TXT, fade(step, 18), f11,
    )

    # 4 - evidence bars
    a_ev = fade(step, 28)
    if a_ev > 0:
        draw_text(im, (150, 152), "the evidence — sentences kept, of 218:", MUTED, a_ev, f10)
        grow = ease((step - 32) / 16)
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        # mahalanobis bar (track then fill)
        d.rounded_rectangle((150, 170, 430, 182), radius=4, fill=BAR_TRACK)
        w_m = int(280 * 0.312 * grow)
        if w_m > 8:
            d.rounded_rectangle((150, 170, 150 + w_m, 182), radius=4, fill=BAR_EXCLUDED)
        d.text((440, 170), "68/218 (31.2%)", font=f11, fill=INK)
        # euclidean bar
        d.rounded_rectangle((150, 196, 430, 208), radius=4, fill=BAR_TRACK)
        w_e = int(280 * 0.739 * grow)
        if w_e > 8:
            d.rounded_rectangle((150, 196, 150 + w_e, 208), radius=4, fill=BAR_ACCEPTED)
        d.text((440, 196), "161/218 (73.9%)", font=f11, fill=INK)
        d.text((136, 170), "M", font=f10, fill=MUTED, anchor="rm")
        d.text((136, 196), "E", font=f10, fill=MUTED, anchor="rm")
        layer.putalpha(layer.getchannel("A").point(lambda a: int(a * a_ev)))
        im.alpha_composite(layer)
    draw_text(
        im, (W // 2, 226), "the assumed-best metric was over-rejecting",
        RED, fade(step, 46), f10, "mm",
    )

    # 5 - strike + excluded tag
    a_strike = ease((step - 52) / 8)
    if a_strike > 0:
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        x_end = 150 + int((490 - 150) * a_strike)
        d.line((150, 84, x_end, 52), fill=RED, width=3)
        layer.putalpha(layer.getchannel("A").point(lambda a: int(a * 0.9)))
        im.alpha_composite(layer)
    a_tag = fade(step, 58, 6)
    if a_tag > 0:
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle((498, 46, 574, 66), radius=4, fill=RED)
        d.text((536, 56), "excluded", font=f10, fill="#ffffff", anchor="mm")
        layer.putalpha(layer.getchannel("A").point(lambda a: int(a * a_tag)))
        im.alpha_composite(layer)

    # 6 - excluded_by chip
    draw_chip(
        im, (176, 248), "excluded_by: oliver (validation) · 2026-06-11",
        INDIGO, INDIGO_TXT, fade(step, 64), f11,
    )

    # 7 - adopted line
    draw_text(
        im, (W // 2, 296), "euclidean → adopted by the manuscript",
        GREEN_TXT, fade(step, 74), f12, "mm",
    )

    # 8 - caption
    draw_text(
        im, (W // 2, 334), "theory proposed; evidence and a human ruled.",
        INK, fade(step, 84), fcap, "mm",
    )
    return im


def main() -> None:
    steps = 100
    frames = [render_frame(s).convert("P", palette=Image.Palette.ADAPTIVE) for s in range(steps)]
    durations = [65] * (steps - 1) + [2200]
    OUT.parent.mkdir(exist_ok=True)
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KiB, {steps} frames)")


if __name__ == "__main__":
    main()
