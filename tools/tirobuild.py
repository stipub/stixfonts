import logging
from copy import deepcopy
from enum import Enum
from pathlib import Path

import yaml

logger = logging.getLogger("builder")

PSNAMES_KEY = "public.postscriptNames"


class TemporaryLogLevel:
    def __init__(self, level):
        self.level = level
        self.logger = logging.getLogger()

    def __enter__(self):
        self.old = self.logger.level
        self.logger.setLevel(self.level)

    def __exit__(self, kind, value, tb):
        self.logger.setLevel(self.old)


class SaveState:
    def __init__(self, font):
        self.font = font

    def __enter__(self):
        self.name = self.font.name
        self.fmt = self.font.fmt
        self.variable = self.font.variable
        self.names = self.font.names
        self.instances = self.font.instances
        self.STAT = self.font.STAT
        self.meta = self.font.meta

    def __exit__(self, kind, value, tb):
        self.font.name = self.name
        self.font.fmt = self.fmt
        self.font.variable = self.variable
        self.font.names = self.names
        self.font.instances = self.instances
        self.font.STAT = self.STAT
        self.font.meta = self.meta


class Format(Enum):
    TTF = "ttf"
    OTF = "otf"
    WOFF = "woff"
    WOFF2 = "woff2"


def getName(font, nameID):
    name = font["name"].getName(nameID, platformID=3, platEncID=1, langID=0x409)
    if name:
        return str(name)
    return None


def setName(font, nameID, string):
    font["name"].setName(string, nameID, platformID=3, platEncID=1, langID=0x409)


def instanceMatch(key, instance, font):
    psname = getName(font, instance.postscriptNameID)
    if key == psname:
        return True
    subfamily = getName(font, instance.subfamilyNameID)
    if key == subfamily:
        return True
    if "-" in key:
        part = key.split("-", 1)[1]
        if subfamily == part:
            return True
        if subfamily.replace(" ", "") == part:
            return True
    return False


def instanceName(name, instance, font):
    psname = getName(font, instance.postscriptNameID)
    if psname:
        return psname

    subfamily = getName(font, instance.subfamilyNameID)
    return name.split("-")[0] + "-" + subfamily


def mergeConfigs(first, second, skip=None):
    conf = {**first}
    for key in second:
        if skip and key in skip:
            continue
        if key not in conf:
            conf[key] = second[key]
        elif isinstance(second[key], dict):
            # We want to merge dictionaries from the two configurations, so
            # that, say, names can be set in the second and over-ridden by
            # the font’s conf.
            conf[key] = {**second[key], **conf[key]}
    return conf


def splitfearureparamtag(tag):
    script = None
    langsys = None
    if "." in tag:
        tag, script = tag.split(".", 1)
        if "." in script:
            script, langsys = script.split(".", 1)
            langsys = langsys.ljust(4, " ")
        script = script.ljust(4, " ")
    return tag, script, langsys


def validatefeatureparamtag(tag):
    if tag.count(".") > 2:
        return False

    tag, _, _ = splitfearureparamtag(tag)
    if not tag[2:].isnumeric():
        return False

    num = int(tag[2:])
    if tag.startswith("ss") and num in range(1, 21):
        return True
    elif tag.startswith("cv") and num in range(1, 100):
        return True
    return False


def collectfeatures(table, tag):
    tag, script, langsys = splitfearureparamtag(tag)
    features = []
    if script:
        for srec in table.ScriptList.ScriptRecord:
            indices = []
            if srec.ScriptTag == script:
                if langsys == "dflt":
                    indices += srec.Script.DefaultLangSys.FeatureIndex
                    indices.append(srec.Script.DefaultLangSys.ReqFeatureIndex)
                elif langsys:
                    for lrec in srec.Script.LangSysRecord:
                        if lrec.LangSysTag == langsys:
                            indices += lrec.LangSys.FeatureIndex
                            indices.append(lrec.LangSys.ReqFeatureIndex)
                else:
                    indices += srec.Script.DefaultLangSys.FeatureIndex
                    indices.append(srec.Script.DefaultLangSys.ReqFeatureIndex)
                    for lrec in srec.Script.LangSysRecord:
                        indices += lrec.LangSys.FeatureIndex
                        indices.append(lrec.LangSys.ReqFeatureIndex)
            for i in indices:
                if i == 0xFFFF:
                    continue
                features.append(table.FeatureList.FeatureRecord[i])
    else:
        features = table.FeatureList.FeatureRecord

    return [f.Feature for f in features if f.FeatureTag == tag]


