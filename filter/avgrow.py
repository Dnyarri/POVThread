#!/usr/bin/env python3

"""Averaging image pixels in a row until reaching
``abs(average - current) > threshold``, then repeating in a column.

Pure Python image filtering module for `POV-Ray Thread`_ and
`Averager`_ applications.

Initial purpose was transforming row sequences of closely colored pixels
into a sequence of the same solid color to simulate single thread in canvas;
however filter may work with columns as well,
producing squarish flat color areas.

Usage
-----

::

    from filter.avgrow import filter
    filtered_image = filter(source_image, threshold_x, threshold_y, wraparound, keep_alpha)

where:

- **``source_image``**: input image as list of lists of lists
  of ``int`` channel values;
- **``threshold_x``**: threshold upon which row averaging stops
  and restarts from this pixel on (``int``);
- **``threshold_y``**: threshold upon which column averaging stops
  and restarts from this pixel on (``int``);
- **``wrap_around``**: whether image edge pixel will be read in
  "repeat edge" or "wrap around" mode (``bool``);
- **``keep_alpha``**: whether returned filtered image will have
  alpha channel copied from source image, or alpha channel will be
  filtered along with color (``bool``).

.. note:: Both threshold values (``int``) are used literally,
    regardless of 8 bpc or 16 bpc color depth.
    Filter input does not include color depth and/or range value in any form,
    therefore threshold range normalization, if deemed necessary,
    must be performed at host end.

.. warning:: Some programs completely destroy L or RGB data upon saving
    LA or RGBA image pixels with A=0 (fully transparent) as PNG.
    This may lead to unexpected and unpredictable results of filtering.
    This potential problem is completely out of responsibility scope
    of current filter developer.

-----
Main site: `The Toad's Slimy Mudhole`_

`POV-Ray Thread`_ previews and description

`Averager`_ preview and description

POV-Ray Thread source: main `@Github`_ and mirror `@Gitflic`_

.. _The Toad's Slimy Mudhole: https://dnyarri.github.io

.. _POV-Ray Thread: https://dnyarri.github.io/povthread.html

.. _Averager: https://dnyarri.github.io/povthread.html#averager

.. _@Github: https://github.com/Dnyarri/POVthread

.. _@Gitflic: https://gitflic.ru/project/dnyarri/povthread

"""

#   History:
#   --------
# 0.10.12.3     Initial version - 12 Oct 2024. RGB only.
# 0.10.13.2     Forces RGB, skips alpha. Changed threshold condition to r, g, b
#                   separately. Seem to be just what I need.
# 0.10.25.1     Bugfix for tiny details.
# 1.16.5.10     Modularization, some optimization. Force keep alpha.
# 1.17.10.1     Edge condition bugfix.
# 2.19.14.16    Wrap around processing introduced.
# 3.20.1.1      Substantial rewriting with `map` to correctly support L.
#                   No force RGB anymore.
# 3.20.7.14     Alpha filtering. Full support for L, LA, RGB, RGBA filtering
#                   with a single `map`.
# 3.20.20.3     Code harmonization. Lambdas completely replaced with operators
#                   and defined functions to improve speed.
# 3.22.13.11    Unnecessary map to list conversions removed,
#                   necessary ones replaced with [*map] unpacking.
# 3.22.18.8     Evasive bug discovered and presumably exterminated.
# 3.26.6.18     Major minor refurbishment: docstring etc. etc.
# 3.26.20.8     Surprisingly, there is a room for optimizing "create_image"!
# 3.33.23.23    Converting some lists to tuples gives ca. 7% more speed.

__author__ = 'Ilya Razmanov'
__copyright__ = '(c) 2024-2026 Ilya Razmanov'
__credits__ = 'Ilya Razmanov'
__license__ = 'unlicense'
__version__ = '3.33.23.23'  # 23 Sep 2026
__maintainer__ = 'Ilya Razmanov'
__email__ = 'ilyarazmanov@gmail.com'
__status__ = 'Production'

