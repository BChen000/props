"""A Christmas present instead of the heart: 137 marbles build a red gift box with a gold ribbon cross and a bow.

Run with EPISODE=present. The picture is coloured by region (box, ribbon, bow) rather than by band, so every marble
can take any spot while the picture grows, and each marble wears the colour of the spot it ends up on: the run shows
a mix of red and gold, and the present only shows once the last marbles push it into place.
"""
FILE = "Marble_Run_Present"
SHAPE = "present"
N_MARBLES = 137
REGION_COLOURS = True
REGION_SRGB = {"box": (222, 34, 44), "ribbon": (250, 192, 36), "bow": (250, 192, 36)}
PRESENT = dict(half_w=13.0, depth=17.0, bow_r=3.0, bow_dx=1.1, bow_dy=0.8, ribbon_half=2.1, ribbon_at=0.45)
CUSP_Z = 6.6
WATERMARK_Y = 0.98
THUMB_FRAME = None
