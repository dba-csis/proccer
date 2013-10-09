import sys


def allocate(bytes):
    some_str = ' ' * bytes
    del some_str

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write('Usage: {0} <size_bytes>\n'.format(sys.argv[0]))
        sys.exit(1)

    try:
        value = int(sys.argv[1])
        allocate(value)

    except ValueError:
        sys.stderr.write('{0}: invalid number: {1}\n'.format(sys.argv[0],
                                                             sys.argv[1]))
        sys.exit(2)

    except MemoryError:
        sys.stderr.write('Memory Error\n')
        sys.exit(50)
