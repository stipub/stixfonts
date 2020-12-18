import sys

from fontTools.otlLib.builder import buildStatTable
from fontTools.otlLib.maxContextCalc import maxCtxFont
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import ttProgram


def main():
    font = TTFont(sys.argv[1])

    # Drop VOLT table
    if "TSIV" in font:
        del font["TSIV"]

    # Add STAT table
    os2 = font["OS/2"]
    italic = bool(os2.fsSelection & (1 << 0))

    fvar = font["fvar"]
    axes = [dict(tag=a.axisTag, name=a.axisNameID) for a in fvar.axes]

    if italic:
        value = dict(value=italic, name="Italic")
    else:
        value = dict(value=italic, name="Normal", flags=0x0002, linkedValue=1)
    axes.append(dict(tag="ital", name="Italic", values=[value]))

    buildStatTable(font, axes)

    # Prune name table
    names = [n for n in font["name"].names if n.platformID == 3]

    # Drop Regular from Roman font names
    if not italic:
        for name in names:
            if name.nameID in (3, 6):
                name.string = str(name).replace("-Regular", "")
            if name.nameID == 4:
                name.string = str(name).replace(" Regular", "")

    font["name"].names = names
    font["OS/2"].usMaxContext = maxCtxFont(font)

    font["DSIG"] = DSIG = newTable("DSIG")
    DSIG.ulVersion = 1
    DSIG.usFlag = 0
    DSIG.usNumSigs = 0
    DSIG.signatureRecords = []

    if "glyf" in font and "prep" not in font:
        # Google Fonts “smart dropout control”
        font["prep"] = prep = newTable("prep")
        prep.program = ttProgram.Program()
        prep.program.fromAssembly(
            ["PUSHW[]", "511", "SCANCTRL[]", "PUSHB[]", "4", "SCANTYPE[]"]
        )

    if "MVAR" in font:
        del font["MVAR"]

    font.save(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
