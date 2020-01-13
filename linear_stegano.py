from PIL import Image
import numpy as np
from pathlib import Path
import datetime
import click
import math
from linear_encoding_methods import MODES, LossyEncoding, LosslessEncoding, EncodingMethod, METHOD_LOSSLESS, METHOD_LOSSY, compute_method_used, JpegEncodingMethod
from linear_utils import len_to_np8_16, np8_to_number_16

def merge_with_dims(base, secret, lossy, add_noise, engrave_method=False):
    mode = LossyEncoding if lossy else LosslessEncoding
    fake = LosslessEncoding.hide(base, secret, add_noise, engrave_method)
    return fake


def unmerge_with_dims(base, lossy, read_method=False):
    if read_method:
        method = compute_method_used(base)
        assert method is not None
        lossy = engraved_bit == METHOD_LOSSY
    else:
        method = LossyEncoding if lossy else LosslessEncoding
    revealed = method.reveal(base)
    return revealed


def filename_if_missing(input_file_path, suffix):
    bn = input_file_path.stem
    output = '{}_{}.png'.format(bn, suffix)
    if Path(output).exists():
        now = datetime.datetime.now()
        output = '{}_{}_{}.png'.format(bn, suffix, now.strftime('%Y-%M-%d-%H-%M-%S'))
    return output


def calculate_scale_factor(base, secret, mode: EncodingMethod):
    needed_space = mode.needed_hidden_size(secret)
    available_space = mode.available_hidden_size(base)
    scale = math.sqrt(float(needed_space) / available_space)
    return scale


def calculate_scaled_dimensions(initial_width, initial_height, scale):
    if scale > 1.0:
        return int(math.ceil(initial_width * scale)), int(math.ceil(initial_height * scale))
    else:
        return int(math.floor(initial_width * scale)), int(math.floor(initial_height * scale))


def check_supported_modes(base, secret):
    b_w, b_h = base.size
    s_w, s_h = secret.size
    supported_modes = []
    return [mode for mode in MODES if mode.can_fit(base, secret)]

@click.group()
def cli():
    pass

@cli.command()
@click.option('--base', required=True, type=str, help='Image that will hide another image')
@click.option('--secret', required=True, type=str, help='Image that will be hidden')
@click.option('--output', required=False, type=str, help='Output image')
@click.option('--base-resize-lossless', is_flag=True, type=bool, help='Resize the input image (bigger) so that lossless secret can be hidden. No resize is done if the data would already fit.')
@click.option('--secret-resize-lossless', is_flag=True, type=bool, help='Resize the input image (smaller) so that lossless secret can be hidden. No resize is done if the data would already fit.')
@click.option('--force-jpeg', is_flag=True, type=bool, help='Save the jpeg of the secret to save space')
def hide(base, secret, output, base_resize_lossless, force_jpeg, secret_resize_lossless):
    if output is None:
        output = filename_if_missing(Path(secret), 'hidden')
    
    base_image, secret_image = Image.open(base), Image.open(secret)
    modes = check_supported_modes(base_image, secret_image)
    mode = None
    if force_jpeg:
        mode = JpegEncodingMethod
    # We should resize if needed
    elif base_resize_lossless or secret_resize_lossless:
        # Check if we need to even resize one of the images
        if LosslessEncoding not in modes:
            required_scale = calculate_scale_factor(base_image, secret_image, LosslessEncoding)
            assert required_scale > 1.0
            if base_resize_lossless:
                # Rather resize the base image than to downside the secret
                nw, nh = calculate_scaled_dimensions(base_image.width, base_image.height, required_scale)
                print('Creating a new resized base image of size ({0:d}, {0:d}) to fit lossless (scale of {0:.2f}).'.format(nw, nh, required_scale))
                base_image = base_image.resize((nw, nh))
            else:
                nw, nh = calculate_scaled_dimensions(base_image.width, base_image.height, 1.0 / required_scale)
                print('Creating a new resized secret image of size ({0:d}, {0:d}) to fit lossless (scale of {0:.2f}).'.format(nw, nh, 1.0 / required_scale))
                secret_image = secret_image.resize((nw, nh))

        mode = LosslessEncoding
    else:
        if LosslessEncoding in modes:
            mode = LosslessEncoding
        elif LossyEncoding in modes:
            mode = LossyEncoding
        else:
            raise ValueError('Base image is not big enough to hide even when using lossy. No resize option specified')

    print('Using n = {} with method {} - filling with noise'.format(4, mode))
    merged_image = mode.hide(base_image, secret_image, add_noise=True, engrave_method=True)
    merged_image.save(output)

@cli.command()
@click.option('--base', required=True, type=str, help='Image containing secret')
@click.option('--output', required=False, type=str, help='Output image')
def reveal(base, output):
    if output is None:
        output = filename_if_missing(Path(base), 'revealed')
    base_image = Image.open(base)
    method = compute_method_used(base_image)
    if method is not None:
        unmerged_image = method.reveal(base_image)
    kwargs = dict()
    if method == JpegEncodingMethod:
        kwargs['quality'] = 100
        kwargs['optimize'] = True
        if output.endswith('.png'):
            output = '{}.jpg'.format(output[:-4])
            print('Original image was jpeg encoded, saving as {}'.format(output))
    unmerged_image.save(output, **kwargs)

@cli.command()
@click.option('--img1', required=True, type=str, help='Image that will hide another image')
@click.option('--img2', required=True, type=str, help='Image that will be hidden')
@click.option('--output', required=True, type=str, help='Output image')
@click.option('--lossy/--lossless', default=False, help='If the output should be lossy or lossless')
@click.option('--fill-with-noise/--no-noise', default=False, help='If the leftover space should contain noise')
def merge(img1, img2, output, lossy, fill_with_noise):
    print('Using n = {} with method {} - {}'.format(4, 'lossy' if lossy else 'lossless', 'filling with noise' if fill_with_noise else 'no noise'))
    merged_image = merge_with_dims(Image.open(img1), Image.open(img2), lossy=lossy, add_noise=fill_with_noise)
    merged_image.save(output)


@cli.command()
@click.option('--img', required=True, type=str, help='Image that will be hidden')
@click.option('--output', required=True, type=str, help='Output image')
@click.option('--lossy/--lossless', default=False, help='If the hidden image is lossy or lossless')
def unmerge(img, output, lossy):
    unmerged_image = unmerge_with_dims(Image.open(img), lossy=lossy)
    unmerged_image.save(output)



if __name__ == "__main__":
    cli()
