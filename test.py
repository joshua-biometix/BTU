
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 29 22:44:23 2014

"""

import os
import sys
import getopt
import shutil
import modules.NISTutility as nu
import json
import tempfile
import base64


def main(argv):
   in_file = ''
   out_format = ''
   out_file=''
   opts=[]


   with open(sys.argv[1], 'r+b') as nist_file:
     nist_data=base64.b64encode(nist_file.read())

   json_data={}
   json_data['nist_file']=nist_data
   json_data['btu_settings']={'transform':0, 'get_images':0, 'get_features':1}
   print json.dumps(json_data)


if __name__ == "__main__":
   main(sys.argv[1:])


