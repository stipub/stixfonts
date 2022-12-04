import sys

from fontTools.ttLib import TTFont, newTable
from fontTools.otlLib.maxContextCalc import maxCtxFont


def main():
    font = TTFont(sys.argv[1])

    name = font["name"]
    head = font["head"]
    OS_2 = font["OS/2"]
    family = name.getName(1, 3, 1)
    if str(family).endswith(" Italic"):
        family.string = str(family).replace(" Italic", "")
        name.setName("Italic", 2, family.platformID, family.platEncID, family.langID)

        # Set italic bits
        head.macStyle |= 1 << 1
        OS_2.fsSelection |= 1 << 0

        # Clear regular bit
        OS_2.fsSelection &= ~(1 << 6)

    # Force ppem to integer values, since the fonts are hinted.
    head.flags |= 1 << 3

    OS_2.usMaxContext = maxCtxFont(font)

    font["DSIG"] = DSIG = newTable("DSIG")
    DSIG.ulVersion = 1
    DSIG.usFlag = 0
    DSIG.usNumSigs = 0
    DSIG.signatureRecords = []

    font.save(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
