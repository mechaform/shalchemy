import argparse
import os
import sys
import select
from typing import List


def run_complain(args: argparse.Namespace, rest: List[str]):
    if args.n:
        end=''
    else:
        end='\n'
    output = ' '.join(rest) + end
    if args.both:
        sys.stdout.write(output)
        sys.stdout.flush()
    sys.stderr.write(output)
    sys.stderr.flush()


def run_errcat(args: argparse.Namespace, rest: List[str]):
    if len(args.files) > 0:
        for fname in args.files:
            with open(fname, 'r') as fileobj:
                sys.stderr.write(fileobj.read())
        return
    while True:
        ready, _, _ = select.select([sys.stdin], [], [], 0.0)
        stdin_fd = sys.stdin.fileno()
        stdout_fd = sys.stdout.fileno()
        stderr_fd = sys.stderr.fileno()
        if sys.stdin in ready:
            data = os.read(stdin_fd, 4096)
            if len(data) == 0:
                break
            if args.both:
                os.write(stdout_fd, data)
            os.write(stderr_fd, data)


def run_args(args: argparse.Namespace, rest: List[str]):
    print(sys.argv)


def probe_main():
    parser = argparse.ArgumentParser(description='shalchemyprobe is a tool for testing shalchemy')
    subparsers = parser.add_subparsers()

    parser_complain = subparsers.add_parser('complain', help='complain is like echo but prints to stderr')
    parser_complain.add_argument('-n', action='store_true')
    parser_complain.add_argument('--both', action='store_true')
    parser_complain.set_defaults(func=run_complain)

    parser_errcat = subparsers.add_parser('errcat', help='errcat is like cat but prints to stderr')
    parser_errcat.add_argument('--both', action='store_true')
    parser_errcat.add_argument('files', nargs='*')
    parser_errcat.set_defaults(func=run_errcat)

    parser_args = subparsers.add_parser('args', help='args prints out the args provided')
    parser_args.set_defaults(func=run_args)

    known, rest = parser.parse_known_args()
    if not hasattr(known, 'func'):
        parser.print_help()
    else:
        known.func(known, rest)
