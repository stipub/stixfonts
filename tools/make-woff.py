import sys
from argparse import ArgumentParser
from fontTools.ttLib import TTFont

def main(args=None):
    parser = ArgumentParser(description="Pre-process UFO files")
    parser.add_argument("input")
    parser.add_argument("flavor")
    parser.add_argument("output")

    options = parser.parse_args(args)

    font = TTFont(options.input)
    font.flavor = options.flavor
    font.save(options.output)


if __name__ == "__main__":
    main()