def run_tx(otf, options, outTag=None):
    import cffsubr
    import subprocess
    import tempfile
    import os
    from io import BytesIO
    from fontTools.ttLib import newTable

    if "CFF " in otf:
        tag = "CFF "
    elif "CFF2" in otf:
        tag = "CFF2"
    else:
        raise RuntimeError(f"Can’t run tx on {otf}")

    if outTag is None:
        outTag = tag

    buf = BytesIO()
    otf.save(buf)
    input_data = buf.getvalue()

    with tempfile.NamedTemporaryFile(prefix="tx-", delete=False) as in_temp:
        in_temp.write(input_data)

    with tempfile.NamedTemporaryFile(prefix="tx-", delete=False) as out_temp:
        out_temp.write(b"")

    args = [
        f"-{outTag.rstrip().lower()}",
        "+b",
        *options,
        "-o",
        out_temp.name,
        in_temp.name,
    ]
    kwargs = dict(check=True, stderr=subprocess.PIPE)

    try:
        cffsubr._run_embedded_tx(*args, **kwargs)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e.stderr.decode())
    else:
        with open(out_temp.name, "rb") as fp:
            output_data = fp.read()
    finally:
        os.remove(in_temp.name)
        os.remove(out_temp.name)

    cff = newTable(outTag)
    cff.decompile(output_data, otf)

    del otf[tag]
    otf[outTag] = cff

    return otf


def instantiateCFF2(otf, coordinates):
    from fontTools.varLib.mutator import interpolate_cff2_metrics
    from fontTools.misc.fixedTools import floatToFixedToFloat
    from fontTools.varLib.models import normalizeLocation, piecewiseLinearMap

    # instantiate the CFF2 table using tx, since FontTools.varLib mutator
    # produces broken glyphs.
    coords = ",".join(str(v) for v in coordinates.values())
    otf = run_tx(otf, ["+V", "-U", coords], "CFF ")

    # But tx doesn’t interpolate metrics, so we do it here.
    topDict = otf["CFF "].cff.topDictIndex[0]

    # Some odd rounding happens to TopDict version, so reset it.
    topDict.version = f"{otf["head"].fontRevision}"

    glyphOrder = otf.getGlyphOrder()
    fvarAxes = otf["fvar"].axes
    axes = {a.axisTag: (a.minValue, a.defaultValue, a.maxValue) for a in fvarAxes}
    loc = normalizeLocation(coordinates, axes)
    if "avar" in otf:
        maps = otf["avar"].segments
        loc = {k: piecewiseLinearMap(v, maps[k]) for k, v in loc.items()}
    # Quantize to F2Dot14, to avoid surprise interpolations.
    loc = {k: floatToFixedToFloat(v, 14) for k, v in loc.items()}
    interpolate_cff2_metrics(otf, topDict, glyphOrder, loc)

    # Set post table version to 3.0.
    otf["post"].formatType = 3.0

    return otf


