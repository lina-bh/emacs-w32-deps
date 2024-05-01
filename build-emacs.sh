#!/bin/bash
set -e
prefix="$(realpath ./out)"
emacs="emacs-29.3"
if [ ! -d "$emacs" ]; then
	wget --no-clobber "https://ftp.gnu.org/gnu/emacs/${emacs}.tar.xz"
	tar -xvf "${emacs}.tar.xz"
fi
mkdir -p "$prefix"
if [ ! -e "${prefix}/bin/emacs.exe" ]; then
	cd "$emacs"
	dash ./configure -C --prefix="$prefix" --disable-acl --without-all \
             --with-{w32,toolkit-scroll-bars,mailutils,native-image-api,small-ja-dic,file-notification=w32,gnutls,compress-install} \
             --without-libgmp CC="ccache gcc" CFLAGS="-Os -pipe"
	make
	make install
fi
cd "$prefix/bin"
rm "${emacs}.exe"
for binary in *.exe; do
	strip -v -s "$binary"
done
cd "${prefix}/share/emacs/site-lisp"
cat > site-start.el <<EOF
-*- lexical-binding: t; -*-
(push invocation-directory exec-path)
EOF
