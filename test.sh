#!/usr/bin/env bash
MSB_VALUES=( 0 1 2 3 4 5 6 7 8 )
INPUT_FILE="${INPUT_FILE:-input.jpg}"
CONCEAL_FILE="${CONCEAL_FILE:-toconceal.jpg}"

if [ ! -f "$INPUT_FILE" ]; then
    echo "Input file $INPUT_FILE does not exist!"
    exit 1
fi

if [ ! -f "$CONCEAL_FILE" ]; then
    echo "Input file $CONCEAL_FILE does not exist!"
    exit 1
fi

mkdir -p 'test'

# TODO: Put correct venv path or comment if not needed
source './.stegano/bin/activate'

echo "Pillow-SIMD method tests..."
for n in "${MSB_VALUES[@]}"; do
    echo "$n"
    python stegano.py merge --img1 "$INPUT_FILE" --img2 "$CONCEAL_FILE" --output "test/concealed_${n}.png" -n "$n"
    python stegano.py unmerge --img "test/concealed_${n}.png" --output "test/reconstructed_${n}.png" -n "$n"
done

# TODO: Force lossy/lossless mode
echo "Linear method tests..."
for noise in "fill-with-noise" "no-noise"; do
    python linear_stegano.py hide --base "$INPUT_FILE" --secret "$CONCEAL_FILE" "--$noise" --output "test/concealed_${detail}_${noise}.png"
    python linear_stegano.py reveal --base "test/concealed_${detail}_${noise}.png" --output "test/reconstructed_${detail}_${noise}.png"
done