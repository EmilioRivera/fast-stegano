from PIL import Image
import numpy as np
import io

from linear_utils import np8_to_number_16, len_to_np8_16, np8_to_number_32, len_to_np8_32

# TODO: Better method encoding scheme
METHOD_LOSSLESS = 0x01
METHOD_LOSSY    = 0x02

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(funcName)18s: %(message)s',
)

class EncodingMethod(object):
    value = None
    @staticmethod
    def can_fit(base, secret):
        pass
    @staticmethod
    def available_hidden_size(base):
        return base.width * base.height * 3
    @staticmethod
    def needed_hidden_size(secret):
        raise NotImplementedError('Not for the base class')
    @staticmethod
    def hide(base, secret, add_noise, engrave_method):
        raise NotImplementedError('Not for the base class')
    @staticmethod
    def reveal(base):
        raise NotImplementedError('Not for the base class')


class LosslessEncoding(EncodingMethod):
    value = METHOD_LOSSLESS
    header_size = 9
    @staticmethod
    def can_fit(base, secret):
        b_w, b_h = base.size
        s_w, s_h = secret.size
        available_size = LosslessEncoding.available_hidden_size(base)
        needed_size = LosslessEncoding.needed_hidden_size(secret)
        return needed_size <= available_size
    @staticmethod
    def needed_hidden_size(secret):
        return secret.width * secret.height * 3 * 2 + LosslessEncoding.header_size
    
    @staticmethod
    def _construct_lossless_with_dims(a, b, add_noise=False):
        # 32 bits are needed to encode the length
        # Using n = 4 for the LSB, we need 8 entries to encode the length of the message.
        # We will occupy 9 entries, the last one being unused. Just to get a total of 3 pixels
        LosslessEncoding.header_size = 9
        # We need to encode each pixel into the 4 LSB, resulting in twice the size
        # assert base.width * base.height > secret.width * secret.height * 2
        # TODO: Remove and change for own can_fit method
        assert a.size >= LosslessEncoding.header_size + b.size * 2

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
        offset = LosslessEncoding.header_size
        start, end = offset, offset + b.size * 2
        # When raveled, they will be consecutive, i.e all red data, then all green data, then all blue data
        stacked_arr = np.stack([red_noise, green_noise, blue_noise])
        hidden_noise[offset:end] = stacked_arr.ravel('C')
        
        if add_noise:
            hidden_noise[end:] = np.random.randint(low=0x00, high=0x0F, size=a.size-end, dtype=np.uint8)

        fake = fake.ravel('C') + hidden_noise
        return fake.reshape(a.shape)
    
    @staticmethod
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
    @staticmethod
    def hide(base, secret, add_noise, engrave_method):
        assert LosslessEncoding.can_fit(base, secret)
        a = np.asarray(base)
        b = np.asarray(secret)
        fake_data = LosslessEncoding._construct_lossless_with_dims(a, b, add_noise)
        if engrave_method:
            fake_data.ravel('C')[8] = LosslessEncoding.value
        return Image.fromarray(fake_data)
    @staticmethod
    def reveal(base):
        c = np.asarray(base)
        w, h, f = LosslessEncoding._reconstruct_lossless_with_dims(c)
        i = Image.fromarray(f, mode='RGB')
        return i

