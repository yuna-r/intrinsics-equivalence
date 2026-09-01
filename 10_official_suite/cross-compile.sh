#!/bin/sh
set -eu

suite_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_dir=$(dirname -- "$suite_dir")
output_dir=${1:-"$project_dir/build/official-cross"}

if [ -n "${IOITF_CLANG:-}" ]; then
    compiler=$IOITF_CLANG
elif [ -x /opt/homebrew/opt/llvm/bin/clang ]; then
    compiler=/opt/homebrew/opt/llvm/bin/clang
elif [ -x /usr/local/opt/llvm/bin/clang ]; then
    compiler=/usr/local/opt/llvm/bin/clang
else
    compiler=$(command -v clang)
fi

if ! "$compiler" --print-targets | grep -q 'ppc64le'; then
    echo "clang with the ppc64le backend is required" >&2
    echo "macOS: brew install llvm" >&2
    exit 1
fi

mkdir -p "$output_dir/intel" "$output_dir/openpower"

for block in f64x2 i8x16 i16x8 i32x4 i64x2; do
    "$compiler" \
        --target=x86_64-unknown-linux-gnu \
        -march=x86-64 -msse2 \
        -Wall -Wextra -Wpedantic -Werror \
        -c "$suite_dir/intel/$block.c" \
        -o "$output_dir/intel/$block.o"

    "$compiler" \
        --target=powerpc64le-unknown-linux-gnu \
        -mcpu=power8 -maltivec -mvsx \
        -Wall -Wextra -Wpedantic -Werror \
        -c "$suite_dir/openpower/$block.c" \
        -o "$output_dir/openpower/$block.o"
done

echo "Cross-compiled official suite:"
file "$output_dir/intel/"*.o
file "$output_dir/openpower/"*.o
