import click
from PIL import Image, ImageMath

MASKS = {
    1: 0b10000000,
    2: 0b11000000,
    3: 0b11100000,
    4: 0b11110000,
    5: 0b11111000,
    6: 0b11111100,
    7: 0b11111110,
}

def _merge(img1, img2, n=4):
    r1, g1, b1 = img1.split()
    r2, g2, b2 = img2.split()
    o_r = ImageMath.eval("(a & m) + (b >> n) ", a=r1, b=r2, m=MASKS[8-n], n=8-n).convert('L')
    o_g = ImageMath.eval("(a & m) + (b >> n) ", a=g1, b=g2, m=MASKS[8-n], n=8-n).convert('L')
    o_b = ImageMath.eval("(a & m) + (b >> n) ", a=b1, b=b2, m=MASKS[8-n], n=8-n).convert('L')
    output = Image.merge("RGB", (o_r, o_g, o_b))
    return output

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
def merge(img1, img2, output, n):
    merged_image = _merge(Image.open(img1), Image.open(img2), n)
    merged_image.save(output)


@cli.command()
@click.option('--img', required=True, type=str, help='Image that will be hidden')
@click.option('--output', required=True, type=str, help='Output image')
@click.option('-n', type=int, help='Number of bits to use')
def unmerge(img, output, n):
    unmerged_image = _unmerge(Image.open(img), n)
    unmerged_image.save(output)


if __name__ == "__main__":
    cli()
