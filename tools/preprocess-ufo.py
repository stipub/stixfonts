import sys
from argparse import ArgumentParser
from ufoLib2 import Font
from fontTools.ttLib import TTFont
from fontTools.misc import xmlWriter
from io import BytesIO

PSNAMES_KEY = "public.postscriptNames"


def load_names(ren):
    names = {}
    with open(ren, "r") as fp:
        lines = [
            l.split() for l in fp.read().split("\n") if l and not l.startswith("%")
        ]
        names = {l[0]: l[1] for l in lines}

    return names


def add_otl(font, otf, tags):
    namemap = {v: k for k, v in font.lib[PSNAMES_KEY].items()}
    otf.setGlyphOrder([namemap.get(n, n) for n in otf.getGlyphOrder()])
    font.glyphOrder = otf.getGlyphOrder()
    for tag in tags:
        fp = BytesIO()

        writer = xmlWriter.XMLWriter(fp)
        writer.begintag("ttFont")
        writer.newline()
        writer.begintag(tag)
        writer.newline()
        table = otf[tag]
        table.toXML(writer, otf)
        writer.endtag(tag)
        writer.newline()
        writer.endtag("ttFont")
        writer.close()

        font.data[f"com.github.fonttools.ttx/{tag}.ttx"] = fp.getvalue()


def main(args=None):
    parser = ArgumentParser(description="Pre-process UFO files")
    parser.add_argument("input")
    parser.add_argument("ren")
    parser.add_argument("otl")
    parser.add_argument("output")

    options = parser.parse_args(args)

    font = Font.open(options.input, validate=False)
    font.features.text = ""
    font.kerning = {}
    font.groups = {}

    font.lib[PSNAMES_KEY] = load_names(options.ren)
    otf = TTFont(options.otl, lazy=True)
    tables = {"GDEF", "GSUB", "GPOS"}
    if "MATH" in otf:
        tables |= {"MATH", "cmap"}
    add_otl(font, otf, tables)

    font.save(options.output, validate=False, overwrite=True)


if __name__ == "__main__":
    main()
