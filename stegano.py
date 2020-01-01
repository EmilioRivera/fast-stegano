import click
from PIL import Image, ImageMath

MASKS = {
    0: 0b00000000,
    1: 0b10000000,
    2: 0b11000000,
    3: 0b11100000,
    4: 0b11110000,
    5: 0b11111000,
    6: 0b11111100,
    7: 0b11111110,
    8: 0b11111111,
}

def lsb_components(img, n):
    r, g, b = img.split()
    o_r = ImageMath.eval('a & m', a=r, m=MASKS[8-n])
    o_g = ImageMath.eval('a & m', a=g, m=MASKS[8-n])
    o_b = ImageMath.eval('a & m', a=b, m=MASKS[8-n])
    return o_r, o_g, o_b

# Returns a cropped image, the same size as img2 (if img2 is smaller than img1).
def _naive_merge(img1, img2, n=4):
    r1, g1, b1 = img1.split()
    r2, g2, b2 = img2.split()
    o_r = ImageMath.eval("(a & m) + (b >> n) ", a=r1, b=r2, m=MASKS[8-n], n=8-n).convert('L')
    o_g = ImageMath.eval("(a & m) + (b >> n) ", a=g1, b=g2, m=MASKS[8-n], n=8-n).convert('L')
    o_b = ImageMath.eval("(a & m) + (b >> n) ", a=b1, b=b2, m=MASKS[8-n], n=8-n).convert('L')
    output = Image.merge("RGB", (o_r, o_g, o_b))
    return output

# This method returns an image the is the same size as img1.
# Img1 has its `n` LSBs put to 0 first. This incurs overhead.
def _full_merge(img1, img2, n=4):
    # We need to remove the LSB for each pixels
    cp_r, cp_g, cp_b = lsb_components(img1, n)
    r2, g2, b2 = img2.split()
    o_r = ImageMath.eval("a + (b >> n) ", a=cp_r, b=r2, n=8-n).convert('L')
    o_g = ImageMath.eval("a + (b >> n) ", a=cp_g, b=g2, n=8-n).convert('L')
    o_b = ImageMath.eval("a + (b >> n) ", a=cp_b, b=b2, n=8-n).convert('L')
    lsb_merged = Image.merge('RGB', (cp_r.convert('L'), cp_g.convert('L'), cp_b.convert('L')))
    output = Image.merge("RGB", (o_r, o_g, o_b))
    lsb_merged.paste(output)
    return lsb_merged



def _unmerge(img, n=4):
    r, g, b = img.split()
    o_r = ImageMath.eval(" (a << n) & m ", a=r, m=MASKS[n], n=8-n).convert('L')
    o_g = ImageMath.eval(" (a << n) & m ", a=g, m=MASKS[n], n=8-n).convert('L')
    o_b = ImageMath.eval(" (a << n) & m ", a=b, m=MASKS[n], n=8-n).convert('L')
    output = Image.merge("RGB", (o_r, o_g, o_b))
    return output


@click.group()
def cli():
    pass


@cli.command()
@click.option('--img1', required=True, type=str, help='Image that will hide another image')
@click.option('--img2', required=True, type=str, help='Image that will be hidden')
@click.option('--output', required=True, type=str, help='Output image')
@click.option('-n', type=int, help='Number of bits to use')
@click.option('--full/--naive', default=False, help='Use the full original image (slower)')
def merge(img1, img2, output, n, full):
    print('Using n = {} with method {}'.format(n, 'FULL' if full else 'CROPPED'))
    if full:
        merged_image = _full_merge(Image.open(img1), Image.open(img2), n)
    else:
        merged_image = _naive_merge(Image.open(img1), Image.open(img2), n)
    merged_image.save(output)


@cli.command()
@click.option('--img', required=True, type=str, help='Image that will be hidden')
@click.option('--output', required=True, type=str, help='Output image')
@click.option('-n', type=int, help='Number of bits to use')
@click.option('--crop/--no-crop', default=False, help='Whether to crop the output image. Useful when image was saved with --full')
def unmerge(img, output, n, crop):
    unmerged_image = _unmerge(Image.open(img), n)
    if crop:
        box = unmerged_image.getbbox()
        unmerged_image = unmerged_image.crop(box)
    unmerged_image.save(output)


if __name__ == "__main__":
    cli()
