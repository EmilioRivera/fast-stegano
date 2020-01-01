#!/usr/bin/env bash
MSB_VALUES=( 0 1 2 3 4 5 6 7 8 )
INPUT_FILE="${INPUT_FILE:-input.jpg}"
CONCEAL_FILE="${CONCEAL_FILE:-toconceal.jpg}"

mkdir -p 'test'

# TODO: Put correct venv path or comment if not needed
source './.stegano/bin/activate'

for n in "${MSB_VALUES[@]}"; do
    echo "$n"
    python stegano.py merge --img1 "$INPUT_FILE" --img2 "$CONCEAL_FILE" --output "test/concealed_${n}.png" -n "$n"
    python stegano.py unmerge --img "test/concealed_${n}.png" --output "test/reconstructed_${n}.png" -n "$n"
done