class Font:
    def __init__(self, name, conf, project):
        self.name = name

        # Merge keys from the top level (project) configuration into the
        # current font’s conf.
        conf = mergeConfigs(conf, project, skip=["fonts"])

        self.source = conf.get("source")
        self.ren = conf.get("glyphnames")
        self.ttf = conf.get("ttf", {})

        path = conf["path"]
        self.output = path.parent / "output" / path.stem

        if self.source is None:
            raise RuntimeError(f"Can’t build {self.name} without a source")

        self.source = path.parent / self.source
        self.ren = path.parent / self.ren if self.ren else None

        self.variable = self.source.suffix == ".designspace"
        self.suffix = conf.get("vf-suffix")

        if "source" in self.ttf:
            if self.variable:
                if not isinstance(self.ttf["source"], list):
                    raise RuntimeError("TTF source must be a list for variable fonts")
                self.ttf["source"] = [path.parent / p for p in self.ttf["source"]]
            else:
                if isinstance(self.ttf["source"], list):
                    raise RuntimeError("TTF source must not be a list for static fonts")
                self.ttf["source"] = path.parent / self.ttf["source"]

        self.subsets = {}
        for name, subset in conf.get("subsets", {}).items():
            if "glyphlist" not in subset:
                raise RuntimeError(f"Subset “{name}” did not provide a glyph list")
            glyphlist, tags = self._parsesubset(path.parent / subset["glyphlist"])
            subset["glyphlist"] = glyphlist
            subset["langsys"] = tags
            if "cmapoverride" in subset:
                subset["cmapoverride"] = self._parsecmapoverride(
                    path.parent / subset["cmapoverride"]
                )
            self.subsets[name] = mergeConfigs(subset, conf, skip=["instances"])

        self.names = conf.get("names", {})
        self.set = conf.get("set", {})

        self.DSIG = conf.get("DSIG")
        if "DSIG" in conf and self.DSIG != "dummy":
            raise RuntimeError(f"Only support “DSIG” value is “dummy”: “{self.DSIG}”")

        self.components = conf.get("components", {})

        self.meta = conf.get("meta", [])

        self.formats = [Format(f) for f in conf.get("formats", list(Format))]
        self.fmt = None

        self.instances = conf.get("instances")
        if self.instances is not None:
            if self.instances == "all":
                self.instances = {}
            if not isinstance(self.instances, dict):
                raise RuntimeError(f"Unsupported “instances” value: “{self.instances}”")

        self.STAT = conf.get("STAT")
        if self.STAT:
            if "axes" not in self.STAT:
                raise RuntimeError("“STAT” table must have “axes”")

        self.featureparams = conf.get("featureparams", {})
        if not isinstance(self.featureparams, dict):
            raise RuntimeError("“featureparams” must be a dictionary")
        for tag, params in self.featureparams.items():
            if not validatefeatureparamtag(tag):
                raise RuntimeError(
                    f"Invalid or unsupported feature tag for “featureparams”: {tag}"
                )

            if tag.startswith("ss"):
                if not isinstance(params, str):
                    raise RuntimeError(
                        "“featureparams” of stylistic set must be a string"
                    )
            elif tag.startswith("cv"):
                if not isinstance(params, dict):
                    raise RuntimeError(
                        "“featureparams” of character variant must be a dictionary"
                    )

        self.autohinting = conf.get("autohinting", {})
        self.gasp = conf.get("gasp", {})

    @property
    def ext(self):
        return self.fmt.value

    @property
    def filename(self):
        return self.name + "." + self.ext

    def _parsesubset(self, path):
        with open(path) as f:
            lines = f.read().split("\n")

        glyphlist = set()
        tags = set()
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("#"):
                if i == 0:
                    _, tags = line.split("#", 1)
                    tags = {t.strip() for t in tags.split(",")}
            else:
                glyphlist.add(line)

        return (glyphlist, tags if tags else ["*"])

    def _parsecmapoverride(self, path):
        with open(path) as f:
            lines = f.read().split("\n")

        override = {}
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                code, glyphname = line.split()
                code = int(code, 16)
                if code in override:
                    raise ValueError(f"Duplicate mapping for “{code:04X}” in: {path}")
                override[code] = glyphname

        return override

    def _openufo(self, path, dspath=None):
        from ufoLib2 import Font as UFOFont

        if not path.exists() and dspath is not None:
            path = dspath.parent / path.name

        ufo = UFOFont.open(path, validate=False)

        if self.ren is not None:
            with open(self.ren, "r") as f:
                logger.info(f"Setting {path.name} final glyph names")
                lines = f.read().split("\n")
                lines = [
                    line.split() for line in lines if line and not line.startswith("%")
                ]
                ufo.lib[PSNAMES_KEY] = {line[0]: line[1] for line in lines}

        if "fstype" in self.set:
            ufo.info.openTypeOS2Type = self.set["fstype"]

        if self.gasp:
            records = []
            for range in self.gasp:
                records.append(
                    {
                        "rangeMaxPPEM": range["maxPPEM"],
                        "rangeGaspBehavior": range["behavior"],
                    }
                )
            ufo.info.openTypeGaspRangeRecords = records

        return ufo

    def _setfeatureparams(self, otf):
        if not self.featureparams:
            return

        from fontTools.ttLib.tables import otTables

        logger.info(f"Adding “featureParams” to {self.filename}")
        name = otf["name"]

        def addName(string):
            if not string:
                return 0
            if isinstance(string, str):
                return name.addMultilingualName({"en": string}, mac=False)
            elif isinstance(string, list):
                nameid = name.addMultilingualName({"en": string[0]}, mac=False)
                for s in string[1:]:
                    name.addMultilingualName({"en": s}, mac=False)
                return nameid

        for tag in ("GSUB", "GPOS"):
            if tag not in otf:
                continue
            table = otf[tag].table

            for tag, conf in self.featureparams.items():
                features = collectfeatures(table, tag)
                for feature in features:
                    if feature.FeatureParams:
                        raise RuntimeError(
                            f"Feature “{tag}” already has “featureparams”"
                        )
                    if tag.startswith("ss"):
                        params = otTables.FeatureParamsStylisticSet()
                        params.Version = 0
                        params.UINameID = addName(conf)
                    elif tag.startswith("cv"):
                        label = conf.get("label")
                        tooltip = conf.get("tooltip")
                        sampletext = conf.get("sampletext")
                        paramlabels = conf.get("paramlabels", [])
                        characters = conf.get("characters", [])
                        if isinstance(characters, str):
                            characters = [ord(c) for c in characters]
                        else:
                            characters = [
                                ord(c) if isinstance(c, str) else c for c in characters
                            ]

                        params = otTables.FeatureParamsCharacterVariants()
                        params.Format = 0
                        params.FeatUILabelNameID = addName(label)
                        params.FeatUITooltipTextNameID = addName(tooltip)
                        params.SampleTextNameID = addName(sampletext)
                        params.NumNamedParameters = len(paramlabels)
                        params.FirstParamUILabelNameID = addName(paramlabels)
                        params.Character = characters
                        params.CharCount = len(characters)
                    feature.FeatureParams = params

    def _setstat(self, font):
        if self.STAT:
            from fontTools.otlLib.builder import buildStatTable

            logger.info(f"Adding “STAT” table to {self.filename}")
            buildStatTable(
                font,
                axes=self.STAT["axes"],
                locations=self.STAT.get("locations"),
                elidedFallbackName=self.STAT.get("elidedFallbackName", 2),
            )
        elif self.variable:
            from axisregistry import build_stat

            logger.info(f"Adding default “STAT” table to {self.filename}")
            build_stat(font)

    def _copytables(self, otf, otl):
        from fontTools.otlLib.maxContextCalc import maxCtxFont

        otl.setGlyphOrder(otf.getGlyphOrder())
        for tag in self.ttf.get("tables", []):
            logger.info(f"Copying “{tag}” table to {self.filename}")
            otf[tag] = deepcopy(otl[tag])
        otf["OS/2"].usMaxContext = maxCtxFont(otf)

        return otf

    def _setmeta(self, otf):
        if self.meta:
            from fontTools.ttLib import newTable

            logger.info(f"Adding “meta” table to {self.filename}")
            otf["meta"] = meta = newTable("meta")
            meta.data = {t: ",".join(v) for t, v in self.meta.items()}

    def _postprocess(self, otf):
        if self.DSIG:
            from fontTools.ttLib import newTable

            logger.info(f"Adding “DSIG” table to {self.filename}")
            otf["DSIG"] = DSIG = newTable("DSIG")
            DSIG.ulVersion = 1
            DSIG.usFlag = 0
            DSIG.usNumSigs = 0
            DSIG.signatureRecords = []

        self._setmeta(otf)
        self._setstat(otf)

        return otf

    def _autohint(self, otf):
        if self.variable:
            return otf

        from fontTools.ttLib import TTFont

        if self.fmt == Format.TTF:
            conf = self.autohinting.get("ttfautohint", {})
            if conf.get("disable"):
                return otf

            logger.info(f"Autohinting {self.filename}")

            from io import BytesIO

            from ttfautohint import ttfautohint

            opts = {"no-info": True, **conf}
            opts = {k.replace("-", "_"): v for k, v in opts.items()}

            # Pop our own options or options controlling input/output.
            for key in {"disable", "in_buffer", "in_file", "out_file"}:
                opts.pop(key, None)

            buf = BytesIO()
            otf.save(buf)
            otf.close()
            data = ttfautohint(in_buffer=buf.getvalue(), **opts)
            otf = TTFont(BytesIO(data))

            # Set bit 3 on head.flags
            # https://font-bakery.readthedocs.io/en/latest/fontbakery/profiles/googlefonts.html#com.google.fonts/check/integer_ppem_if_hinted
            head = otf["head"]
            head.flags |= 1 << 3
        elif self.fmt == Format.OTF:
            conf = self.autohinting.get("psautohint", {})
            if conf.get("disable"):
                return otf

            logger.info(f"Autohinting {self.filename}")

            from tempfile import TemporaryDirectory

            from psautohint.__main__ import main as psautohint

            with TemporaryDirectory() as d:
                path = Path(d) / "tmp.otf"
                otf.save(path)
                with TemporaryLogLevel(logging.ERROR):
                    psautohint([str(path)])
                otf.close()
                otf = TTFont(path)
        return otf

    def _subset(self, otf):
        from fontTools.subset import Options, Subsetter

        for name, subset in self.subsets.items():
            with SaveState(self):
                self.name = name
                logger.info(f"Creating {self.filename} subset")
                new = deepcopy(otf)
                options = Options()
                options.name_legacy = True
                options.name_languages = ["*"]
                options.recommended_glyphs = True
                options.layout_features = ["*"]
                options.notdef_outline = True
                options.notdef_glyph = True
                options.glyph_names = True
                options.hinting = True
                options.legacy_kern = True
                options.symbol_cmap = True
                options.layout_closure = False
                options.prune_unicode_ranges = True
                options.prune_codepage_ranges = True
                options.passthrough_tables = False
                options.recalc_average_width = True
                options.ignore_missing_glyphs = True
                options.layout_scripts = subset["langsys"]

                options.drop_tables.remove("DSIG")
                options.no_subset_tables += ["DSIG", "meta"]

                options.name_IDs = [
                    n.nameID for n in otf["name"].names if n.nameID < 256
                ]

                subsetter = Subsetter(options=options)
                subsetter.populate(subset["glyphlist"])

                with TemporaryLogLevel(logging.WARNING):
                    subsetter.subset(new)

                self.names = subset.get("names", {})
                self.instances = subset.get("instances")
                self.meta = subset.get("meta")
                self._overridecmap(new, subset.get("cmapoverride"))
                new = self._optimize(new)
                self._setnames(new)
                self._setmeta(new)
                self._instanciate(new)
                self._addvfsuffix(new)
                self._buildwoff(new)
                self._save(new)

    def _removeoverlaps(self, otf):
        from fontTools.ttLib.removeOverlaps import removeOverlaps

        logger.info(f"Removing overlaps from {self.filename}")
        try:
            removeOverlaps(otf)
        except NotImplementedError:
            pass
        return otf

    def _instanciate(self, vf):
        if self.instances is None or not self.variable:
            return

        from io import BytesIO

        from fontTools.ttLib import TTFont
        from fontTools.varLib.instancer import setRibbiBits
        from fontTools.varLib.instancer.names import pruningUnusedNames, updateNameTable
        from fontTools.varLib.mutator import instantiateVariableFont

        logger.info(f"Instancing {self.filename} statics")
        instances = []
        if not self.instances:
            for instance in vf["fvar"].instances:
                name = instanceName(self.name, instance, vf)
                conf = {"name": name.replace(" ", "")}
                instances.append((instance.coordinates, conf))
        else:
            for key, conf in self.instances.items():
                conf = conf if isinstance(conf, dict) else {}
                conf["name"] = key
                if "coordinates" in conf:
                    instances.append((conf["coordinates"], conf))
                    continue
                for instance in vf["fvar"].instances:
                    if instanceMatch(key, instance, vf):
                        instances.append((instance.coordinates, conf))
                        break

        for coordinates, conf in instances:
            stream = BytesIO()
            vf.save(stream)
            stream.seek(0)
            otf = TTFont(stream)

            # Some odd rounding happens to fontRevision when loading from
            # binary again, so reset it.
            otf["head"].fontRevision = vf["head"].fontRevision

            # Remove Variations PS Name Prefix, and do so before updating the
            # name table so it does not leak into the instance PS name.
            otf["name"].removeNames(25)

            try:
                updateNameTable(otf, coordinates)
            except ValueError:
                pass

            with SaveState(self):
                self.name = conf["name"]
                logger.info(f"Instancing {self.filename}")
                self.variable = False
                self.STAT = None
                with pruningUnusedNames(otf):
                    if "CFF2" in otf:
                        otf = instantiateCFF2(otf, coordinates)
                    otf = instantiateVariableFont(otf, coordinates, inplace=True)
                setRibbiBits(otf)
                self.names = conf.get("names", {})
                drop_typo_names = (1 in self.names and 2 in self.names) or False
                otf = self._setnames(
                    otf, fix_psname=True, drop_typo_names=drop_typo_names
                )
                otf = self._postprocess(otf)
                otf = self._removeoverlaps(otf)
                otf = self._autohint(otf)
                otf = self._optimize(otf)
                self._save(otf)
                self._buildwoff(otf)

    def _setnames(self, font, fix_psname=False, drop_typo_names=False):
        font["name"].names = [n for n in font["name"].names if n.platformID == 3]
        if not self.names and not fix_psname:
            return font

        logger.info(f"Adding “name” entries to {self.filename}")

        # Make a copy as we might modify it.
        names = {**self.names}

        if 6 not in names and fix_psname:
            import re

            family = names.get(1, getName(font, 1))
            subfamily = names.get(2, getName(font, 2))
            names[6] = re.sub(r"[^A-Za-z0-9-]", r"", f"{family}-{subfamily}")

        if drop_typo_names:
            font["name"].removeNames(16)
            font["name"].removeNames(17)

        # If version or psname IDs are specified, but unique ID is not, update
        # the later.
        if (5 in names or 6 in names) and (3 not in names):
            version = names.get(5, getName(font, 5))
            psname = names.get(6, getName(font, 6))
            vendor = font["OS/2"].achVendID
            names[3] = f"{version.replace('Version ', '')}:{vendor}:{psname}"

        for nameID, string in names.items():
            setName(font, nameID, string)

        if 5 in names:
            import re

            m = re.match(r"Version (\d\.\d\d)", names[5])
            if m is None:
                raise ValueError(
                    "Can’t parse version string. "
                    f"“{names[5]}” is not a valid version string."
                )
            font["head"].fontRevision = float(m.group(1))

        if "CFF " in font and any(n in names for n in (0, 1, 4, 5, 6, 7)):
            cff = font["CFF "].cff
            cff.fontNames[0] = names.get(6, cff.fontNames[0])
            topDict = cff.topDictIndex[0]
            topDict.Copyright = names.get(0, topDict.Copyright)
            topDict.FamilyName = names.get(1, topDict.FamilyName)
            topDict.FullName = names.get(4, topDict.FullName)
            topDict.Notice = names.get(7, topDict.Notice)
            if 5 in names:
                topDict.version = f"{font['head'].fontRevision}"

        return font

    def _optimize(self, otf):
        if self.variable:
            return otf

        if "CFF " in otf:
            tag = "CFF "
        elif "CFF2" in otf:
            tag = "CFF2"
        else:
            return otf

        import cffsubr
        from fontTools.cffLib.specializer import specializeProgram

        logger.info(f"Optimizing {self.filename}")
        topDict = otf[tag].cff.topDictIndex[0]
        charStrings = topDict.CharStrings
        for charString in charStrings.values():
            charString.decompile()
            charString.program = specializeProgram(charString.program)

        logger.info(f"Subroutinizing {self.filename}")
        cffsubr.subroutinize(otf, keep_glyph_names=False, cff_version=1)

        return otf

    def _addvfsuffix(self, otf):
        names = {}

        if self.variable and self.suffix:
            family = None

            # Find the family name, we need it to know where to insert the
            # suffix in full names
            for record in otf["name"].names:
                if record.nameID == 16:
                    family = str(record)
                elif record.nameID == 1 and family is None:
                    family = str(record)

            for record in otf["name"].names:
                if record.nameID in [1, 16, 21]:
                    # Family names, append space then the suffix
                    names[record.nameID] = f"{str(record)} {self.suffix}"
                if record.nameID == 6:
                    # PostScript name, append suffix to family name
                    psfamily = family.replace(" ", "")
                    vfpsfamily = f"{psfamily}{self.suffix}"
                    names[record.nameID] = str(record).replace(psfamily, vfpsfamily)
                if record.nameID in [4, 18]:
                    # Full names, append space then the suffix to family name
                    vffamily = f"{family} {self.suffix}"
                    names[record.nameID] = str(record).replace(family, vffamily)

        with SaveState(self):
            self.names = names
            self._setnames(otf)

    def _overridecmap(self, otf, cmapoverride):
        if cmapoverride is None:
            return

        logger.info(f"Overriding “cmap” in {self.filename}")
        ga = otf.getGlyphOrder()
        cmap = otf["cmap"]
        for subtable in cmap.tables:
            if subtable.isUnicode():
                for code, glyphname in cmapoverride.items():
                    if glyphname not in ga:
                        raise ValueError(
                            f"Glyph “{glyphname}” used in “camp” override not in font"
                        )
                    subtable.cmap[code] = glyphname

    def _buildwoff(self, otf):
        for fmt in self.formats:
            if fmt not in (Format.WOFF, Format.WOFF2):
                continue
            new = deepcopy(otf)
            new.flavor = fmt.value
            self._save(new, fmt)

    def _save(self, otf, wfmt=None):
        import re

        fmt = self.fmt
        fmtdir = fmt.name
        if self.variable:
            fmtdir += "VF"
        if wfmt is not None:
            fmtdir += wfmt.name
            self.fmt = wfmt
        name = re.sub(r"\[.*?\]", "", self.name).split("-")[0]
        parent = self.output / name / fmtdir
        parent.mkdir(parents=True, exist_ok=True)
        path = parent / self.filename
        logger.info(f"Saving {path}")
        otf.save(path)
        self.fmt = fmt

    def build(self):
        logger.info(f"Building {self.name}")
        with SaveState(self):
            if self.variable:
                self._buildvariable()
            else:
                self._buildstatic()

    def _buildvariable(self):
        from fontTools.designspaceLib import DesignSpaceDocument
        from fontTools.varLib import build as buildvf
        from ufo2ft import (
            compileInterpolatableOTFsFromDS,
            compileInterpolatableTTFsFromDS,
        )

        ds = DesignSpaceDocument.fromfile(self.source)
        ds.loadSourceFonts(lambda p: self._openufo(Path(p), self.source))

        options = {"inplace": False}
        if {"GDEF", "GSUB", "GPOS"}.issubset(self.ttf.get("tables", {})):
            options["featureWriters"] = []

        for fmt in self.formats:
            self.fmt = fmt
            if fmt == Format.TTF:
                compileFont = compileInterpolatableTTFsFromDS
            elif fmt == Format.OTF:
                compileFont = compileInterpolatableOTFsFromDS
            else:
                continue

            otfds = compileFont(ds, **options)

            if "source" in self.ttf:
                from fontTools.ttLib import TTFont

                if len(otfds.sources) != len(self.ttf["source"]):
                    raise RuntimeError("TTF sources must equal DesignSpace sources")

                for i, source in enumerate(otfds.sources):
                    otl = TTFont(self.ttf["source"][i])
                    with SaveState(self):
                        self.name = Path(source.path).stem
                        source.font = self._copytables(source.font, otl)

            vf, _, _ = buildvf(otfds)

            vf = self._setnames(vf)
            vf = self._postprocess(vf)
            self._setfeatureparams(vf)
            self._subset(vf)
            self._instanciate(vf)
            self._addvfsuffix(vf)
            vf = self._optimize(vf)
            self._buildwoff(vf)
            self._save(vf)

    def _buildstatic(self):
        from ufo2ft import compileOTF, compileTTF

        ufo = self._openufo(self.source)

        for fmt in (Format.TTF, Format.OTF):
            self.fmt = fmt
            options = {}
            if fmt == Format.TTF:
                compileFont = compileTTF
            elif fmt == Format.OTF:
                compileFont = compileOTF
                options["optimizeCFF"] = False
            else:
                continue

            options["removeOverlaps"] = True
            options["overlapsBackend"] = "pathops"
            if {"GDEF", "GSUB", "GPOS"}.issubset(self.ttf.get("tables", {})):
                options["featureWriters"] = []

            otf = compileFont(
                ufo,
                **options,
            )

            if (
                fmt == Format.TTF
                and "decompose" in self.components
                and self.components["decompose"] == "overlapping"
            ):
                from fontTools.ttLib.removeOverlaps import removeTTGlyphOverlaps

                # Decompose composite glyphs with overlapping components, and
                # remove overelap. We already decomposed simple glyphs while
                # building the font, so we process only composite glyphs below.
                # The removeTTGlyphOverlaps function only decomposes composites
                # with overlapping components, so we don’t check for the
                # overlap ourselves.
                logger.info(f"Decomposing {self.name} overlapping components")
                glyf = otf["glyf"]
                hmtx = otf["hmtx"]
                glyphSet = otf.getGlyphSet()
                glyphOrder = otf.getGlyphOrder()
                for name in glyphOrder:
                    glyph = glyf[name]
                    if glyph.isComposite():
                        removeTTGlyphOverlaps(name, glyphSet, glyf, hmtx, False)

            if "source" in self.ttf:
                from fontTools.ttLib import TTFont

                otl = TTFont(self.ttf["source"])
                otf = self._copytables(otf, otl)

            otf = self._setnames(otf)
            otf = self._postprocess(otf)
            otf = self._autohint(otf)
            self._setfeatureparams(otf)
            self._subset(otf)
            otf = self._optimize(otf)
            self._buildwoff(otf)
            self._save(otf)


