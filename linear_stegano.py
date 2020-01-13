from PIL import Image
import numpy as np
from pathlib import Path
import datetime
import click
import math
from linear_encoding_methods import MODES, LossyEncoding, LosslessEncoding, EncodingMethod, METHOD_LOSSLESS, METHOD_LOSSY
from linear_utils import len_to_np8_16, np8_to_number_16

#
# Lossy linear steganography
#
def _construct_loss_with_dims(a, b, add_noise=False):
    # 32 bits are needed to encode the length
    # Using n = 4 for the LSB, we need 8 entries to encode the length of the message.
    # We will occupy 9 entries, the last one being unused. Just to get a total of 3 pixels
    offset = 9
    assert a.size >= offset + b.size

    hidden_noise = np.zeros(a.size, dtype=np.uint8)
    fake = a.copy('C')
    
    
    # The 8 first value will be the length of the message, the additional 9th value is not used
    width_np, height_np = len_to_np8_16(b.shape[0]), len_to_np8_16(b.shape[1])
    hidden_noise[:4] = width_np
    hidden_noise[4:8] = height_np
    # Put the hidden image data in target
    start, end = offset, offset + b.size
    hidden_noise[offset:end] = (b.ravel('C') & 0xF0) >> 4
    
    if add_noise:
        hidden_noise[end:] = np.random.randint(low=0x00, high=0x0F, size=a.size-end, dtype=np.uint8)
    
    # Discard the LSB from the fake up until the last fake data
    fake[:end] = fake[:end] & 0xF0
    fake = fake.ravel('C') + hidden_noise
    return fake.reshape(a.shape)


def _reconstruct_loss_with_dims(a):
#     print((a.ravel()[:9] & 0x0F) << 4)
    # Get the dimensions
    flat = (a.ravel() & 0x0F)
    width, height = np8_to_number_16(flat[:4]), np8_to_number_16(flat[4:8])
#     print(width, height)
    n_elems = width * height * 3
    start, end = 9, 9 + n_elems
    rr, rg, rb  = flat[start:end:3] << 4, flat[start+1:end+1:3] << 4, flat[start+2:end+2:3] << 4
    packed = np.stack([rr, rg, rb], axis=-1)
#     print(packed.shape)
    return width, height, packed.reshape(width, height, 3)


#
# Lossless linear steganography
# 
def _construct_lossless_with_dims(a, b, add_noise=False):
    # 32 bits are needed to encode the length
    # Using n = 4 for the LSB, we need 8 entries to encode the length of the message.
    # We will occupy 9 entries, the last one being unused. Just to get a total of 3 pixels
    offset = 9
    # We need to encode each pixel into the 4 LSB, resulting in twice the size
    # assert base.width * base.height > secret.width * secret.height * 2
    assert a.size >= offset + b.size * 2

    hidden_noise = np.zeros(a.size, dtype=np.uint8)
    fake = a.copy('C')
    
    # Discard the LSB from the fake
    fake = fake & 0xF0
    
    # The 8 first value will be the length of the message, the additional 9th value is not used
    width_np, height_np = len_to_np8_16(b.shape[0]), len_to_np8_16(b.shape[1])
    hidden_noise[:4] = width_np
    hidden_noise[4:8] = height_np
    
    red_noise = np.repeat(b[:,:,0], 2, -1).ravel('C')
    red_noise[0::2] = (red_noise[0::2] & 0xF0) >> 4  # MSB of red
    red_noise[1::2] = (red_noise[1::2] & 0x0F)  # LSB of red
    
    green_noise = np.repeat(b[:,:,1], 2, -1).ravel('C')
    green_noise[0::2] = (green_noise[0::2] & 0xF0) >> 4  # MSB of green
    green_noise[1::2] = (green_noise[1::2] & 0x0F)  # LSB of green
    
    blue_noise = np.repeat(b[:,:,2], 2, -1).ravel('C')
    blue_noise[0::2] = (blue_noise[0::2] & 0xF0) >> 4  # MSB of blue
    blue_noise[1::2] = (blue_noise[1::2] & 0x0F)  # LSB of blue
    
    
    # Put the hidden image data in target
    start, end = offset, offset + b.size * 2
    # When raveled, they will be consecutive, i.e all red data, then all green data, then all blue data
    stacked_arr = np.stack([red_noise, green_noise, blue_noise])
    hidden_noise[offset:end] = stacked_arr.ravel('C')
    
    if add_noise:
        hidden_noise[end:] = np.random.randint(low=0x00, high=0x0F, size=a.size-end, dtype=np.uint8)

    fake = fake.ravel('C') + hidden_noise
    return fake.reshape(a.shape)


