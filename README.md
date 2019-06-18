# stixfonts
OpenType Unicode fonts for Scientific, Technical, and Mathematical texts

## Overview

* See https://www.stixfonts.org/ for background on the the STIX Fonts
  project.

* Download the [current version](zipfiles/STIXv2.0.2.zip) of the OTF,
  WOFF, and WOFF2 files in a zip archive.

* View [code charts](docs/charts) for the
  * [Math](docs/charts/StixTwoMath.pdf),
  * [Regular text](docs/charts/StixTwoRegular.pdf),
  * [Italic](docs/charts/StixTwoItalic.pdf),
  * [Bold](docs/charts/StixTwoBold.pdf), and
  * [Bold Italic](docs/charts/StixTwoBoldItalic.pdf)
  fonts.

### Type 1 fonts (STIX 2.0.0 only)

The STIX Two fonts are OpenType fonts and are meant to be used in that
format.  For the benefit of LaTeX users who are unable to use XeTeX or
luaTeX, we have also provided version 2.0.0 of the STIX fonts as a
[set of TFM files and Type 1 fonts](Type1).  These are also available
as a separate [zip file](zipfiles/STIXv2.0.0-type1.zip).

Note that **no further updates** are planned to the Type 1
distribution; future development efforts will focus on improving the
OpenType fonts.  Patches to the existing Type 1 distribution are
welcome and, pending review, will be incorporated into the
distribution.

## About the STIX fonts.

The Scientific and Technical Information eXchange (STIX) fonts are
intended to meet the demanding needs of authors, publishers, printers,
and others in the scientific, medical, and technical fields.  They
combine a comprehensive Unicode-based collection of mathematical
symbols and alphabets with a set of text faces suitable for
professional publishing.  They are available royalty-free under the
[SIL Open Font License](docs/STIX_2.0.2_license.pdf).

