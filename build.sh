#!/usr/bin/env bash

set -e

FAMILY=STIXTwo
TEXT_FAMILY=${FAMILY}Text
MATH_FAMILY=${FAMILY}Math
TEXT_MASTERS="Regular Bold Italic BoldItalic"
MATH_MASTERS="Regular"
VF="Roman Italic"

BUILD="${PWD}/build"
SOURCE="${PWD}/source"
TOOLS="${PWD}/tools"

rm -rf "${BUILD}"
mkdir -p "${BUILD}/masters"

echo "Pre-processing UFOs:"
for m in ${TEXT_MASTERS}; do
	UFO=${TEXT_FAMILY}-${m}.ufo
	echo "    ${UFO}"
	python3 "${TOOLS}"/preprocess-ufo.py "${SOURCE}"/${UFO} \
					  "${SOURCE}"/STIX2-Dev2Post.ren \
					  "${SOURCE}"/${TEXT_FAMILY}-${m}.input.ttf \
					  "${BUILD}"/masters/${UFO}
done

for m in ${MATH_MASTERS}; do
	UFO=${MATH_FAMILY}-${m}.ufo
	echo "    ${UFO}"
	python3 "${TOOLS}"/preprocess-ufo.py "${SOURCE}"/${UFO} \
					  "${SOURCE}"/STIX2-Dev2Post.ren \
					  "${SOURCE}"/${MATH_FAMILY}-${m}.input.ttf \
					  "${BUILD}"/masters/${UFO}
done

FMOPTS="--feature-writer=None --subroutinizer=cffsubr --overlaps-backend=pathops"
if test "$1" != "--verbose"; then
	FMOPTS="${FMOPTS} --verbose=WARNING"
fi

cd "${BUILD}" || exit

for v in $VF; do
	echo ""
	echo "Building ${v} fonts:"

	DS=${TEXT_FAMILY}VF-${v}.designspace
	cp "${SOURCE}/${DS}" "${DS}"

	echo "    variable"
	fontmake ${FMOPTS} -m "${DS}" -o variable
	if [ ${v} = "Roman" ]; then
		mv "variable_ttf/${TEXT_FAMILY}VF-${v}-VF.ttf" "variable_ttf/${TEXT_FAMILY}[wght].ttf"
	else
		mv "variable_ttf/${TEXT_FAMILY}VF-${v}-VF.ttf" "variable_ttf/${TEXT_FAMILY}-${v}[wght].ttf"
	fi

	echo "    masters"
	fontmake ${FMOPTS} -m "${DS}" -o ttf otf --optimize-cff=0 --keep-overlaps

	echo "    static"
	fontmake ${FMOPTS} -m "${DS}" -o ttf --optimize-cff=0 -i --interpolate-binary-layout --output-dir static_ttf
	fontmake ${FMOPTS} -m "${DS}" -o otf --optimize-cff=0 -i --interpolate-binary-layout --output-dir static_otf
done

echo ""
echo "Building math fonts:"
for m in ${MATH_MASTERS}; do
	UFO=${MATH_FAMILY}-${m}.ufo
	echo "    ${UFO}"
	fontmake ${FMOPTS} -u "masters/${UFO}" -o ttf --optimize-cff=0 --output-path="static_ttf/${MATH_FAMILY}-${m}.ttf"
	fontmake ${FMOPTS} -u "masters/${UFO}" -o otf --optimize-cff=0 --output-path="static_otf/${MATH_FAMILY}-${m}.otf"
done

echo ""
echo "Autohinting:"
for f in static_ttf/*.ttf; do
	echo "    $(basename "${f}")"
	temp=$(mktemp)
	python -m ttfautohint --no-info "${f}" "${temp}"
	mv "${temp}" "${f}"
done

for f in static_otf/*.otf; do
	echo "    $(basename "${f}")"
	temp=$(mktemp)
	psautohint "${f}" -o "${temp}"
	python -m cffsubr "${temp}" -o "${f}"
done

# Fix name string for italic fonts
echo ""
echo "Post-processing fonts:"
for f in static_*/*.{ttf,otf}; do
	echo "    $(basename "${f}")"
	python3 "${TOOLS}"/postprocess-static.py "${f}"
done

for f in variable_ttf/*.ttf; do
	echo "    $(basename "${f}")"
	python3 "${TOOLS}"/postprocess-variable.py "${f}"
done

echo ""
echo "Web fonts:"
for w in woff woff2; do
	echo "    ${w}:"
	for f in static_*/*.{ttf,otf}; do
		b=$(basename "${f}")
		e=${b##*.}
		b=${b%.*}
		echo "        ${b}.${w}"
		mkdir -p static_${e}_${w}
		python3 "${TOOLS}"/make-woff.py "${f}" ${w} static_${e}_${w}/${b}.${w}
	done
	for f in variable_ttf/*.ttf; do
		b=$(basename "${f}")
		e=${b##*.}
		b=${b%.*}
		echo "        ${b}.${w}"
		mkdir -p variable_${e}_${w}
		python3 "${TOOLS}"/make-woff.py "${f}" ${w} variable_${e}_${w}/${b}.${w}
	done
done