class LossyEncoding(EncodingMethod):
    value = METHOD_LOSSY
    header_size = 9
    @staticmethod
    def can_fit(base, secret):
        b_w, b_h = base.size
        s_w, s_h = secret.size
        available_size = LossyEncoding.available_hidden_size(base)
        needed_size = LossyEncoding.needed_hidden_size(secret)
        print(available_size, needed_size)
        return needed_size <= available_size
    @staticmethod
    def needed_hidden_size(secret):
        return secret.width * secret.height * 3 + LossyEncoding.header_size

    @staticmethod
    def _construct_loss_with_dims(a, b, add_noise):
        # 32 bits are needed to encode the length
        # Using n = 4 for the LSB, we need 8 entries to encode the length of the message.
        # We will occupy 9 entries, the last one being unused. Just to get a total of 3 pixels
        offset = LossyEncoding.header_size

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

    @staticmethod
    def _reconstruct_loss_with_dims(a):
        # Get the dimensions
        flat = (a.ravel() & 0x0F)
        width, height = np8_to_number_16(flat[:4]), np8_to_number_16(flat[4:8])
        n_elems = width * height * 3
        start, end = 9, 9 + n_elems
        rr, rg, rb  = flat[start:end:3] << 4, flat[start+1:end+1:3] << 4, flat[start+2:end+2:3] << 4
        packed = np.stack([rr, rg, rb], axis=-1)
        return width, height, packed.reshape(width, height, 3)
    
    @staticmethod
    def hide(base, secret, add_noise, engrave_method):
        assert LossyEncoding.can_fit(base, secret)
        a = np.asarray(base)
        b = np.asarray(secret)
        fake_data = LossyEncoding._construct_loss_with_dims(a, b, add_noise)
        if engrave_method:
            fake_data.ravel('C')[8] = LossyEncoding.value
        return Image.fromarray(fake_data)
    
    @staticmethod
    def reveal(base):
        c = np.asarray(base)
        w, h, f = LossyEncoding._reconstruct_loss_with_dims(c)
        i = Image.fromarray(f, mode='RGB')
        return i

class JpegEncodingMethod(EncodingMethod):
    value = 0x03
    header_size = 9
    @staticmethod
    def can_fit(base, secret):
        b_w, b_h = base.size
        available_size = LosslessEncoding.available_hidden_size(base)
        needed_size = LosslessEncoding.needed_hidden_size(secret)
        return needed_size <= available_size
    @staticmethod
    def needed_hidden_size(secret):
        b = io.BytesIO()
        secret.save(ba, format='jpeg')
        memview = ba.getbuffer()
        return len(memview)
    @staticmethod
    def hide(base, secret, add_noise, engrave_method):
        ba = io.BytesIO()
        secret.save(ba, format='jpeg')
        memview = ba.getbuffer()
        z = np.frombuffer(memview, dtype=np.uint8)
        
        a = np.asarray(base)
        b = np.asarray(secret)
        # 32 bits are needed to encode the length
        # Using n = 4 for the LSB, we need 8 entries to encode the length of the message.
        # We will occupy 9 entries, the last one being unused. Just to get a total of 3 pixels
        offset = JpegEncodingMethod.header_size
        tot_size = len(memview)
        hidden_noise = np.zeros(a.size, dtype=np.uint8)
        fake = a.copy('C')
        print(len(memview), len(z), tot_size, tot_size * 2)
        
        
        # The 8 first value will be the length of the message, the additional 9th value is not used
        # width_np, height_np = len_to_np8_16(b.shape[0]), len_to_np8_16(b.shape[1])
        hidden_noise[:8] = len_to_np8_32(tot_size * 2)
        # Put the hidden image data in target
        start, end = offset, offset + tot_size * 2
        hidden_noise[offset:end:2] = (z & 0xF0) >> 4
        hidden_noise[offset+1:end+1:2] = z & 0x0F

        if add_noise:
            hidden_noise[end:] = np.random.randint(low=0x00, high=0x0F, size=a.size-end, dtype=np.uint8)
        
        # Discard the LSB from the fake up until the last fake data
        fake[:end] = fake[:end] & 0xF0
        fake = fake.ravel('C') + hidden_noise
        if engrave_method:
            fake[8] = JpegEncodingMethod.value
        fake_image = Image.fromarray(fake.reshape(a.shape))

        return fake_image
    @staticmethod
    def reveal(base):
        c = np.asarray(base)
        flat = c.ravel('C') & 0x0F
        to_read = np8_to_number_32(flat[:8])

        start, end = JpegEncodingMethod.header_size, JpegEncodingMethod.header_size + to_read
        _msb = flat[start:end:2] << 4
        _lsb = np.zeros_like(_msb, dtype=np.uint8)
        _lsb[:end-start] = flat[start+1:end+1:2]
        _f = _msb + _lsb
        v = io.BytesIO(_f.tobytes())
        image = Image.open(v)
        return image
        raise NotImplementedError('Not for the base class')

MODES = [ LosslessEncoding, LossyEncoding, JpegEncodingMethod ]

def compute_method_used(image):
    _arr = np.asarray(image, dtype=np.uint8)
    method_value = _arr.ravel('C')[8] & 0x0F
    del _arr
    method = next((m for m in MODES if m.value == method_value), None)
    return method
