#!/usr/bin/env python3
import os
import os.path as path
import subprocess
import sys
from typing import NamedTuple
from urllib.parse import urlparse
from pathlib import PurePath
from textwrap import dedent

SCRIPT_DIRECTORY = path.dirname(path.realpath(__file__))
DOWNLOAD_DIRECTORY = path.join(SCRIPT_DIRECTORY, "./tarballs/")
SOURCES_DIRECTORY = path.join(SCRIPT_DIRECTORY, "./unpacked/")
PREFIX_DIRECTORY = path.join(SCRIPT_DIRECTORY, "./prefix/")
RECIPES_DIRECTORY = path.join(SCRIPT_DIRECTORY, "./recipes/")


def eprint(*args, **kwargs):
    if not "file" in kwargs:
        kwargs["file"] = sys.stderr
    return print(*args, **kwargs)


class Source(NamedTuple):
    name: str
    url: str
    target: str
    dependencies: [str]

    @property
    def file(self):
        return path.basename(urlparse(self.url).path)

    @property
    def src(self):
        return self.file.removesuffix(".gz").removesuffix(".xz").removesuffix(".tar")

    @property
    def rule(self):
        return f"{self.name}: {' '.join(self.dependencies)}\n\t\
        test -e {path.join(PREFIX_DIRECTORY, self.target)} || \
        (cd {path.join(SOURCES_DIRECTORY, self.src)} \
        && bash -e {RECIPES_DIRECTORY}/{self.name})\n\n"

    @classmethod
    def from_list(cls, fields):
        if fields[0][0] == "#":
            return
        return cls(
            name=fields[0],
            url=fields[1],
            target="./" + path.normpath(fields[2]),
            dependencies=(fields[3].split(",") if len(fields) >= 4 else []),
        )


def read_sources():
    with open("./sources") as f:
        return [
            tar
            for tar in (
                Source.from_list([field.strip() for field in line.split(" ")])
                for line in f
            )
            if tar is not None
        ]


def download(tar):
    eprint(f"downloading {tar.url}")
    subprocess.run(
        (
            "curl",
            "--disable",
            "--location",
            "--remote-name",
            "--output-dir",
            "tarballs",
            "--progress-bar",
            "--create-dirs",
            "--continue-at",
            "-",
            # "--write-out",
            # "%{filename_effective}",
            tar.url,
        )
    ).check_returncode()


def extract(tar):
    eprint(f"extracting {tar.file}")
    os.makedirs("./unpacked", exist_ok=True)
    subprocess.run(
        ("tar", "-xkv", "-C", "./unpacked", "-f", "./tarballs/" + tar.file)
    ).check_returncode()


def process(tar):
    download(tar)
    extract(tar)


if __name__ == "__main__":
    os.chdir(path.dirname(path.realpath(__file__)))
    eprint(f"working in {os.getcwd()}")
    sources = read_sources()
    for tar in sources:
        process(tar)

    with open("Makefile", "w") as f:
        f.write(
            dedent(f"""\
        export TRIPLE := x86_64-w64-mingw32
        export PREFIX := {PREFIX_DIRECTORY}
        export CFLAGS := -Os -pipe
        export LDFLAGS := -L$(PREFIX)/lib -L$(PREFIX)/bin
        export CPATH := $(PREFIX)/include
        export CPPFLAGS := -I$(PREFIX)/include
        export PKG_CONFIG_PATH := $(PREFIX)/lib/pkgconfig
        export JOBS := 4\n
        """)
        )
        f.write(f"all: {' '.join(tar.name for tar in sources)}\n\t\
        bash -e {RECIPES_DIRECTORY}/package\n\n")
        for rule in (tar.rule for tar in sources):
            f.write(rule)
        # f.write(".PHONY: all " + " ".join(tar.name for tar in sources) + "\n")
    os.makedirs(PREFIX_DIRECTORY, exist_ok=True)
    with open("Makefile") as f:
        sys.stdout.write(f.read())
