#!/usr/bin/env python
"""Convert in folder all .jpg, .jpeg, .JPG, and .JPEG, apply watermark that exists in a_file wm.jpg and re-save
    -h / --help
        Print this message and exit
    -d / --debug  <e.g. 0>
        Use this verbosity level to debug program
    -t / --type <e.g. 'tile', 'scale' or 'sign'>
    -V, --version
        Print version and quit \n"
    -w, --watermarkfile <e.g. wm.jpg>
        Use this watermark a_file

Tests:
python watermark.py -w watermarkKPEr.png
>>> main(['-w', 'watermarkKPEr.png'])
Opening water mark a_file watermarkKPEr.png ...
Marking  Figure_1.jpg  and saving as  wFigure_1.jpg
Done.

"""
# import cProfile
import getopt
import sys
from PIL import Image
from PIL import ImageEnhance
from pyDAG import mySystem


def usage(msg=''):
    """Usage description"""
    code = sys.stderr
    print >> code, __doc__
    if msg:
        print >> code, msg
    sys.exit(code)


def reduce_opacity(im, opacity):
    """Returns an image with reduced opacity."""
    assert 1 >= opacity >= 0
    if im.mode != 'RGBA':
        im = im.convert('RGBA')
    else:
        im = im.copy()
    alpha = im.split()[3]
    alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
    im.putalpha(alpha)
    return im


def watermark(im, mark, position, opacity=1.0):
    """Adds a watermark to an image."""
    if opacity < 1:
        mark = reduce_opacity(mark, opacity)
    if im.mode != 'RGBA':
        im = im.convert('RGBA')
    # create a transparent layer the size of the image and draw the
    # watermark in that layer.
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    if position == 'tile':
        for y in range(0, im.size[1], mark.size[1]):
            for x in range(0, im.size[0], mark.size[0]):
                layer.paste(mark, (x, y))
    elif position == 'scale':
        # scale, but preserve the aspect ratio
        ratio = min(
            float(im.size[0]) / mark.size[0], float(im.size[1]) / mark.size[1])
        w = int(mark.size[0] * ratio)
        h = int(mark.size[1] * ratio)
        mark = mark.resize((w, h))
        layer.paste(mark, ((im.size[0] - w) / 2, (im.size[1] - h) / 2))
    else:
        layer.paste(mark, position)
    # composite the watermark with the layer
    return Image.composite(layer, im, layer)


def main(argv):
    """Add watermark to all jpegs <a_file>.jpg, saving to w<a_file>.jpg"""

    # Initialize static variables.
    global verbose
    verbose = 0

    # Initialize
    wm_file = 'wm.jpg'
    type_out = 'tile'

    # Options
    options = ""
    try:
        options, remainder = getopt.getopt(argv, 'd:hp:Vw:t:', ['debug=', 'force', 'help', 'program=', 'type=',
                                                                'version', 'watermark'])
    except getopt.GetoptError:
        usage('ERR')
    for opt, arg in options:
        if opt in ('-h', '--help'):
            print usage('help')
        elif opt in ('-d', '--debug'):
            verbose = int(arg)
        elif opt in ('-V', '--version'):
            print 'watermark.py Version 1.0.  DA Gutz 9/12/09'
            exit(0)
        elif opt in ('-t', '--type'):
            type_out = arg
        elif opt in ('-w', '--watermarkfile'):
            wm_file = arg
        else:
            print usage('OK')

    print 'Opening water mark a_file', wm_file, '...'
    mark = Image.open(wm_file)
    
    # Alphabetical directory listing
    d_list_alpha = mySystem.lsl('.')

    # jpeg listings
    j_list = []
    for a_file in d_list_alpha:
        if a_file.count('.jpg') | a_file.count('.jpeg') | a_file.count('JPG') | \
                a_file.count('JPEG'):
            if a_file.count(wm_file) == 0:
                j_list.append(a_file)
    if j_list.__len__():
        for a_file in j_list:
            s_file = 'w' + a_file
            print 'Marking ', a_file, ' and saving as ', s_file
            im = Image.open(a_file)
            im_mod = im.copy()
            if type_out == 'tile':
                im_mod = watermark(im, mark, 'tile', 0.08)
            elif type_out == 'scale':
                im_mod = watermark(im, mark, 'scale', 0.08)
            elif type_out == 'sign':
                im_mod = watermark(im, mark, (im.size[0]-mark.size[0], im.size[1]-mark.size[1]), 0.8)
            else:
                print 'watermark.py:  unknown type'
            if verbose > 3:
                im_mod.show()
            im_mod.save(s_file)
    else:
        print 'No files...'
    print 'Done.'


if __name__ == '__main__':
    # sys.exit(cProfile.run("main(sys.argv[1:])"))
    sys.exit(main(sys.argv[1:]))
