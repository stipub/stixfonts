import sys

from fontTools.ttLib import TTFont
from fontTools.otlLib.maxContextCalc import maxCtxFont


def main():
    font = TTFont(sys.argv[1])

    name = font["name"]
    family = name.getName(1, 3, 1)
    if str(family).endswith(" Italic"):
        family.string = str(family).replace(" Italic", "")
        name.setName("Italic", 2, family.platformID, family.platEncID, family.langID)

    font["OS/2"].usMaxContext = maxCtxFont(font)
    font.save(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
