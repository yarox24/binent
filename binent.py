#!/usr/bin/env python
import argparse
import math
import os
import platform
import sys

try:
   import numpy
except:
   print "Numpy library not installed. To fix this: "
   print "pip install numpy"
   sys.exit(-2)

VERSION = "0.3 (beta)"
PROJECT_SITE = "https://github.com/yarox24/binent"


# PARSER
def entropy_float(x):
   x = float(x)
   if x < 0.0 or x > 8.0:
      raise argparse.ArgumentTypeError("{:} - Entropy valid range is between 1.0-8.0   e.g. 7.993".format(x))
   return x


def utf_variable(string):
   utf = string.decode(sys.getfilesystemencoding(), "replace")
   return utf


parser = argparse.ArgumentParser(description='Cross-platform entropy calculation script with filtering and custom-block size options.')
parser.add_argument('-c', '--chunk', nargs=1, help='Fixed block-size (e.g. 256, 15K, 20M, 30G) Default: whole file')
parser.add_argument('-r', '--recursive', dest='recursive', action='store_true', help='Recursive traversal')
parser.add_argument('-l', "--low_limit", default=1.0, type=entropy_float,
                    help='Show only entries with entropy >= limit (Default: 1.0)')
parser.add_argument('-u', "--upper_limit", default=8.0, type=entropy_float,
                    help='Show only entries with entropy <= limit (Default: 8.0)')
parser.add_argument('-e', "--suppress_errors", action='store_true',
                    help="Don't show any exceptions/errors and also empty files")
parser.add_argument('sources', nargs='*', action='append', type=utf_variable, help="file1 file2 non_empty_dir/ [...]")


def human2bytes(s):
   """
   Bytes-to-human / human-to-bytes converter.
   Based on: http://goo.gl/kTQMs
   Working with Python 2.x and 3.x.
   Author: Giampaolo Rodola' <g.rodola [AT] gmail [DOT] com>
   License: MIT
   """
   SYMBOLS = {
      'customary': ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
      'customary_ext': ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
                        'zetta', 'iotta'),
      'iec': ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
      'iec_ext': ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi',
                  'zebi', 'yobi'),
   }

   if s.strip().isdigit():
      return int(s)

   init = s
   num = ""
   while s and s[0:1].isdigit() or s[0:1] == '.':
      num += s[0]
      s = s[1:]
   try:
      num = float(num)
   except:
      return 0
   letter = s.strip().upper()
   for name, sset in SYMBOLS.items():
      if letter in sset:
         break
   else:
      if letter == 'K':
         sset = SYMBOLS['customary']
         letter = letter.upper()
      else:
         return 0
   prefix = {sset[0]: 1}
   for i, s in enumerate(sset[1:]):
      prefix[s] = 1 << (i + 1) * 10
   return int(num * prefix[letter])


def correct_float(fl):
   out = numpy.empty_like(fl, dtype=numpy.float64)

   if fl < 7.99:
      numpy.round(fl, 4, out)
   else:
      # Eight is special case and shouldn't be rounded, just truncation 7.99xxxx = 7.99 and only real 8.0 = 8.0
      temp = numpy.empty_like(fl, dtype=numpy.float64)
      numpy.subtract(fl, numpy.round(fl - 0.005, 2, temp), temp)
      numpy.subtract(fl, temp, out)
   return out.item(0)


def shortcut_filename(filename):
   if len(filename) > 40:
      cut = len(filename) - 40
      center = len(filename) / 2
      temp = filename[:center - 1 - int(math.ceil(cut / 2) + 1)] + "[..]" + filename[
                                                                            center + 3 + int(math.floor(cut / 2)):]
      return temp
   else:
      return filename


def create_visual(float_entropy):
   how_many = int(numpy.round(float_entropy, decimals=0))
   return "|" + str("#" * how_many).ljust(8) + "|"


def print_error(text, suppress_errors_flag):
   if not suppress_errors_flag:
      sys.stderr.write(text + "\n")


