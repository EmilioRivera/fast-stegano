# Steganography

Quick repo doing steganography, originally inspired from this repository: https://github.com/kelvins/steganography, but using bitwise operations with Pillow-SIMD.

As a more general solution, module `linear_stegano.py` is based on `numpy` arrays which is still substianlly faster.
# Installation
You need Python 3.x for this project. I suggest using [pyenv](https://github.com/pyenv/pyenv).
Then you can create a virtual environment with

`python -m venv .venvs/stegano`

The activate it with

`source .venvs/stegano/bin/activate`.

Then install dependencies with
`pip install -r requirements.txt`


# How to use

For quick and easy steganography I suggest using `linear_stegano.py` in the following way:

**tl;dr: \
`python linear_stegano.py hide --base container.png --secret secret.jpg` 
\
and \
`python linear_stegano.py reveal --base steganographied.png`**


## Hiding image within image
Consider you want to:
- Use _myimage.wtv_ as **the image that will contain the image NOT the secret**
- Use _secret.wtv_ as **the image that will be hidden**

`python linear_stegano.py hide --base myimage.wtv --secret secret.wtv [--output name_of_output.png]`

### Notes
**N.B: If specifying the _optional_ `--output`, the file extension HAS to be `.png`. Specifying an output _will_ overwrite a previous file with the same name** 

If no output is specified, a new file will be created for you with a suffix `_hidden` based on the input file name. For example, with the above example, the resulting output file name if not specified would be `secret_hidden.png`.

If no output is specified via `--output` *and* the resulting file name would clash with an already existing file, a new file name is attributed with the date and time of the operation. For example, if `--output` is not specified and file `secret_hidden.png` already exists, the output will be something like `secret_hidden_2020-21-12-19-21-25.png`.

## Revealing image from file

Consider you want to:
- Use _secret_hidden.png_ as **the image that contains a secret**

`python linear_stegano.py reveal --base secret_hidden.png [--output name_of_output.png]`

The same considerations for `--output` apply for the retrieval (except that instead of `hidden` the suffix is `revealed`). See [this section](#Notes).
