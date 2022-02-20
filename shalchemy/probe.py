from typing import cast, List
import argparse
import io
import json
import os
import sys
import select


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


def run_kwcat(args: argparse.Namespace, rest: List[str]):
    kwargs = [args.apple, args.banana, args.carrot]
    for filename in kwargs:
        if filename is None:
            continue
        with open(filename, 'r') as file:
            print(file.read(), end='')


def run_kwtee(args: argparse.Namespace, rest: List[str]):
    files: List[io.IOBase] = []
    kwargs = [args.apple, args.banana, args.carrot]
    for filename in kwargs:
        if filename is not None:
            fp = cast(io.IOBase, open(filename, 'wb'))
            files.append(fp)

    stdin_fd = sys.stdin.fileno()
    stdout_fd = sys.stdout.fileno()
    while True:
        ready, _, _ = select.select([sys.stdin], [], [], 0.0)
        if sys.stdin in ready:
            data = os.read(stdin_fd, 4096)
            if len(data) == 0:
                break
            for file in files:
                file.write(data)
            os.write(stdout_fd, data)

    for file in files:
        file.close()


def run_args(args: argparse.Namespace, rest: List[str]):
    print(json.dumps(sys.argv))


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

    parser_kwtee = subparsers.add_parser('kwtee', help='kwtee is like tee but the files are keyword arguments for testing purposes')
    parser_kwtee.add_argument('--apple')
    parser_kwtee.add_argument('--banana')
    parser_kwtee.add_argument('--carrot')
    parser_kwtee.set_defaults(func=run_kwtee)

    parser_kwcat = subparsers.add_parser('kwcat', help='kwcat is like cat but the files are keyword arguments for testing purposes')
    parser_kwcat.add_argument('--apple')
    parser_kwcat.add_argument('--banana')
    parser_kwcat.add_argument('--carrot')
    parser_kwcat.set_defaults(func=run_kwcat)

    parser_args = subparsers.add_parser('args', help='args prints out the args provided')
    parser_args.set_defaults(func=run_args)

    known, rest = parser.parse_known_args()
    if not hasattr(known, 'func'):
        parser.print_help()
    else:
        known.func(known, rest)
