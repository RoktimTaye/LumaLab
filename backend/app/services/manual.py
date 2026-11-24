"""Bounded manual tone controls and deterministic geometry."""
from math import sin, cos, radians, floor
import numpy as np
from PIL import Image, ImageOps, ImageFilter


def tone_table(exposure=0, highlights=0, shadows=0, ambience=0):
    x = np.arange(256, dtype=np.float64) / 255
    x = np.clip(x * 2 ** exposure, 0, 1)
    x = np.clip(x + shadows / 100 * .35 * (1-x)**2 + highlights / 100 * .35 * x**2
                + ambience / 100 * .3 * (1-2*x) * (4*x*(1-x)), 0, 1)
    return np.round(x * 255).astype(np.uint8).tolist()


def geometry_size(width, height, settings):
    angle = radians(abs(settings.straighten))
    scale = min(width / (width*cos(angle)+height*sin(angle)), height / (height*cos(angle)+width*sin(angle)))
    w, h = max(1, floor(width*scale)), max(1, floor(height*scale))
    return (h, w) if settings.rotation in (90,270) else (w,h)


def transform(image, settings):
    if settings.straighten:
        width, height = image.size
        angle = radians(abs(settings.straighten))
        scale = min(width / (width*cos(angle)+height*sin(angle)), height / (height*cos(angle)+width*sin(angle)))
        w, h = max(1, floor(width*scale)), max(1, floor(height*scale))
        rotated = image.rotate(-settings.straighten, resample=Image.Resampling.BICUBIC, expand=False)
        left, top = (width-w)//2, (height-h)//2
        image = rotated.crop((left, top, left+w, top+h))
    if settings.flip_horizontal:
        image = ImageOps.mirror(image)
    if settings.flip_vertical:
        image = ImageOps.flip(image)
    if settings.rotation:
        image = image.transpose({90: Image.Transpose.ROTATE_270,180: Image.Transpose.ROTATE_180,270: Image.Transpose.ROTATE_90}[settings.rotation])
    return image


def add_structure(image, amount):
    if not amount:
        return image
    # Detail is computed from fixed-source overlapping tiles, not the destination.
    radius = max(1, max(image.size) / 400)
    halo = int(radius*4)+8
    output = Image.new('RGB',image.size)
    for top in range(0,image.height,64):
        bottom=min(top+64,image.height); start=max(0,top-halo); stop=min(image.height,bottom+halo)
        with image.crop((0,start,image.width,stop)) as tile:
            filtered=tile.filter(ImageFilter.UnsharpMask(radius=radius,percent=amount,threshold=4))
            output.paste(filtered.crop((0,top-start,image.width,bottom-start)),(0,top))
    return output
