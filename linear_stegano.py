from PIL import Image
import numpy as np
import click

# TODO: Better method encoding scheme
METHOD_LOSSLESS = 0x01
METHOD_LOSSY    = 0x02


# Utilities
def len_to_np8_16(number):
    # Returns a numpy array of np8 corresponding to the representation of `number`
    # The MSBs are at the front of the returned array
    assert number <= 0xFFFF
    r = np.ndarray((4, ), dtype=np.uint8)
    for i, o in enumerate(range(0, 16, 4)):
        m = (number & (0xF000 >> o)) >> (12-o)
#         print(i, o, m, '{0:032b}'.format(0xF000 >> o), '{0:032b}'.format(m), sep='\t')
        r[i] = m
    return r

def np8_to_number_16(np8_len_arr):
    total = 0
    for i,v in enumerate(np8_len_arr):
#         print(v)
        total += int(v) << (12- 4*i)
#     print(total)
    return total

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


@click.group()
def cli():
    pass

@cli.command()
@click.option('--base', required=True, type=str, help='Image that will hide another image')
@click.option('--secret', required=True, type=str, help='Image that will be hidden')
@click.option('--output', required=False, type=str, help='Output image')
def hide(base, secret, output):
    if output is None:
        from pathlib import Path
        p = Path(secret)
        bn = p.stem
        output = '{}_hidden.png'.format(bn)
        if Path(output).exists():
            import datetime
            now = datetime.datetime.now()
            output = '{}_hidden_{}.png'.format(bn, now.strftime('%Y-%M-%d-%H-%M-%S'))
    
    base_image, secret_image = Image.open(base), Image.open(secret)
    available_hidden_size = base_image.width * base_image.height * 3
    lossless_data_size = secret_image.width * secret_image.height * 3 * 2 + 9
    lossy_data_size = secret_image.width * secret_image.height * 3 + 9
    if lossy_data_size > available_hidden_size:
        raise ValueError('Base image is not big enough to hide even when using lossy')
    
    lossy = lossless_data_size > available_hidden_size
    print('Method {} due to size'.format('lossy' if lossy else 'lossless'))
    
    
    print('Using n = {} with method {} - filling with noise'.format(4, 'lossy' if lossy else 'lossless'))
    merged_image = merge_with_dims(base_image, secret_image, lossy=lossy, add_noise=True, engrave_method=True)
    merged_image.save(output)

@cli.command()
@click.option('--base', required=True, type=str, help='Image containing secret')
@click.option('--output', required=False, type=str, help='Output image')
def reveal(base, output):
    # TODO: Create output file name is not provided
    unmerged_image = unmerge_with_dims(Image.open(base), lossy=None, read_method=True)
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
