## Font formats

### static_otf

This folder contains individual, static fonts in CFF outline format with AFDKO autohinting.

### static_ttf

This folder contains individual, static fonts in TrueType outline format with ttfautohint autohinting.

### variable_ttf

This folder contains OpenType variable fonts in TrueType outline format. The variable fonts are unhinted.

###_woff2

Corresponding _woff2 folders contain compressed webfont versions of each format.

-

All the font formats are generated from the same set of sources, using the build process described in the main project readme, and the static fonts correspond to named instances in the variable fonts.

Note that the build process also generates the older WOFF webfont format, but these files are not made available as part of the standard distribution; run the build process locally to obtain WOFF files.