def only_file_output(path, chunk_size):
   result = entropy_file(path, chunk_size)
   if result['exception'] == "":
      count_chunks = len(result['entropy_chunks'])

      if count_chunks == 1:
         print "Entropy: " + '{:g}'.format(correct_float(result['entropy']))
         print result['interpretation']

      if count_chunks > 1:
         max_len = len(str(result['entropy_chunks_info'][-1][1])) + 2
         print "Chunks (Decimal offsets):"
         print ' ' + 'START'.center(max_len) + "STOP".center(max_len + 2) + ' ' + "ENTROPY".center(
            10) + " VISUAL".center(12)

         for i in range(0, count_chunks):
            print ' {:} {:} {:}  {:10}'.format(
               str(result['entropy_chunks_info'][i][0]).center(max_len),
               str(result['entropy_chunks_info'][i][1]).center(max_len + 1),
               " {: <9}".format(correct_float(result['entropy_chunks'][i])),
               create_visual(result['entropy_chunks'][i]))
   else:
      print_error(result['exception'], False)
      sys.exit(-3)


def many_files_output(path, comp, suppress_err):
   # Unicode assumed
   result = entropy_file(path, 0)

   filename = shortcut_filename(os.path.basename(path))
   if result['exception'] == "":
      # Filter results
      if not comp(result['entropy']):
         return
      print ' {:<40} {:<13} {:<10}'.format(filename.encode("ascii", "replace"), correct_float(result['entropy']),
                                           create_visual(result['entropy']))
   else:
      print_error(' {:<40} {:<13}'.format(filename.encode("ascii", "replace"), result['exception'].strip()),
                  suppress_err)


def recursive_output(starting_point, comp, suppress_err):
   for (current_dir, _, filenames) in os.walk(starting_point):
      for file in filenames:
         absolute_path = os.path.join(current_dir, file)
         if not os.path.isfile(absolute_path):
            # print_error(absolute_path + ": Is not a file")
            continue

         result = entropy_file(absolute_path, 0)
         if result['exception'] != "":
            print_error(absolute_path + ": " + result['exception'], suppress_err)
         else:
            # Filter results
            if not comp(result['entropy']):
               continue
            print '"{:}",{:},{:},"{:}","{:}"'.format(absolute_path.encode("ascii", "replace"),
                                                     correct_float(result['entropy']), result['entropy'],
                                                     result['interpretation'], create_visual(result['entropy']))


def interpretation(entropy):
   if entropy == 0.0:
      return "No information!"
   elif entropy > 0.0 and entropy < 3.9:
      return "Low entropy. Potential for compression"
   elif entropy < 4.9:
      return "Possible plain text"
   elif entropy < 5.63:
      return "Like source code"
   elif entropy < 6.54:
      return "Poor compression/encryption"
   elif entropy < 7.00:
      return "Almost good compresion/encryption/randomness"
   elif entropy < 7.70:
      return "Good compresion/encryption/randomness"
   elif entropy < 8:
      return "Very good compresion/encryption/randomness"
   elif entropy == 8.00:
      return "ULTIMATE compresion/encryption/randomness!"
   else:
      return "Exception: Entropy out of range"


def provide_next(start, stop, max, one_time_max):
   start = stop
   stop += one_time_max

   still_valid = True
   if stop >= max:
      stop = max
   if stop == start:
      still_valid = False

   return (start, stop, still_valid)


