import sys

from fontTools.otlLib.builder import buildStatTable
from fontTools.otlLib.maxContextCalc import maxCtxFont
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import ttProgram


WEIGHT_MAP = {
    100: "Thin",
    200: "ExtraLight",
    300: "Light",
    400: "Regular",
    500: "Medium",
    600: "SemiBold",
    700: "Bold",
    800: "ExtraBold",
    900: "Black",
}


def axisValue(instance, axis, italic):
    weight = instance.coordinates[axis.axisTag]
    name = WEIGHT_MAP[weight]
    flags = 0x0002 if italic and name == "Regular" else 0x0
    return dict(value=weight, name=name, flags=flags)


def main():
    font = TTFont(sys.argv[1])

    # Drop VOLT table
    if "TSIV" in font:
        del font["TSIV"]

    # Add STAT table
    os2 = font["OS/2"]
    italic = bool(os2.fsSelection & (1 << 0))

    fvar = font["fvar"]
    axes = [
        dict(
            tag=a.axisTag,
            name=a.axisNameID,
            values=[axisValue(i, a, italic) for i in fvar.instances],
        )
        for a in fvar.axes
    ]

    if italic:
        value = dict(value=italic, name="Italic")
    else:
        value = dict(value=italic, name="Roman", flags=0x0002, linkedValue=1)
    axes.append(dict(tag="ital", name="Italic", values=[value]))

    buildStatTable(font, axes)

    # Drop Regular from Roman font names
    for name in font["name"].names:
        if name.platformID != 3:
            continue
        if not italic:
            if name.nameID in (3, 6):
                name.string = str(name).replace("-Regular", "")
            if name.nameID == 4:
                name.string = str(name).replace(" Regular", "")
        # Adobe bug
        if name.nameID == 1:
            psPrefix = str(name).replace(" ", "")
            if italic:
                psPrefix += "Italic"
            else:
                psPrefix += "Roman"
            font["name"].setName(psPrefix, 25, 3, 1, 0x409)

    # Prune name table
    font["name"].names = [n for n in font["name"].names if n.platformID == 3]

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
