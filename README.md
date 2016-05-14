# binent
 Cross-platform entropy calculation script with filtering and custom-block size options. 

## Requirements
- numpy
- Python 2 (not tested on 3)
- Windows/Linux

## Demo
![demo/demo.gif](https://raw.githubusercontent.com/yarox24/binent/master/demo/demo.gif)

##Installation
Work in progress

## Limitations
- calculation of files of any size require 64-bit version of Python

## Usage
Calculate/interpret entropy of single file:
```
binent.py unk.zip
```
Calculate entropy of single file with custom defined block-size = 10M(B):
```
binent.py -c 10M large.iso")
```
Calculate entropy of files inside directory (non-recursive):
```
binent.py mp3_dir
```
Calculate entropy for files in directory and sub-directories (recursive):
```
binent.py -r starting_directory
```

## Options
```
positional arguments:
  sources               file1 file2 non_empty_dir/ [...]

optional arguments:
  -h, --help            show this help message and exit
  -c CHUNK, --chunk CHUNK
                        Fixed block-size (e.g. 256, 15K, 20M, 30G) Default: whole file
  -r, --recursive       Recursive traversal
  -l LOW_LIMIT, --low_limit LOW_LIMIT      
                        Show only entries with entropy >= limit (Default: 1.0)
  -u UPPER_LIMIT, --upper_limit UPPER_LIMIT
                        Show only entries with entropy <= limit (Default: 8.0)
  -e, --suppress_errors
                        Don't show any exceptions/errors and also empty files
```
