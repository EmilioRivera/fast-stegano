from PIL import Image
import numpy as np
from pathlib import Path
import datetime
import click
import math
import logging
from linear_encoding_methods import MODES, LossyEncoder, LosslessEncoder, BaseEncoder, METHOD_LOSSLESS, METHOD_LOSSY, compute_method_used, JpegEncoder
from linear_utils import len_to_np8_16, np8_to_number_16

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(funcName)18s: %(message)s',
)

def filename_if_missing(input_file_path, suffix):
    bn = input_file_path.stem
    output = '{}_{}.png'.format(bn, suffix)
    if Path(output).exists():
        now = datetime.datetime.now()
        output = '{}_{}_{}.png'.format(bn, suffix, now.strftime('%Y-%M-%d-%H-%M-%S'))
    return output


def calculate_scale_factor(base, secret, mode: BaseEncoder):
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

# TODO: Force lossy/lossless mode
@cli.command()
@click.option('--base', required=True, type=click.Path(exists=True, dir_okay=False), help='Image that will hide another image')
@click.option('--secret', required=True, type=click.Path(exists=True, dir_okay=False), help='Image that will be hidden')
@click.option('--output', required=False, type=click.Path(), help='Output image')
@click.option('--base-resize', required=False, type=float, default=1.0, help='Resize to apply to input image regardless of options specified.')
@click.option('--secret-resize', required=False, type=float, default=1.0, help='Resize to apply to input image regardless of options specified.')
@click.option('--base-resize-lossless', is_flag=True, type=bool, help='Resize the input image (bigger) so that lossless secret can be hidden. No resize is done if the data would already fit.')
@click.option('--secret-resize-lossless', is_flag=True, type=bool, help='Resize the input image (smaller) so that lossless secret can be hidden. No resize is done if the data would already fit.')
@click.option('--force-jpeg', is_flag=True, type=bool, help='Save the jpeg of the secret to save space')
@click.option('--fill-with-noise/--no-noise', default=False, help='If the leftover space should contain noise')
@click.pass_context
def hide(ctx, base, secret, output, base_resize_lossless, force_jpeg, secret_resize_lossless, base_resize, secret_resize, fill_with_noise):
    for param in ctx.params.items():
        logging.info('Using parameter {}: {}'.format(*param))
    if output is None:
        output = filename_if_missing(Path(secret), 'hidden')
    
    base_image, secret_image = Image.open(base), Image.open(secret)
    if base_resize != 1.0:
        assert base_resize > 0
        b_w, b_h = calculate_scaled_dimensions(base_image.width, base_image.height, base_resize)
        logging.info('Rescaling base image to size ({}, {}). Scale of {}'.format(b_w, b_h, base_resize))
        base_image = base_image.resize((b_w, b_h))
    if secret_resize != 1.0:
        assert secret_resize > 0
        s_w, s_h = calculate_scaled_dimensions(secret_image.width, secret_image.height, secret_resize)
        logging.info('Rescaling secret image to size ({}, {}). Scale of {}'.format(s_w, s_h, secret_resize))
        secret_image = secret_image.resize((s_w, s_h))

    modes = check_supported_modes(base_image, secret_image)
    mode = None
    if force_jpeg:
        mode = JpegEncoder
    # We should resize if needed
    elif base_resize_lossless or secret_resize_lossless:
        # Check if we need to even resize one of the images
        if LossyEncoder not in modes:
            required_scale = calculate_scale_factor(base_image, secret_image, LossyEncoder)
            assert required_scale > 1.0
            if base_resize_lossless:
                # Rather resize the base image than to downside the secret
                nw, nh = calculate_scaled_dimensions(base_image.width, base_image.height, required_scale)
                logging.info('Creating a new resized base image of size ({0:d}, {0:d}) to fit lossless (scale of {0:.2f}).'.format(nw, nh, required_scale))
                base_image = base_image.resize((nw, nh))
            else:
                nw, nh = calculate_scaled_dimensions(base_image.width, base_image.height, 1.0 / required_scale)
                logging.info('Creating a new resized secret image of size ({0:d}, {0:d}) to fit lossless (scale of {0:.2f}).'.format(nw, nh, 1.0 / required_scale))
                secret_image = secret_image.resize((nw, nh))

        mode = LossyEncoder
    else:
        if LossyEncoder in modes:
            mode = LossyEncoder
        elif LossyEncoder in modes:
            mode = LossyEncoder
        else:
            raise ValueError('Base image is not big enough to hide even when using lossy. No resize option specified')

    logging.info('Using n = {} with method {} - filling with noise'.format(4, mode))
    encoder = mode()
    try:
        merged_image = encoder.hide(base_image, secret_image, add_noise=fill_with_noise, engrave_method=True)
    except AssertionError as e:
        logging.error('Assertion error while merging.')
        logging.error(e)
        exit(1)
    else:
        merged_image.save(output)

@cli.command()
@click.option('--base', required=True, type=click.Path(exists=True, dir_okay=False), help='Image containing secret')
@click.option('--output', required=False, type=click.Path(), help='Output image')
@click.pass_context
def reveal(ctx, base, output):
    for param in ctx.params.items():
        logging.info('Using parameter {}: {}'.format(*param))
    if output is None:
        output = filename_if_missing(Path(base), 'revealed')
    base_image = Image.open(base)
    method = compute_method_used(base_image)
    if method is not None:
        encoder = method()
        unmerged_image = encoder.reveal(base_image)
    kwargs = dict()
    if method == JpegEncoder:
        kwargs['quality'] = 100
        kwargs['optimize'] = True
        if output.endswith('.png'):
            output = '{}.jpg'.format(output[:-4])
            logging.info('Original image was jpeg encoded, saving as {}'.format(output))
    unmerged_image.save(output, **kwargs)

if __name__ == "__main__":
    cli()