Version 2 of the STIX fonts, now known as “STIX Two”, is a thorough
revision of version 1 undertaken by the renowned type house [Tiro
Typeworks](https://tiro.com).  The STIX Two fonts consist of four text
fonts (Regular, Italic, Bold, and Bold Italic) and one Math font.
Together, they provide a uniform set of fonts that can be used
throughout the production process, whether that be a traditional
print-only process, an entirely electronic one, or a combination of
the two.

The [STIX project](https://www.stixfonts.org/) began through the joint
efforts of
the [American Mathematical Society](https://www.ams.org/) (AMS),
the [American Institute of Physics](https://www.aip.org/) (AIP),
the [American Physical Society](https://www.aps.org/) (APS),
the [American Chemical Society](https://www.acs.org/) (ACS),
the [Institute of Electrical and Electronic](https://www.ieee.org/) Engineers (IEEE),
and [Elsevier](https://www.elsevier.com/).
These companies are collectively known as the STI Pub companies.

### A Fresh Take on Times Roman

The original version of STIX was based on Times Roman, which has now
been updated for the digital age.

As is well known, Times Roman was originally intended for printing the
*London Times*.  What is not generally appreciated is that the
production quality of the *Times* was atypically high: It was printed
on unusually high-quality paper on presses that operated more slowly
than most newspaper presses.  This allowed for the design of a
typeface that could exploit this level of care: serifs could be much
finer and counters (enclosed areas such as that in the lowercase *e*)
could be much smaller than in other newspaper typefaces.  These
features of the font have not always fared well in less exacting
environments.  At the same time, a notable quirk of the Times Roman
family is that the bold font is, in many respects, strikingly
dissimilar to the roman font.

Tiro Typeworks explain their approach to updating the Times Roman
basis of STIX as follows:

> “Our principal goal in approaching STIX Two was to address several
> inherent deficiencies in the Times New Roman model as well as expand
> the typographic features. This process necessarily involved
> diverging somewhat from Times as familiar to people who have only
> known the common digital versions, while simultaneously restoring to
> that typeface aspects of the size-appropriate design characteristics
> that made it so successful in newspaper, book, and journal
> publishing in it’s metal type incarnation. The essential
> ‘Times-ness’ remains, but are with greater harmonisation of style
> across the family.
> 
> “Most digital versions of Times have been based on an optical size
> model that appears too light and fine when scaled down to typical
> text sizes. In the design of STIX Two, we went back to specimens of
> size-specific designs from the metal era, and adapted proportions,
> weights, and spacing of the 10pt and 12pt designs. The oft-noted
> mismatch between the style of different weights of Times has been
> resolved with a new bold design that matches the construction of the
> regular weight.”

### Font implementation decisions

* The STIX fonts do not contain fixed-width or sans serif text faces.

* The sans serif, fraktur, script, etc., alphabets in Plane 1
  (U+1D400-U+1D4FF) are intended to be used only as technical symbols.

* These fonts are designed to support left-to-right typesetting in
  Latin-based scripts, with additional support for Greek and Cyrillic
  text.  Extensions to support other writing directions have been
  considered, but are currently deemed to be outside the scope of the
  STIX project.

### Note to TeX users

These fonts have been tested with both
[XeTeX](http://xetex.sourceforge.net/)
and
[luaTeX](http://www.luatex.org/)
with good results.  For best results, XeTeX users will want to use
version 0.99999 or later of XeTeX, which ships with
[TeXLive 2018](https://www.tug.org/texlive/).
This version fixes a number of bugs that were present in earlier
versions.  Our thanks go out to Jonathan Kew and Khaled Hosny for
their generous help in identifying and fixing these bugs.  LaTeX users
should also make sure they have the latest version of the
[amsmath package](https://ctan.org/pkg/amsmath).

## Summary of OpenType Features and Scripts

Further details these features can be found in the [font charts](docs/charts).

The four text fonts implement the following OpenType script tags:

    Regular   Bold      Italic    BoldItalic
    
    DFLT      DFLT      DFLT      DFLT          Default

    cyrl      cyrl      cyrl      cyrl          Cyrillic
                        cyrl.MKD  cyrl.MKD      Cyrillic/Macedonian
                        cyrl.SRB  cyrl.SRB      Cyrillic/Serbian

    grek      grek      grek      grek          Greek

    latn      latn      latn      latn          Latin
    latn.ROM  latn.ROM  latn.ROM  latn.ROM      Latin/Romanian        
    latn.TRK  latn.TRK  latn.TRK  latn.TRK      Latin/Turkish

and the following features

    c2sc    Small Capitals from Capitals
    case    Case-Sensitive Forms
    ccmp    Glyph Composition/Decomposition
    dnom    Denominators
    frac    Fractions
    kern    Kerning
    liga    Standard Ligatures -- latn only
    locl    Localized Forms    -- latn.ROM and Italic/BoldItalic cyrl.MKD only
    numr    Numerators
    onum    Oldstyle Figures
    pnum    Proportional Figures
    smcp    Small Capitals
    subs    Subscript
    sups    Superscript

All four text fonts also support the following Character Variants:

    cv01    U+019B Lambda with horizontal, not slanted stroke -- latn only
    cv02    U+0264 Rams horn with serifs -- latn only
    cv03    U+2423 OPEN BOX curved instead of straight

In addition, the Italic and BoldItalic faces support the following
Stylistic Variants:

    ss01    Replace two-story g by hooked g      -- Italic/BoldItalic only
    ss02    Upright parens, brackets, and braces -- Italic/BoldItalic only

STIX Two Math implements the following font features:

    ccmp    Glyph Composition/Decomposition
    dtls    Dotless forms of i and j
    flac    Flattened accents
    ssty    Math Script style alternates

and the following Character Variant (note the different meaning
compared to the text fonts):

    cv03    Replace U2205 EMPTY SET by an oblate form

and the following Stylistic Sets (again, note that ss01 and ss02 have
different meanings compared to the text fonts):

    ss01    Stylistic Set 1 -- Math chancery to roundhand (\mathcal -> \mathscr)
    ss02    Stylistic Set 2 -- Alternate italic forms: g, u, v, w, z
    ss03    Stylistic Set 3 -- Horizontal crossbar variants
    ss04    Stylistic Set 4 -- Minute, second and primes to long variants
    ss05    Stylistic Set 5 -- Short arrow variants
    ss06    Stylistic Set 6 -- Short/narrow variants
    ss07    Stylistic Set 7 -- Alternate math symbols (product, summation, etc)
    ss08    Stylistic Set 8 -- Upright integral variants; XITS compatible
    ss09    Stylistic Set 9 -- Vertical slash variants; XITS compatible
    ss10    Stylistic Set 10 -- Diagonal greater/lesser combination variants
    ss11    Stylistic Set 11 -- Long slash not-equal combination variants
    ss12    Stylistic Set 12 -- Low contrast (sans-like) variants
    ss13    Stylistic Set 13 -- Horizontally flipped sine wave glyph
    ss14    Stylistic Set 14 -- Tall variants
    ss15    Stylistic Set 15 -- Slab serif symbol variants
    ss16    Stylistic Set 16 -- Circled operator variants
    ss20    Stylistic Set 20 -- Miscellaneous variants