from operator import add, floordiv  # Operator in `map` seem to work ca. 7% faster than lambda.


def create_image(X: int, Y: int, Z: int, cheat: bool = True) -> list[list[list[int]]] | list[list[tuple[int]]]:
    """Create 3D nested list of X * Y * Z size, filled with zeroes.
    Addressing is ``result[y][x][z]``.

    :param int X: image width, pixels;
    :param int Y: image height, pixels;
    :param int Z: number of image channels;
    :param bool cheat: whether to use some in-row links
        instead of fair 3D-list to speed image creation up.
        Links ought to be replaced with pixels when filtering.
    :return: empty image as 3D nested list of X * Y * Z size, filled with zeroes.
        Addressing is ``list[y][x][z]``.
    :rtype: list[list[list[int]]] or list[list[tuple[int]]].

    """

    if cheat:
        return [[(0,) * Z] * X for y in range(Y)]
    # ↑ Works ca. 80 times faster than fair 3D-list comprehension,
    #   but creates in-row and in-pixel links, harmless for this filter.
    #   NOTE: Can NOT be replaced with "[[[0] * Z] * X] * Y",
    #         since the latter creates cross-row links as well.

    return [[[z for z in range(Z)] for x in range(X)] for y in range(Y)]
    # ↑ Fair 3D-list comprehension, no cheating, no cross-links.


