import argparse
import os
import sys
import platform
import math

# TODO: REVISE ALL CODE
# TODO: REVISE ALL CODE
# TODO: REVISE ALL CODE
# TODO: REVISE ALL CODE

try:
   import numpy
except:
   print "Numpy library not detected. To fix this: "
   print "pip install numpy"
   sys.exit(-2)

VERSION = "0.2 (beta)"
PROJECT_SITE = "https://github.com/yarox24/binent"

# PARSER
parser = argparse.ArgumentParser(description='Calculate entropy of a file(s)')
parser.add_argument('-c', '--chunk', nargs=1, help='Fixed chunk size (e.g. 44K, 20M)')
parser.add_argument('-r', '--recursive', nargs=1, help='Recursive TOP-BOTTOM traversal')
parser.add_argument('sources', nargs='*', action='append', help="file1 file2 non_empty_dir/ [...]")
args = parser.parse_args()


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
      numpy.round(fl, 3, out)
   else:
      # Eight is special case and shouldn't be rounded, just truncation 7.99xxxx = 7.99 and 8.0 = 8.0
      temp = numpy.empty_like(fl, dtype=numpy.float64)
      numpy.subtract(fl, numpy.round(fl - 0.005, 2, temp), temp)
      numpy.subtract(fl, temp, out)

   return out.item(0)


def shortcut_filename(filename):
   if len(filename) > 25:
      cut = len(filename) - 25
      center = len(filename) / 2
      temp = filename[:center-1-int(math.ceil(cut/2)+1)] + "[..]" + filename[center+3+int(math.floor(cut/2)):]
      return temp
   else:
      return filename


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
            10) + "VISUAL".center(10)

         for i in range(0, count_chunks):
            hashes = "|" + str(numpy.round(result['entropy_chunks'][i], decimals=0) * "#").ljust(8) + "|"
            print ' {:} {:} {:}  {:10}'.format(
               str(result['entropy_chunks_info'][i][0]).center(max_len),
               str(result['entropy_chunks_info'][i][1]).center(max_len + 1),
               " {: <9}".format(correct_float(result['entropy_chunks'][i])),
               hashes)
   else:
      print result['exception']
      sys.exit(-3)


def many_files_output(path, recursive):
   if not hasattr(many_files_output, "i"):
      many_files_output.i = 0
      print 'FILENAME'.center(23) + "ENTROPY".center(13) + "       VISUAL"

   if many_files_output.i > 0:
      result = entropy_file(path, 0)

      filename = shortcut_filename(os.path.basename(path))
      if result['exception'] == "":
         entropy = correct_float(result['entropy'])
         hashes = "|" + str(int(numpy.round(result['entropy'], decimals=0)) * "#").ljust(8) + "|"
      else:
         entropy = result['exception'].strip()
         hashes = ""

      print ' {:<25} {:<13} {:<10}'.format(filename, entropy, hashes)

   many_files_output.i += 1


def interpretation(entropy):
   if entropy >= 1.0 and entropy < 3.9:
      return "Low entropy. Potential for compression"
   elif entropy < 4.9:
      return "Possible plain text"
   elif entropy < 5.63:
      return "Like source code"
   elif entropy < 6.54:
      return "Poor compression/encryption"
   elif entropy < 7.00:
      return "Almost good compresion/encryption/randomness"
   elif entropy < 7.50:
      return "Good compresion/encryption/randomness"
   elif entropy < 7.99:
      return "Very good compresion/encryption/randomness"
   elif entropy <= 8.00:
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


# @profile
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

      if size > min(sys.maxsize - 100 * 1024 * 1024, 1024*1024*1024) and platform.architecture()[0] == "32bit":
         result['exception'] = "32-bit limit (1-2GB) use 64-bit python"
         return result

      mm = numpy.memmap(path, dtype='uint8', mode='r')
      while pointer < size:
         fix_last_one = False
         # CHECK BOUNDARIES
         end = pointer + chunk_size
         if end > size:
            fix_last_one = True
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

         # print "Initial temp start:" + str((temp_start, temp_end))
         if current_capacity > MAX_ONE_TIME:
            while True:
               # print "Optimized model: " + str((temp_start,temp_end))
               weights = numpy.add(numpy.bincount(mm[temp_start:temp_end], minlength=256), weights)
               (temp_start, temp_end, valid) = provide_next(temp_start, temp_end, end, MAX_ONE_TIME)
               if valid == False:
                  # print "Model end"
                  break
         else:
            # print "Normal model"
            weights = numpy.bincount(mm[pointer:end], minlength=256)

         prob = numpy.divide(weights, float(current_capacity))
         tempopy = 0.0

         for i in range(0, 256):
            if prob[i] > 0.0:
               tempopy += -prob[i] * numpy.log2(prob[i])
         # if fix_last_one:
         #   tempopy = tempopy /numpy.log2(current_capacity) * numpy.log2(chunk_size)
         result['entropy_chunks'].append(tempopy)
         result['entropy_chunks_info'].append((pointer, end - 1))
         pointer += chunk_size
      result['entropy'] = numpy.mean(result['entropy_chunks'])
      result['interpretation'] = interpretation(result['entropy'])
      # INTERPRETATION
      try:
         del mm
      except NameError:
         pass

   except Exception as e:
      result['exception'] = "Exception: " + e.message + e.__str__()
      try:
         del mm
      except NameError:
         pass

   return result


def main():
   chunk_size = 0  # AUTOMATIC
   sources = args.sources[0]
   items_number = len(sources)

   if items_number == 0:
      print("*** Please provide at least one file or directory")
      print("")
      print("Examples:")
      # TODO - REVISE!!!!!!!!!!!!!!!!!!!!!!!!
      # print("1. Fix in-place 2 files (Make sure you got a copy!):")
      # print(" " + sys.argv[0] + " AppEvent.Evt SysEvent.Evt")
      # print("")
      # print("2. Find all *.evt files in evt_dir/, copy them to fixed_copy/ and repair them:")
      # print(" " + sys.argv[0] + " --copy_to_dir=fixed_copy evt_dir")
      sys.exit(-10)

   if args.chunk:
      test_size = human2bytes(args.chunk[0])
      if test_size > 0:
         chunk_size = test_size
      else:
         print "Incorrect chunk size. Sample valid ones: 256 or 100K or 33.5M or 20G"
         sys.exit(-11)

   for path in sources:
      path = path.rstrip("/\\").rstrip('"').rstrip("'")
      if os.path.isdir(path):
         # NON-RECURSIVE
         try:
            files = os.listdir(path)

         except Exception as e:
            print("Error when listing directory: %s" % (path) + " [" + e.strerror + e.message + "]")
            continue
         for file in files:
            full_path = path + os.path.sep + file
            if os.path.isfile(full_path):
               if not hasattr(many_files_output, "i"):
                  many_files_output(full_path, False)
               many_files_output(full_path, False)
      elif os.path.isfile(path):
         only_file_output(path, chunk_size)
      else:
         print("Error: File/directory doesn't exist: " + path)


if __name__ == "__main__":
   main()