def entropy_file(path, chunk_size):
   result = dict()
   result['entropy'] = 0.0
   result['entropy_chunks'] = list()
   result['entropy_chunks_info'] = list()
   result['interpretation'] = ""
   result['exception'] = ""

   size = os.path.getsize(path)
   if chunk_size == 0 or chunk_size > size:
      chunk_size = size

   mm = None
   try:
      pointer = 0

      if size == 0:
         result['exception'] = "Exception: Empty file"
         return result

      if size > min(sys.maxsize - 100 * 1024 * 1024, 1024 * 1024 * 1024) and platform.architecture()[0] == "32bit":
         result['exception'] = "32-bit limit (1-2GB) use 64-bit python"
         return result

      mm = numpy.memmap(path, dtype='uint8', mode='r')
      while pointer < size:
         # fix_last_one = False
         # CHECK BOUNDARIES
         end = pointer + chunk_size
         if end > size:
            # fix_last_one = True
            end = size
         current_capacity = end - pointer

         # WEIGHTS
         # Memory less-usage
         MAX_ONE_TIME = 512 * 1024
         weights = numpy.zeros(256)

         temp_start = pointer
         temp_end = pointer + MAX_ONE_TIME
         if temp_end > end:
            temp_end = end

         if current_capacity > MAX_ONE_TIME:
            while True:
               weights = numpy.add(numpy.bincount(mm[temp_start:temp_end], minlength=256), weights)
               (temp_start, temp_end, valid) = provide_next(temp_start, temp_end, end, MAX_ONE_TIME)
               if valid == False:
                  break
         else:
            weights = numpy.bincount(mm[pointer:end], minlength=256)

         prob = numpy.divide(weights, float(current_capacity))
         result_temp = 0.0

         for i in range(0, 256):
            if prob[i] > 0.0:
               result_temp += -prob[i] * numpy.log2(prob[i])
         # if fix_last_one:
         #   tempopy = tempopy /numpy.log2(current_capacity) * numpy.log2(chunk_size)
         result['entropy_chunks'].append(result_temp)
         result['entropy_chunks_info'].append((pointer, end - 1))
         pointer += chunk_size
      result['entropy'] = numpy.mean(result['entropy_chunks'])
      result['interpretation'] = interpretation(result['entropy'])

   except Exception as e:
      result['exception'] = "Exception: " + e.message + e.__str__()

   # CLEAN MEMORY MAPPING
   try:
      del mm
   except NameError:
      pass
   return result


def main():
   args = parser.parse_args()
   recursive = args.recursive
   chunk_size = 0  # AUTOMATIC
   sources = args.sources[0]
   low_limit = args.low_limit - 0.001
   upper_limit = args.upper_limit + 0.001
   suppress_errors = args.suppress_errors

   if low_limit > upper_limit:
      print "Error: Wrong limits. Nothing will be found"
      sys.exit(-65)

   entropy_filter = lambda x: True if x >= low_limit and x <= upper_limit else False
   items_number = len(sources)

   if items_number == 0:
      print("binent v " + VERSION + "\t-== " + PROJECT_SITE + " ==-")
      print("*** Please provide at least one file or directory")
      print("")
      print("Examples:")
      print("1. Calculate/interpret entropy of single file:")
      print(" " + sys.argv[0] + " unk.zip")
      print("")
      print("2. Calculate entropy of single file with custom defined block-size = 10M(B):")
      print(" " + sys.argv[0] + " -c 10M large.iso")
      print("")
      print("3. Calculate entropy of files inside directory (non-recursive):")
      print(" " + sys.argv[0] + " mp3_dir")
      print("")
      print("4. Calculate entropy for files in directory and sub-directories (recursive):")
      print(" " + sys.argv[0] + " -r starting_directory")
      print("")
      sys.exit(0)

   if args.chunk:
      test_size = human2bytes(args.chunk[0])
      if test_size > 0:
         chunk_size = test_size
      else:
         print "Incorrect chunk size. Sample valid ones: 256 or 100K or 33.5M or 20G"
         sys.exit(-11)

   for path in sources:
      if len(path) > 2:
         path = path.rstrip("/\\").rstrip('"').rstrip("'")
      if os.path.isdir(path):
         if recursive:
            print 'Absolute_path,Entropy_rounded,Entropy_precise,Interpretation,Visual'
            recursive_output(path, entropy_filter, suppress_errors)
            break
         else:
            print 'FILENAME'.center(38) + "ENTROPY".center(15) + "     VISUAL"
            # NON-RECURSIVE
            # STILL UNICODE PROBLEMS WHEN PASSING DIR ON WINDOWS ON SOME CHARACTERS EXAMPLE: e with dash
            try:
               files = os.listdir(path)
            except Exception as e:
               if not suppress_errors:
                  print("Error when listing directory: %s" % (path) + " [" + e.strerror + e.message + "]")
               continue
            for file in files:
               full_path = path + os.path.sep + file
               if os.path.isfile(full_path):
                  many_files_output(full_path, entropy_filter, suppress_errors)
      elif os.path.isfile(path):
         only_file_output(path, chunk_size)
      else:
         print("Error: File/directory doesn't exist: " + path)


if __name__ == "__main__":
   main()
