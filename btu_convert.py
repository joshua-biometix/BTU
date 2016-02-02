# -*- coding: utf-8 -*-
"""
Created on Sun Jun 29 22:44:23 2014

@author: Joshua Abraham
@description: eft/an2 NIST image converter/re-packager using NIST NBIS binaries
        Note: To run this script use:

              python btu_convert.py -i <input_file>  -f <image_format> [-o <output_file>]

              e.g. python btu_convert.py -i file.eft  -f wsq file_new.eft
              
"""

import os
import sys
import getopt
import shutil
import modules.NISTutility as nu
import json
import tempfile
import base64

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
     with open(sys.argv[1]) as json_settings_file:
       json_settings=json.load(json_settings_file)
   except:
     sys.exit(1)

   
   in_file_data = base64.b64decode(json_settings['nist_file'])
   in_file=tempfile.NamedTemporaryFile(delete=False) 
   try:
     in_file.write(in_file_data)
   except:
     in_file.close()
     os.unlink(in_file.name)
     sys.exit(1)


   #Modes: get_features, get_images, get
   convert_options=json_settings['btu_settings']
   out_file=tempfile.NamedTemporaryFile(delete=False)

   in_file.close()
   out_file.close()
   result=nu.convertNIST(in_file.name, out_format, out_file.name, convert_options)
   print json.dumps(result)
   os.unlink(in_file.name)
   os.unlink(out_file.name)


if __name__ == "__main__":
   try:
      opts, args = getopt.getopt(sys.argv,"hi:f:o:",["ifile=","ofile=","format="])
   except getopt.GetoptError: 
      pass    
   main(sys.argv[1:])


