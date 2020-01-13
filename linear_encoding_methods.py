# TODO: Better method encoding scheme
METHOD_LOSSLESS = 0x01
METHOD_LOSSY    = 0x02


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

MODES = [ LosslessEncoding, LossyEncoding ]