class Builder:
    def __init__(self, path):
        with open(path) as f:
            project = yaml.safe_load(f)
            project["path"] = path

        if project.get("fonts", None) is None:
            raise RuntimeError("Missing or empty top level “fonts:” key.")

        self.fonts = []
        for name, conf in project.get("fonts", {}).items():
            self.fonts.append(Font(name, conf, project))

        if not self.fonts:
            raise RuntimeError("There are no fonts in the project.")

    def build(self):
        for font in self.fonts:
            font.build()


class ColorLogFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\x1b[38;21m",
        logging.INFO: "\x1b[1;32m",
        logging.WARNING: "\x1b[33;21m",
        logging.ERROR: "\x1b[31;21m",
        logging.CRITICAL: "\x1b[31;1m",
    }
    RESET = "\x1b[0m"

    def format(self, record):
        color = self.COLORS[record.levelno]
        name = "[\x1b[33;21m%(name)s\x1b[0m]"
        fmt = f"{color}%(levelname)s{self.RESET}\t%(message)s {name}"
        return logging.Formatter(fmt).format(record)


def main(args=None):
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Build Tiro fonts.")
    parser.add_argument("project", metavar="PROJECT", help="Project file.", type=Path)
    parser.add_argument("-q", "--quite", action="store_true", help="Be quite")
    options = parser.parse_args(args)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(ColorLogFormatter())
    if options.quite:
        logging.basicConfig(level=logging.WARNING, handlers=[ch])
    else:
        logging.basicConfig(level=logging.INFO, handlers=[ch])

    builder = Builder(options.project)
    builder.build()


if __name__ == "__main__":
    import sys

    sys.exit(main())
