import click
from PIL import Image, ImageMath

def _merge(img1, img2):
    r1, g1, b1 = img1.split()
    r2, g2, b2 = img2.split()
    o_r = ImageMath.eval("(a & 0xF0) + (b >> 4) ", a=r1, b=r2).convert('L')
    o_g = ImageMath.eval("(a & 0xF0) + (b >> 4) ", a=g1, b=g2).convert('L')
    o_b = ImageMath.eval("(a & 0xF0) + (b >> 4) ", a=b1, b=b2).convert('L')
    output = Image.merge("RGB", (o_r, o_g, o_b))
    return output

def _unmerge(img):
    r, g, b = img.split()
    o_r = ImageMath.eval(" (a << 4) & 0xF0 ", a=r).convert('L')
    o_g = ImageMath.eval(" (a << 4) & 0xF0 ", a=g).convert('L')
    o_b = ImageMath.eval(" (a << 4) & 0xF0 ", a=b).convert('L')
    output = Image.merge("RGB", (o_r, o_g, o_b))
    return output


@click.group()
def cli():
    pass


@cli.command()
@click.option('--img1', required=True, type=str, help='Image that will hide another image')
@click.option('--img2', required=True, type=str, help='Image that will be hidden')
@click.option('--output', required=True, type=str, help='Output image')
def merge(img1, img2, output):
    merged_image = _merge(Image.open(img1), Image.open(img2))
    merged_image.save(output)


@cli.command()
@click.option('--img', required=True, type=str, help='Image that will be hidden')
@click.option('--output', required=True, type=str, help='Output image')
def unmerge(img, output):
    unmerged_image = _unmerge(Image.open(img))
    unmerged_image.save(output)


if __name__ == "__main__":
    cli()
