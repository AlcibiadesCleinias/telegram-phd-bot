def batch(iterable, size=100):
    iterable_len = len(iterable)
    for ndx in range(0, iterable_len, size):
        yield iterable[ndx:min(ndx + size, iterable_len)]
