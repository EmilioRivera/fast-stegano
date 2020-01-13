import numpy as np


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
