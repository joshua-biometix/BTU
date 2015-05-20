# -*- coding: utf-8 -*-
"""
Created on Sun Jun 29 22:44:23 2014

@author: Joshua Abraham
@description: eft/an2 NIST image converter/re-packager using NIST NBIS binaries
        Note: To run this script use:

              python convert_NIST_finger.py -i <input_file>  -f <image_format> [-o <output_file>]

              e.g. python convert_NIST_finger.py -i file.eft  -f wsq file_new.eft
              
"""

import os
import sys
import getopt
import shutil
import modules.NISTutility as nu

#NIST binary path
nist_path="bin/"


#valid image formats for transformation
valid_image_formats=["jpg", "jpeg", "bmp", "png", "wsq", "tiff"]

    
def main(argv):
   in_file = ''
   out_format = ''
   out_file=''
   opts=[]   
   try:
      opts, args = getopt.getopt(argv,"hi:f:o:",["ifile=","ofile=","format="])
   except getopt.GetoptError:
      print 'convert_NIST_finger.py -i <inputfile> -f <format> [-o <outputfile>]'
      sys.exit(2)
   print opts   
   for opt, arg in opts:
      print arg 
      if opt == '-h':
         print 'convert_NIST_finger.py -i <inputfile> -f <format> [-o <outputfile>]'
         sys.exit(1)
      elif opt in ("-i", "--ifile"):
         in_file = arg
      elif opt in ("-f", "--format"):
         out_format = arg
      elif opt in ("-o", "--ofile"):
         out_file = arg
   print argv            
   if(not out_format in valid_image_formats):
      print("Invalid image format "+ out_format)
      sys.exit(1);
       
       
   #if(len(in_file)<4 or in_file[len(in_file)-4:]!=".eft"):
   #   print("Incorrect file format: " + in_file[len(in_file)-4:])
   #   sys.exit(1)

   if os.path.isdir(in_file) and out_file !='' and not os.path.isdir(out_file) or not os.path.isdir(in_file) and out_file !='' and os.path.isdir(out_file):
     print("Both <inputfile> and <outputfile> must be valid directories.")
     sys.exit(1)
      
   if not os.path.isfile(in_file):
      print("file '"+in_file+ "' does not exist!")
      sys.exit(1)
   convert_options={ 'include_finger_index':{1,2,3,4}   }
   nu.convertNIST(in_file, out_format, out_file, convert_options)


if __name__ == "__main__":
   try:
      opts, args = getopt.getopt(sys.argv,"hi:f:o:",["ifile=","ofile=","format="])
   except getopt.GetoptError: 
      pass    
   main(sys.argv[1:])


