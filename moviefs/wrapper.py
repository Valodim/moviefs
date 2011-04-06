import db
import moviefs

import tmdb
import os
import sys

import argparse

pathbase = '/home/shared/hd/'

def mode_init(args):
    db.init()

def mode_add(args):

    for fname in args.file:

        print
        print "filename: ", fname

        if not os.access(fname, os.F_OK):
            print "error: file not found!"
            continue

        info = tmdb.findmovieinfo(fname)

        # no name? skip.
        if info is None or len(info['movie']) == 0:
            print "skipping file.."
            break

        else:
            print "Width:", info['attrs']['ID_VIDEO_WIDTH'], "Height:", info['attrs']['ID_VIDEO_HEIGHT']
            info['movie'] =  info['movie'].info()
            # for key in info['movie']:
                # print key, ": ", info['movie'][key]
            movie = db.Movie.get_or_create(info['movie']['id'], os.path.relpath(fname, pathbase), info)

    db.session.commit()

def mode_mount(args):
    moviefs.mount(args.file[0], pathbase, db.session)

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='turn on verbose output to stderr')
    # parser.add_argument('mode', type=complex, choices=[ 'init', 'add' ], help='work mode')
    parser.add_argument('file', nargs='*', help='movie files')
    args = parser.parse_args()

    mode = args.file[0]
    args.file = args.file[1:]
    if mode == 'add':
        mode_add(args)
    elif mode == 'mount':
        mode_mount(args)
    elif mode == 'init':
        mode_init(args)

if __name__ == '__main__':
    main()