def _reconstruct_lossless_with_dims(a):
    # Get the dimensions
    flat = (a.ravel('C') & 0x0F)
    width, height = np8_to_number_16(flat[:4]), np8_to_number_16(flat[4:8])
    
    per_channel_n_elem = width * height * 2
    
    red_start, red_end = 9, 9 + per_channel_n_elem
    green_start, green_end = red_end, red_end + per_channel_n_elem
    blue_start, blue_end = green_end, green_end + per_channel_n_elem
    rr, rg, rb  = flat[red_start:red_end], flat[green_start:green_end], flat[blue_start:blue_end]
    output = np.zeros((width, height, 3), dtype=np.uint8)
    output[:,:,0] = (((rr[0::2]) << 4) + (rr[1::2])).reshape(width, height)
    output[:,:,1] = (((rg[0::2]) << 4) + (rg[1::2])).reshape(width, height)
    output[:,:,2] = (((rb[0::2]) << 4) + (rb[1::2])).reshape(width, height)
    return width, height, output.reshape(width, height, 3)


def _read_method(arr):
    return arr.ravel('C')[8] & 0x0F


def _engrave_method(arr, method):
    arr.ravel('C')[8] |= method


def merge_with_dims(base, secret, lossy, add_noise, engrave_method=False):
    a = np.asarray(base)
    b = np.asarray(secret)
    fake_data = _construct_loss_with_dims(a, b, add_noise=add_noise) if lossy else _construct_lossless_with_dims(a, b, add_noise=add_noise)
    if engrave_method:
        _engrave_method(fake_data, METHOD_LOSSY if lossy else METHOD_LOSSLESS)
    fake = Image.fromarray(fake_data.astype(np.uint8))
    return fake


def unmerge_with_dims(base, lossy, read_method=False):
    c = np.asarray(base, dtype=np.uint8)
    if read_method:
        engraved_bit = _read_method(c)
        if engraved_bit != METHOD_LOSSLESS and engraved_bit != METHOD_LOSSY:
            raise ValueError('Unable to read the engraved bit. Value is {0:02x}'.format(engraved_bit))
        lossy = engraved_bit == METHOD_LOSSY
    w, h, f = _reconstruct_loss_with_dims(c) if lossy else _reconstruct_lossless_with_dims(c)
    i = Image.fromarray(f, mode='RGB')
    return i

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
    return int(math.ceil(initial_width * scale)), int(math.ceil(initial_height * scale))


def check_supported_modes(base, secret):
    b_w, b_h = base.size
    s_w, s_h = secret.size
    supported_modes = []
    global MODES
    # for mode in MODES:
        # if mode.can_fit(base, secret)
    return [mode for mode in MODES if mode.can_fit(base, secret)]

@click.group()
def cli():
    pass

@cli.command()
@click.option('--base', required=True, type=str, help='Image that will hide another image')
@click.option('--secret', required=True, type=str, help='Image that will be hidden')
@click.option('--output', required=False, type=str, help='Output image')
@click.option('--base-resize-lossless', is_flag=True, type=bool, help='Resize the input image so that lossless secret can be hidden')
def hide(base, secret, output, base_resize_lossless):
    if output is None:
        output = filename_if_missing(Path(secret), 'hidden')
    
    base_image, secret_image = Image.open(base), Image.open(secret)
    modes = check_supported_modes(base_image, secret_image)
    mode = None
    if not base_resize_lossless:
        if LosslessEncoding in modes:
            mode = LosslessEncoding
        elif LossyEncoding in modes:
            mode = LossyEncoding
        else:
            raise ValueError('Base image is not big enough to hide even when using lossy. No resize option specified')
    else:
        if LosslessEncoding not in modes:
            required_scale = calculate_scale_factor(base_image, secret_image, LosslessEncoding)
            nw, nh = calculate_scaled_dimensions(base_image.width, base_image.height, required_scale)
            assert required_scale > 1.0
            print('Creating a new resized image of size ({}, {}) to fit lossless (scale of {}).'.format(nw, nh, required_scale))
            base_image = base_image.resize((nw, nh))
        mode = LosslessEncoding

    print('Using n = {} with method {} - filling with noise'.format(4, mode))
    merged_image = mode.hide(base_image, secret_image, add_noise=True, engrave_method=True)
    merged_image.save(output)

@cli.command()
@click.option('--base', required=True, type=str, help='Image containing secret')
@click.option('--output', required=False, type=str, help='Output image')
def reveal(base, output):
    if output is None:
        output = filename_if_missing(Path(base), 'revealed')
    # TODO: Create a function in linear encoding methods to resolve this
    base_image = Image.open(base)
    _arr = np.asarray(base_image, dtype=np.uint8)
    method_value = _read_method(_arr)
    del _arr
    method = next((m for m in MODES if m.value == method_value), None)
    if method is not None:
        unmerged_image = method.reveal(base_image)
    unmerged_image.save(output)

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
