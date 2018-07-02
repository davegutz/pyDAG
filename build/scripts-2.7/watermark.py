#!C:\Python27\python.exe
"""Convert in folder all .jpg, .jpeg, .JPG, and .JPEG, apply watermark that exists in file wm.jpg and resave
    -h / --help
        Print this message and exit
    -d / --debug  <e.g. 0>
        Use this verbosity level to debug program
    -t / --type <e.g. 'tile', 'scale' or 'sign'>
    -V, --version
        Print version and quit \n"
    -w, --watermarkfile <e.g. wm.jpg>
        Use this watermark file

Tests:
>>>python watermark.py -w watermarkKPEr.png
"""
import cProfile
import getopt
import sys
import Image, ImageEnhance, ImageDraw, ImageFont
from pyDAG import mySystem

def usage(code, msg=''):
    "Usage description"
    print >> sys.stderr, __doc__
    if msg:
        print >> sys.stderr, msg
    sys.exit(code)

def reduce_opacity(im, opacity):
    """Returns an image with reduced opacity."""
    assert opacity >= 0 and opacity <= 1
    if im.mode != 'RGBA':
        im = im.convert('RGBA')
    else:
        im = im.copy()
    alpha = im.split()[3]
    alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
    im.putalpha(alpha)
    return im

def watermark(im, mark, position, opacity=1):
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
    """Add watermark to all jpegs <file>.jpg, saving to w<file>.jpg"""

    # Initialize static variables.
    global verbose
    verbose = 0

    # Initialize
    help     = False
    force    = False
    quitting = False
    WMFILE   = 'wm.jpg'
    type     = 'tile'

    # Options
    try:
        options, remainder = getopt.getopt(argv, 'd:hp:Vw:t:', ['debug=', 'force', 'help', 'program=', 'type=', 'version','watermark',])
    except getopt.GetoptError:
        usage(2)
    for opt, arg in options:
        if   opt in ('-h', '--help'):
            print usage(1)
        elif opt in ('-d', '--debug'):
            verbose = int(arg)
        elif opt in ('-V', '--version'):
            print 'watermark.py Version 1.0.  DA Gutz 9/12/09'
            exit(0)
        elif opt in ('-t', '--type'):
            type = arg
        elif opt in ('-w', '--watermarkfile'):
            WMFILE = arg
        else: print usage(1)

    print 'Opening water mark file', WMFILE, '...'
    mark = Image.open(WMFILE)
    
    # Alphabetical directory listing
    dListAlpha = mySystem.lsl('.')

    # jpeg listings
    jList = []
    for file in dListAlpha:
        if file.count('.jpg') | file.count('.jpeg') | file.count('JPG') | \
                file.count('JPEG'):
            if file.count(WMFILE) == 0:
                jList.append(file)
    if jList.__len__():
        for file in jList:
            sFile = 'w' + file
            print 'Marking ', file, ' and saving as ', sFile
            im = Image.open(file)
            if type == 'tile':
                immod = watermark(im, mark, 'tile', 0.08)
            elif type == 'scale':
                immod = watermark(im, mark, 'scale', 0.08)
            elif type == 'sign':
                immod = watermark(im, mark, (im.size[0]-mark.size[0], im.size[1]-mark.size[1]), 0.8)
            else:
                print 'watermark.py:  unknown type'
            if verbose > 3:
                immod.show()
            immod.save(sFile)
    else:
        print 'No files...'
    print 'Done.'

if __name__ == '__main__':
    #sys.exit(cProfile.run("main(sys.argv[1:])"))
    sys.exit(main(sys.argv[1:]))