def filter(source_image: list[list[list[int]]], threshold_x: int, threshold_y: int, wrap_around: bool = False, keep_alpha: bool = False) -> list[list[list[int]]]:
    """Average image pixels in a row until
    **``abs(average - current) > threshold``**
    criterion met, then repeat in a column.

    :param source_image: input image as nested list of ``int`` channel values;
        coordinate system match Photoshop, i.e. origin is top left corner,
        channels order is LA or RGBA from 0 to top;
    :type source_image: list[list[list[int]]]
    :param int threshold_x: threshold upon which row averaging stops
        and restarts from this pixel on;
    :param int threshold_y: threshold upon which column averaging stops
        and restarts from this pixel on;
    :param bool wrap_around: whether image edge pixel will be read in
        "repeat edge" or "wrap around" mode;
    :param bool keep_alpha: whether returned filtered image will have
        alpha channel copied from source image, or alpha channel will be
        filtered along with color;
    :return: filtered image of the same type and size as ``source_image``.
    :rtype: list[list[list[int]]]

    """

    # ↓ Determining image sizes.
    Y, X, Z = (len(source_image), len(source_image[0]), len(source_image[0][0]))
    # ↓ Number of color channels, alpha excluded.
    Z_COLOR = Z if Z == 1 or Z == 3 else min(Z - 1, 3)

    """ ╭──────────────────────────────────────────╮
        │ Coordinates for reading and writing.     │
        │ NOTE: with 0 overhead filter never goes  │
        │ out of image list index, so separate src │
        │ for repeat edge is unnecessary, and is   │
        │ kept here just for reference and reuse.  │
        ╰──────────────────────────────────────────╯ """

    def _cx_repeat(x: int) -> int:
        """``x`` coordinate for repeat edge processing"""
        return min((X - 1), max(0, int(x)))  # x repeat edge

    def _cx_wrap(x: int) -> int:
        """``x`` coordinate for wrap around processing"""
        return int(x) % X  # x wrap around

    def _cy_repeat(y: int) -> int:
        """``y`` coordinate for repeat edge processing"""
        return min((Y - 1), max(0, int(y)))  # y repeat edge

    def _cy_wrap(y: int) -> int:
        """``y`` coordinate for wrap around processing"""
        return int(y) % Y  # y wrap around

    # ↓ Setting wrap around as default, with overhead = 0 it works like "as is".
    cx = _cx_wrap
    cy = _cy_wrap

    """ Threshold criteria may never be met, yet loop must be stopped somewhere.
        Therefore some maximal run length overhead defined be must.
        Small values sometimes fail (i.e. filter prematurely react
        on short smooth sequences), while values bigger than image size make no sense. """
    if wrap_around:
        x_overhead, y_overhead = X, Y
    else:
        x_overhead = y_overhead = 0

    """ ╭─────────────────╮
        │ Horizontal pass │
        ╰─────────────────╯ """
    # ↓ Creating empty intermediate image.
    intermediate_image = create_image(X, Y, Z, cheat=True)

    def _criterion_x(channel: int, channel_sum: int) -> bool:
        """Threshold criterion for horizontal pass, single channel.
        Uses outer scope ``number`` and ``threshold_x``."""
        return abs(channel - (channel_sum / number)) > threshold_x
        # ↑ Defined function seem to work ca. 5% faster than lambda.
        #   Uses outer scope `number` and `threshold_x`.

    for y in range(0, Y, 1):
        x_start = 0  # Defining start of inner loop of averaging until threshold hit.
        number = 1  # Number of pixels being read during averaging loop.
        pixel = source_image[cy(y)][0]  # Starting pixel.
        pixels_sum = pixel  # Sum of pixels being read during averaging loop.
        for x in range(0, X + x_overhead, 1):
            number += 1
            """ Core part of averaging - adding up.
            It is important to sum pixels read BEFORE current pixel
            so when checking threshold and writing an averaged line
            edge pixel is not included into average. """
            pixels_sum = (*map(add, pixel, pixels_sum),)
            pixel = source_image[cy(y)][cx(x)]
            # ↓ Checking criterion. Alpha excluded from criterion check.
            if any(map(_criterion_x, pixel[:Z_COLOR], pixels_sum[:Z_COLOR])):
                """ Dividing sum by pixel number for inner row loop
                    BEFORE potential criterion hit.
                NOTE: Alpha included in calculation but NOT in check. """
                average_pixel = (*map(floordiv, pixels_sum, (number,) * Z),)  # Inner loop result.
                for i in range(x_start, x - 1, 1):
                    intermediate_image[y][cx(i)] = average_pixel
                # ↓ Redefining starting values of new inner loop until threshold.
                x_start = x
                number = 1
                pixels_sum = pixel
            intermediate_image[y][cx(x)] = pixel  # Edge pixel.

    """ ╭───────────────╮
        │ Vertical pass │
        ╰───────────────╯ """
    # ↓ Creating empty final image.
    result_image = create_image(X, Y, Z, cheat=True)

    def _criterion_y(channel: int, channel_sum: int) -> bool:
        """Threshold criterion for vertical pass, single channel.
        Uses outer scope ``number`` and ``threshold_y``."""
        return abs(channel - (channel_sum / number)) > threshold_y

    for x in range(0, X, 1):
        y_start = 0
        number = 1
        pixel = intermediate_image[0][cx(x)]
        pixels_sum = pixel
        for y in range(0, Y + y_overhead, 1):
            number += 1
            pixels_sum = (*map(add, pixel, pixels_sum),)
            pixel = intermediate_image[cy(y)][cx(x)]
            if any(map(_criterion_y, pixel[:Z_COLOR], pixels_sum[:Z_COLOR])):
                average_pixel = (*map(floordiv, pixels_sum, (number,) * Z),)
                for i in range(y_start, y - 1, 1):
                    result_image[cy(i)][x] = average_pixel
                y_start = y
                number = 1
                pixels_sum = pixel
            result_image[cy(y)][x] = pixel

    """ ╭────────────────╮
        │ Alpha handling │
        ╰────────────────╯ """
    if Z == 1 or Z == 3:
        return result_image
    else:
        if keep_alpha:
            # ↓ Unpacking result_image pixels, overwriting alpha, and packing back.
            resultimage_plus_alpha = [[(*result_image[y][x][:Z_COLOR], source_image[y][x][Z_COLOR]) for x in range(X)] for y in range(Y)]
            return resultimage_plus_alpha
        else:
            return result_image


# ↑ filter finished

# ↓ Dummy stub for standalone execution attempt
if __name__ == '__main__':
    print('Module to be imported, not run as standalone.')
