# -*- coding: utf-8 -*-
"""
Created on Sun Jun 29 22:44:23 2014

@author: Joshua Abraham
@description: eft/an2 NIST image converter/re-packager using NIST NBIS binaries
        Note: To run this script use:

              python convert_NIST_finger.py -i <input_file>  -f <image_format> [-o <output_file>]

              e.g. python convert_NIST_finger.py -i file.eft  -f wsq file_tfm.eft
              
"""

import os
import sys
import getopt
import shutil
import json
import subprocess
import numpy as np
import magic
import logging
import base64

#NIST binary path
root_path=os.path.dirname(os.path.dirname(os.path.realpath(__file__)))+'/'
config_path=root_path+'Config/'
nist_path=root_path+"modules/bin/"

record_type_1_to_map={
                    "1.001":"LOGICAL RECORD LENGTH", 
                    "1.002":"VERSION NUMBER",
                    "1.003":"FILE CONTENT",
                    "1.004":"TYPE OF TRANSACTION",
                    "1.005":"DATE",
                    "1.006":"PRIORITY",
                    "1.007":"DESTINATION AGENCY IDENTIFIER",
                    "1.008":"ORIGINATING AGENCY IDENTIFIER",
                    "1.009":"TRANSACTION CONTROL NUMBER",
                    "1.010":"TRANSACTION CONTROL REFERENCE",
                    "1.011":"NATIVE SCANNING RESOLUTION",
                    "1.012":"NOMINAL TRANSMITTING RESOLUTION",
                    "1.013":"DOMAIN NAME",
                    "1.014":"GREENWICH MEAN TIME",
                    "1.015":"DIRECTORY OF CHARACTER SETS",
             }

record_type_2_to_map={
                      "2.001":"LOGICAL RECORD LENGTH", 
                      "2.002":"INFORMATION DESIGNATION CHARACTER",
}

record_type_3_to_map={
                      "3.001":"LOGICAL RECORD LENGTH",
                      "3.002":"INFORMATION DESIGNATION CHARACTER",
}




record_type_4_to_map={
                    "4.001":"RECORD HEADER", 
                    "4.002":"INFORMATION DESIGNATION CHARACTER",
                    "4.003":"IMPRESSION TYPE",
                    "4.004":"FRICTION RIDGE GENERALIZED POSITION",
                    "4.005":"IMAGE SCANNING RESOLUTION",
                    "4.006":"HORIZONTAL LINE LENGTH",
                    "4.007":"VERTICAL LINE LENGTH",
                    "4.008":"COMPRESSION ALGORITHM",
                    "4.009":"IMAGE DATA",
}


record_type_14_to_map={
                    "14.001":"LOGICAL RECORD LENGTH", 
                    "14.002":"IMAGE DESIGNATION CHARACTER",
                    "14.003":"IMPRESSION TYPE",
                    "14.004":"SOURCE AGENCY/ORI",
                    "14.005":"TENPRINT CAPTURE DATE",
                    "14.006":"HORIZONTAL LINE LENGTH",
                    "14.007":"VERTICAL LINE LENGTH",
                    "14.008":"SCALE UNITS",
                    "14.009":"HORIZONTAL PIXEL SCALE",
                    "14.010":"VERTICAL PIXEL SCALE",
                    "14.011":"COMPRESSION ALGORITHM",
                    "14.012":"BITS PER PIXEL",
                    "14.013":"FINGER POSITION",
                    "14.020":"COMMENT",
                    "14.999":"IMAGE DATA",
}



finger_position_codes={"0":"UNKNOWN", 
                    "1":"Right thumb",
                    "2":"Right index finger",
                    "3":"Right middle finger",
                    "4":"Right ring finger",
                    "5":"Right little finger",
                    "6":"Left thumb",
                    "7":"Left index finger",
                    "8":"Left middle finger",
                    "9":"Left ring finger",
                    "10":"Left little finger",
                    "11":"Plain right thumb",
                    "12":"Plain left thumb",
                    "13":"Plain right four fingers",
                    "14":"Plain left four fingers"
}


reference_replace_rules={}
field_replace_rules={}

replaced_optional_fields={}
deleted_optional_fields={}

date_refs={}

#define X-Y coordinate NIST fields

x_dim_fields=["4.006", "14.006",]
                 
y_dim_fields=["4.007", "14.007",]



def getFieldDescription(field):
        if field in record_type_1_to_map:
          return record_type_1_to_map[field]
        if field in record_type_2_to_map:
          return record_type_2_to_map[field]
        if field in record_type_4_to_map:
          return record_type_4_to_map[field]
#        field in record_type_9_to_map:
#          return record_type_9_to_map[field]
        if field in record_type_14_to_map:
          return record_type_14_to_map[field]

        return None;



def loadConfig():
        fh = open(config_path+"nist.cfg", "r")
        for line in fh.readlines():
            splitted_line = line.split('=')
            if len(splitted_line) == 2: 
 
              field = splitted_line[0].strip(' \t\n\r');
              value = splitted_line[1].strip(' \t\n\r');

              if field == "REPLACE-OPTIONAL-RECORDS":
                replaced_optional_fields[value]=1
              elif field == "DELETE-OPTIONAL-RECORDS":
                deleted_optional_fields[value]=1
              elif field == "DATE-REFS":
                 splitted_vals = value.split(',')
                 for val in splitted_vals:
                   date_refs[val]=1 
              else:
                if getFieldDescription(field) != None: 
                  field_replace_rules[field]=value
                else:
                  reference_replace_rules[field]=value

        #print "adasd "+str(field_replace_rules)
        #print "adasd "+str(reference_replace_rules)


def getMinutiae(path, finger_name):
        X, Y=0, 0
        md1, md2, mdo1, mdo2=[], [], [], []
        b1, b2, b3, b4=0, 0, 0, 0
        MIN_Q=0.2

        if(finger_name!=None): 
                fh = open(path+finger_name+".min", "r")
                line = fh.readline()
                fields = line.split(' ')
                X=float(fields[2])#/scale
                Y=float(fields[3])#/scale
                
                for i in range(3):
                        fh.readline()
                        
                orient_map_fh = open(path + finger_name+".dm", "r")
                quality_map_fh = open(path + finger_name+".qm", "r")
                hc_map_fh = open(path + finger_name+".hcm", "r")

                orient_img=[]
                quality_map=[]
                hc_map=[]

                #Get the orientation map
                i=0
                for line in orient_map_fh.readlines():
                        j=0
                        orient_img_t=[]
                        for s in line.split(' '):
                                try:
                                        orient_img_t.append(float(s)*11.25)
                                        j=j+1
                                except ValueError:
                                        continue
                        orient_img.append(orient_img_t)
                        i=i+1

                #Get the quality map
                i=0
                for line in quality_map_fh.readlines():
                        j=0
                        q_img_t=[]
                        for s in line.split(' '):
                                try:
                                        q_img_t.append(int(s))
                                        j=j+1
                                except ValueError:
                                        continue
                        quality_map.append(q_img_t)
                        i=i+1


                #Get the high curvature map
                i=0
                for line in hc_map_fh.readlines():
                        j=0
                        h_img_t=[]
                        for s in line.split(' '):
                                try:
                                        h_img_t.append(int(s))
                                        j=j+1
                                except ValueError:
                                        continue
                        hc_map.append(h_img_t)
                        i=i+1

                minutiae=[]

                lines=fh.readlines()

                ang_m_list={}
                
                #Get minutiae
                
                for line in lines:
                        line=line.replace(':',',')
                        line=line.replace(';',',')
                        fields = line.split(',')

                        m_type=fields[5].strip()
                            
                        if float(fields[4]) < MIN_Q:
                                continue
                        ang_m_list[int(fields[1])*1000 + int(fields[2])]=float(fields[3])*11.25 * float(np.pi) / 180.0
                        ## <index> <x><y><normalised x>, <normalised y>, direction,  quality, type                                      
                        minutiae.append({"index": int(fields[0]), "x": int(fields[1]), "y":Y-int(fields[2]), "theta":float(fields[3])*11.25*np.pi/180, "quality":float(fields[4]), "type":m_type })
                      
#                fingerprints.append([f[0:len(f)-4], minutiae,  neighbours, [core_x,  core_y], [ncore_x,  ncore_y],  orients, radii,[float(core_x)/dimX, float(core_y)/dimY,core_x, core_y]]     )

                orient_map_fh.close()
                quality_map_fh.close()
                hc_map_fh.close()
                fh.close()
                
        return minutiae #,  dimX,  dimY



#Returns the number of non Type 1 records in the fmt file fmt_file
def getNumberOfRecords(fmt_file):
   for line in fmt_file:
       splitLine = line.split('=')
       ref_num=(splitLine[0])[:splitLine[0].find("[")-1]
       field_num=((splitLine[0])[splitLine[0].find("["):]).replace('[','').replace(']','').strip(' \t\n\r')
       field_val=(splitLine[1])[:len(splitLine[1])-2]
       new_val=(splitLine[1])
       if field_num == "1.003":
          if ref_num == "1.3.1.2":
             try:
                  number_of_records=int(field_val);
#                  print("Number of RECORDS = "+field_val);
                  return number_of_records;
             except:
                  #print("Error in Number of RECORDS field");
                  return -1;
   return 0


#Returns a map of record type counts recorded in the type 2 record fields in the fmt file 'fmt_file'
def getRecordCounts(fmt_file):
   res={}
   cur_rec_type=-1;
   for line in fmt_file:
       splitLine = line.split('=')
       ref_num=(splitLine[0])[:splitLine[0].find("[")-1]
       field_num=((splitLine[0])[splitLine[0].find("["):]).replace('[','').replace(']','').strip(' \t\n\r')
       field_val=(splitLine[1])[:len(splitLine[1])-2]
       new_val=(splitLine[1])
       if field_num == "1.003":
          if ref_num == "1.3.1.2" or ref_num == "1.3.1.1":
             continue
          else:
             if cur_rec_type == -1:
                try:
                    cur_rec_type=int(field_val);
                    #print("Current record type is "+field_val);
                except:
                    #print("Error in retrieving record type");
                    pass 
             else:
                if str(cur_rec_type) in res:
                    res[str(cur_rec_type)]+=1
                else:
                    res[str(cur_rec_type)]=1
                cur_rec_type=-1;
   return res


#Returns the new field value
def getRefVal(fmt_file, x_ref_num):
   fmt_file.seek(0)
   for line in fmt_file:
       splitLine = line.split('=')
       ref_num=(splitLine[0])[:splitLine[0].find("[")-1]
       rec_num=((splitLine[0])[splitLine[0].find("["):]).replace('[','').replace(']','').strip(' \t\n\r')
       field_val=(splitLine[1])[:len(splitLine[1])-2]
       orig_val = field_val

       if ref_num == x_ref_num:
          #print "YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY"
          #print "Field Record is "+rec_num
          #print "Reference is "+ref_num
          #print "val is "+field_val

          #print "Reference keys " +str(reference_replace_rules.keys())
          #print "Field keys " +str(field_replace_rules.keys())
          if ref_num in date_refs.keys():
            field_val="20000101"
          elif rec_num in reference_replace_rules.keys():
            #print "REF NUM IN REPLACE RULES "+ref_num
            if reference_replace_rules[rec_num].strip(' \t\n\r')!="":
              field_val=reference_replace_rules[rec_num]

          elif ref_num in field_replace_rules.keys():
            #print "FIELD NUM IN REPLACE RULES "+field_num
            if field_replace_rules[ref_num].strip(' \t\n\r')!="":
              field_val=field_replace_rules[ref_num]
          else:
            field_val="X" * len(field_val)
          if field_val == orig_val:
            return None
          return field_val
   return ""




def convertNIST(in_source, image_format, out_source, convert_options={}):
   loadConfig()
   json_result={}
   sys_logger = logging.getLogger('btu_application')
   sys_logger.setLevel(logging.DEBUG)
   # create file handler which logs even debug messages
   fh = logging.FileHandler('biometric_transformation.log')
   fh.setLevel(logging.DEBUG)

   ch = logging.StreamHandler()
   ch.setLevel(logging.ERROR)
   # create formatter and add it to the handlers
   formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
   ch.setFormatter(formatter)
   fh.setFormatter(formatter)
   # add the handlers to logger
   sys_logger.addHandler(ch)
   sys_logger.addHandler(fh)


   if in_source == ".":
     in_source  = os.getcwd()+"/"
   if out_source == "." or out_source == '':
     out_source  = os.getcwd()+"/"

   if in_source[0] != '/':
     in_source  = os.getcwd()+"/"+in_source
   if out_source[0] != '/':
     out_source = os.getcwd()+"/"+out_source


   if not os.path.isfile(in_source) and not os.path.isdir(in_source):
      sys_logger.debug("file '"+in_source+ "' does not exist!")
      json_result['result']="file '"+in_source+ "' does not exist!"
      return json_result

   res_logger = logging.getLogger('BTU_RESULT')
   if os.path.isdir(in_source): 
     fh = logging.FileHandler( os.path.abspath(out_source)+ '/results.log', mode='w')
   else:
     fh = logging.FileHandler( 'results.log', mode='w')
   fh.setLevel(logging.INFO)
   ch = logging.StreamHandler()
   ch.setLevel(logging.INFO)
   # create formatter and add it to the handlers
   formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
   ch.setFormatter(formatter)
   fh.setFormatter(formatter)
   # add the handlers to logger
   res_logger.addHandler(ch)
   res_logger.addHandler(fh)

#   in_file  = os.getcwd()+"/"+in_file
#   out_file = os.getcwd()+"/"+out_file
#   if os.path.isdir(in_file) and out_file !='' and not os.path.isdir(out_file) or not os.path.isdir(in_file) and out_file !='' and os.path.isdir(out_file):
#     print("Both <inputfile> and <outputfile> must be valid directories.")
#     sys.exit(1)
   NFIQs={}
   minutiae={}
   if not os.path.isfile(in_source) and not os.path.isdir(in_source):
      json_result['result']="file '"+in_source+ "' does not exist!"
      sys_logger.error("In source '"+in_source+ "' does not exist!")
      return json_result

   convert_options['sys_logger']=sys_logger;
   convert_options['result_logger']=res_logger;
   nist_files=[]
   if os.path.isdir(in_source):
      nist_files += [each for each in os.listdir(in_source) if each.endswith('.eft') or each.endswith('an2') or each.endswith('nist') ]
      for nist_file in nist_files:
        res, NFIQs, minutiae, images=performConvert(in_source+'/'+nist_file, image_format, out_source+'/'+nist_file[max(0, nist_file.rfind('/')+1):len(nist_file)-4]+"_tfm"+nist_file[len(nist_file)-4:], convert_options)
        if res == None:
           res_logger.warn('Transformation of NIST file '+nist_file+ ' UNSUCCESSFUL\r')
        else:
           res_logger.warn('Transformation of NIST file '+nist_file+ ' COMPLETED SUCCESSFULLY and saved as' + res+'\r')
            
   elif os.path.isfile(in_source):
      if os.path.isdir(out_source):
        out_source+=in_source[max(0, in_source.rfind('/')+1):len(in_source)-4]+"_tfm"+in_source[len(in_source)-4:]
      res, NFIQs, minutiae, images=performConvert(in_source, image_format, out_source, convert_options)
      if res == None:
         res_logger.warn('Transformation of NIST file '+in_source+ ' UNSUCCESSFUL\r\n')
         json_result['result']='Transformation of NIST file '+in_source+ ' UNSUCCESSFUL\r\n'
      else:
         res_logger.warn('Transformation of NIST file '+in_source+ ' COMPLETED SUCCESSFULLY and saved as ' + res+"\r")
         json_result['result']='Transformation of NIST file '+in_source+ ' COMPLETED SUCCESSFULLY and saved as ' + res+"\r"

   json_result["NFIQ"]=NFIQs
   json_result["minutiae"]=minutiae
   json_result["images"]=images
   json_result["transformed_file"]=res
   return json_result



def performConvert(in_file, image_format, out_file, convert_options={}):
   sys_logger=convert_options['sys_logger'];
   res_logger=convert_options['result_logger'];

   sys_logger.debug("Input file is "+ in_file+" Image format is "+ image_format +" Output file is "+ out_file)
   in_file_name=in_file[max(0, in_file.rfind('/')+1):len(in_file)-4]

   dir_path=in_file[0:len(in_file)-4]
   if os.path.exists(dir_path):
      sys_logger.debug("Attempting to clean/remove directory "+dir_path)
      shutil.rmtree(dir_path)   
      try:
          #os.system("rm *.tmp")

          with open(os.devnull, 'wb') as devnull:
            proc = subprocess.call(["rm", '*.tmp'], stdout=devnull, stderr=devnull)
          os.removedirs(dir_path)
          pass
      except:
          pass

   #Create output directory if does not exist (directory removal just attempted so should not exist unless permissions issue)
   if not os.path.exists(dir_path):
      sys_logger.debug("Creating directory "+dir_path)
      os.makedirs(dir_path)
   else:   
      sys_logger.error("Directory "+dir_path+" already exists and cannot be removed")
      return None, None, None, None

   os.chdir(dir_path) 

   #for ref_num in reference_replace_rules.keys():
   #  value = reference_replace_rules[ref_num]
   #  value = getRefVal(fmt_file, ref_num)
   #  print(nist_path+"an2ktool -substitute "+ref_num + " "+str(value)+" " +in_file+ " " + in_file)
   #  os.system(nist_path+"an2ktool -delete "+ref_num + " " +in_file+ " " + in_file )
    # break
      
   #Produce NIST formatted field and raw image output   
#   sys_logger.debug("Running "+nist_path+"an2k2txt "+in_file+ " "+dir_path+"/"+in_file_name+".fmt")
   #print("Running "+nist_path+"an2k2txt "+in_file+ " "+dir_path+"/"+in_file_name+".fmt")

   with open(os.devnull, 'wb') as devnull:
      proc = subprocess.call([nist_path+"an2k2txt", in_file ,dir_path+"/"+in_file_name+".fmt"], stdout=devnull, stderr=devnull)

#      proc = subprocess.Popen([nist_path+"an2k2txt", in_file ,dir_path+"/"+in_file_name+".fmt"], stdout=devnull, stderr=devnull)
#      o, e=proc.communicate()
      #print o
      #print e
#      proc = subprocess.check_call([nist_path+"an2k2txt", in_file +" "+dir_path+"/"+in_file_name+".fmt "], stdout=devnull, stderr=devnull)


#   if (os.system(nist_path+"an2k2txt "+in_file+ " "+dir_path+"/"+in_file_name+".fmt" + " > /dev/null 2>&1")<>0):
#     sys_logger.error("fail - probably can't find %s"%nist_path+"an2k2txt or CORRUPTED NIST FILE...")   
#     shutil.rmtree(dir_path)   
#     return None

   sys_logger.debug('Transforming NIST file '+in_file)   
   
   records = {}
   header = {}
   NFIQs={}
   images={}
   minutiae={}
   full_records = [] 
   full_values = [] 
   fingers={}
   img_x=-1
   img_y=-1

   type_14=-1;
   finger_index=-1
   compression_algorithm=0

   finger_dpi="" #"4.005":"IMAGE SCANNING RESOLUTION",                    "14.012":"BITS PER PIXEL",
   finger_source_agency="" #      "14.004":"SOURCE AGENCY/ORI",
   finger_capture_date="" #        "14.005":"TENPRINT CAPTURE DATE",
   finger_comment=""      #           "14.020":"COMMENT",
   idc=""                # "14.002":"IMAGE DESIGNATION CHARACTER",
   
   transformed=0
   #Open txt field file and parse fields/records + update record values
   with open(dir_path+"/"+in_file_name+".fmt", 'rw') as fmt_file:

        for line in fmt_file:
            splitLine = line.split('=')

            ref_num=(splitLine[0])[:splitLine[0].find("[")-1]
            field_num=((splitLine[0])[splitLine[0].find("["):]).replace('[','').replace(']','').strip(' \t\n\r')
            field_val=(splitLine[1])[:len(splitLine[1])-2]
            new_val=(splitLine[1])

            value = getRefVal(fmt_file, ref_num)
            if value == None:
              continue;

            if ref_num in reference_replace_rules:
               #value = reference_replace_rules[ref_num]
               print 'ZZZZZDDDDDDDDDDDDDDDDDD' 
               if transformed == 0:
                 with open(os.devnull, 'wb') as devnull:
                   proc = subprocess.call([nist_path+"an2ktool", '-substitute' ,ref_num,str(value),in_file,out_file], stdout=devnull, stderr=devnull)
               #  os.system(nist_path+"an2ktool -substitute "+ref_num + " "+str(value)+" " +in_file+ " " + out_file)
               else: 
                 with open(os.devnull, 'wb') as devnull:
                   proc = subprocess.call([nist_path+"an2ktool", '-substitute' ,ref_num,str(value),out_file,out_file], stdout=devnull, stderr=devnull)
               #  os.system(nist_path+"an2ktool -substitute "+ref_num + " "+str(value)+" " +out_file+ " " + out_file)
               res_logger.warn('Replacing field '+field_num +" value "+field_val + " with " +value +"\r") 
               #print "ZZZZZZ"
               transformed=1 

            elif ref_num[0] in replaced_optional_fields and field_num not in record_type_2_to_map.keys():
               if transformed == 0:
                 #os.system(nist_path+"an2ktool -substitute "+ref_num + " "+str(value)+" " +in_file+ " " + out_file)
                 with open(os.devnull, 'wb') as devnull:
                   proc = subprocess.call([nist_path+"an2ktool", '-substitute' ,ref_num,str(value),in_file,out_file], stdout=devnull, stderr=devnull)
               else:
                 #os.system(nist_path+"an2ktool -substitute "+ref_num + " "+str(value)+" " +out_file+ " " + out_file)
                 with open(os.devnull, 'wb') as devnull:
                   proc = subprocess.call([nist_path+"an2ktool", '-substitute' ,ref_num,str(value),out_file,out_file], stdout=devnull, stderr=devnull)


               res_logger.warn('Replacing field '+field_num +" value "+field_val + " with " +value +"\r")
               transformed=1

            elif ref_num[0] in deleted_optional_fields and field_num not in record_type_2_to_map.keys():
               if transformed == 0:
                 with open(os.devnull, 'wb') as devnull:
                   proc = subprocess.call([nist_path+"an2ktool", '-delete' ,ref_num,in_file,out_file], stdout=devnull, stderr=devnull)
#                 os.system(nist_path+"an2ktool -delete "+ref_num + " " +in_file+ " " + out_file)
               else:
                 #os.system(nist_path+"an2ktool -delete "+ref_num + " " +out_file+ " " + out_file)
                 with open(os.devnull, 'wb') as devnull:
                   proc = subprocess.call([nist_path+"an2ktool", '-delete' ,ref_num,out_file,out_file], stdout=devnull, stderr=devnull)

               res_logger.warn('Replacing field '+field_num +" value "+field_val + " with " +value +"\r")
               transformed=1



   if transformed==0:
     os.system("cp "+ in_file+ " " + out_file)
     res_logger.warn("No fields found for transformation\r") 


   #Open txt field file and get record counts/types
   with open(dir_path+"/"+in_file_name+".fmt", 'r') as fmt_file:
#        fmt_file_copy=fmt_file
        number_of_records = getNumberOfRecords(fmt_file);
        fmt_file.seek(0)
        nist_record_count = getRecordCounts(fmt_file);

        if number_of_records == -1 or len(nist_record_count) == 0:
          sys_logger.error("NIST record count field extraction error.")   
          shutil.rmtree(dir_path)   
          return None, None, None, None


        if "14" in nist_record_count:
           type_14=1
        else:
           type_14=0

   fmt_file.close()


   os.chdir(root_path)

   number_of_fingers_to_include=100

   if "include_finger_index" in convert_options and finger_index not in convert_options['include_finger_index']:
     number_of_fingers_to_include=len( convert_options['include_finger_index'])
     sys_logger.debug("NUMBER OF FINGERS TO INCLUDE "+str(len(convert_options['include_finger_index'])))
   converted_fingers = 0

   #Open txt field file and parse fields/records + update record values
   with open(dir_path+"/"+in_file_name+".fmt", 'rw') as fmt_file:

        for line in fmt_file:
            splitLine = line.split('=')
            
            ref_num=(splitLine[0])[:splitLine[0].find("[")-1]              
            field_num=((splitLine[0])[splitLine[0].find("["):]).replace('[','').replace(']','').strip(' \t\n\r')              
            field_val=(splitLine[1])[:len(splitLine[1])-2]           
            new_val=(splitLine[1])

            if field_num == "1.003":
               if field_val in nist_record_count:
                  cur_rec_type=field_val
                  nist_record_count[field_val]-=1
                  #check to see if the current record type is for fingers 
                  if cur_rec_type in ["4", "9", "14"]: 
                    number_of_fingers_to_include-=1
            else:
               cur_rec_type=""
            
            if (field_num in ["1.003", "4.001", "4.002", "4.003"]  or (float(field_num) > 14 and  float(field_num)<14.013))  and cur_rec_type in nist_record_count and number_of_fingers_to_include < 0:
               continue

            if(field_num in record_type_1_to_map):
               header[record_type_1_to_map[field_num]]=field_val 

            sys_logger.debug("Field number is "+field_num +" Reference number is "+ref_num +" field value is "+field_val)

            if(field_num in x_dim_fields):
               img_x=int(field_val)
               img_y=-1
            
            if(field_num in y_dim_fields):
               img_y=int(field_val)
            new_val=splitLine[1:][0]

  #          if ref_num in reference_replace_rules:
       #       print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"
       #       print ref_num
       #       print new_val
       #       new_val=new_val.replace(field_val, "x" * len(field_val))  
       #       print new_val
              #new_val = reference_replace_rules[ref_num]+(splitLine[1])[len(splitLine[1])-2:]

#            if field_num in field_replace_rules:
#              new_val = field_replace_rules[field_num]+(splitLine[1])[len(splitLine[1])-2:]

            if(field_num in ("4.005","14.012")):
               finger_dpi=field_val
               
            if(field_num in ("14.002")):
               idc=field_val 
            if(field_num in ("14.004")):
               finger_source_agency=field_val
            if(field_num in ("14.005")):
               finger_capture_date=field_val
            if(field_num in ("14.020")):
               finger_comment=field_val

            
            if (field_num=="14.013" and type_14==1 or field_num=="4.004" and type_14==0) and field_val!="255":
               finger_index=int(field_val  )
               sys_logger.debug("Finger INDEX is "+str(finger_index))

            if finger_index != -1 and "include_finger_index" in convert_options and finger_index not in convert_options['include_finger_index']:
              sys_logger.debug("SKIPPING index "+str(finger_index)+" " +str(convert_options))
              continue

            if field_num=="4.008" or field_num=="14.011":   
               try: 
                   compression_algorithm=int(field_val  )              
               except:
                   pass
            
            if(field_num=="4.009" or field_num=="14.999"):#.tmp" in splitLine[1:][0]) :
               sys_logger.debug("Found image file "+splitLine[1:][0])
               splitLine[1:][0]=(splitLine[1:][0]).replace(".tmp", "."+image_format)
               new_val=(splitLine[1:][0]).replace(".tmp", "."+image_format)
               if(img_x!=-1 and img_y!=-1) and image_format!="tmp":
                  if compression_algorithm==0: 
                     pass 
                  elif compression_algorithm==1:   
                                 #dwsq raw fld_8_9.tmp -raw
                     sys_logger.debug(nist_path+"dwsq tmp "+ field_val + " -raw " )   
                     #os.system(nist_path+"dwsq tmp "+ field_val + " -raw " )   

                     with open(os.devnull, 'wb') as devnull:
                       proc = subprocess.call([nist_path+"dwsq", 'tmp' ,field_val,'-raw'], stdout=devnull, stderr=devnull)


                  m=magic.open(magic.MAGIC_MIME)
                  m.load()
#                  print field_val
                  img_type=m.file(dir_path+"/"+field_val)#, mime=True)
                  sys_logger.debug("IMAGE TYPE IS "+str(img_type))


                  if "application/octet-stream" in img_type:   
                    #print("rawtopgm "+str(img_x)+ " "+str(img_y) + " "+ dir_path+'/'+field_val + " > " + field_val[0:len(field_val)-3]+"pgm")   
#                    with open(os.devnull, 'wb') as devnull:
#                       proc = subprocess.call(["rawtopgm", str(img_x), str(img_y), dir_path+'/'+field_val,'> '+ field_val[0:len(field_val)-3]+"pgm"], stdout=devnull, stderr=devnull)

                    os.system("rawtopgm "+str(img_x)+ " "+str(img_y) +" "+ dir_path+'/'+field_val + " > " + field_val[0:len(field_val)-3]+"pgm")   
                    #print("convert -quality 100 "+field_val[0:len(field_val)-3]+"pgm"+ " " + field_val[0:len(field_val)-3]+"jpg")
                    os.system("convert -quality 100 "+field_val[0:len(field_val)-3]+"pgm"+ " " + field_val[0:len(field_val)-3]+"jpg")
                    os.system("convert -quality 100 "+field_val[0:len(field_val)-3]+"pgm"+ " " + field_val[0:len(field_val)-3]+image_format)
                  elif "image/tiff" in img_type or "image/png" in img_type or "image/x-portable-greymap" in img_type:
                    #print("convert -quality 100  "+ dir_path+'/'+field_val + " " + field_val[0:len(field_val)-3]+"jpg")
                    os.system("convert -quality 100  "+ dir_path+'/'+field_val + " " + field_val[0:len(field_val)-3]+"jpg")
                    os.system("convert -quality 100  "+ dir_path+'/'+field_val + " " + field_val[0:len(field_val)-3]+image_format)
                  elif "image/jpeg" in img_type or "image/jpg" in img_type:
                    os.system("mv "+field_val + " " + field_val[0:len(field_val)-3]+"jpg")
                  else:
                    sys_logger.error("Unsupported image type for file "+field_val)
                    return None, None, None, None
                  if 'get_images' in convert_options.keys() and convert_options['get_images']==1:
                    with open(field_val[0:len(field_val)-3]+"jpg", "rb") as image_file:
                      encoded_image=base64.b64encode(image_file.read())

                    images[field_val]=encoded_image


                  if 'get_features' in convert_options.keys() and convert_options['get_features']==1:  
               
                    #Extract minutiae and orientation flow information
                    os.system(nist_path+"mindtct  -b  -m1 "+field_val[0:len(field_val)-3]+"jpg" +" "+field_val[0:len(field_val)-4]) 
                    minutiae[field_val[0:len(field_val)-4]]=getMinutiae("", field_val[0:len(field_val)-4])

                    #Extract NFIQ score
                    proc = subprocess.Popen([nist_path+"nfiq -d "+ field_val[0:len(field_val)-3]+"jpg" ], stdout=subprocess.PIPE, shell=True)
                    (nfiq, err) = proc.communicate()
                  
                    #valid and unused finger index: so add NFIQ dictionary
                    if finger_index > -1 and finger_index not in NFIQs.keys():
                       #print("NFIQ is "+nfiq)
                       #print("Finger index is "+str(finger_index))
                       NFIQs[finger_index]=int(nfiq[0:len(nfiq)-1])
   
                  record_type="Unknown"
                  if type_14==1:
                     record_type="14"
                  elif type_14==0:
                     record_type="4"
                     
                  fingers[finger_index]={"finger":finger_position_codes[str(finger_index)], "x":img_x, 
                                         "y":img_y, "compressed":compression_algorithm, 
                                         "source agency":finger_source_agency, "capture date":finger_capture_date,
                                         "comment":finger_comment, "dpi":finger_dpi, #"minutiae":getMinutiae("", field_val[0:len(field_val)-4]), "NFIQ":NFIQs[finger_index], "IDC":idc, 
                                        "Record type":record_type, "image":field_val[0:len(field_val)-3]+"jpg"}     
                  converted_fingers+=1                       
                                         
                  finger_dpi="" #"4.005":"IMAGE SCANNING RESOLUTION",                    "14.012":"BITS PER PIXEL",
                  finger_source_agency="" #      "14.004":"SOURCE AGENCY/ORI",
                  finger_capture_date="" #        "14.005":"TENPRINT CAPTURE DATE",
                  finger_comment=""     
                  idc=""            #     "14.002":"IMAGE DESIGNATION CHARACTER",
                  img_x=-1
                  img_y=-1

               
            records[ref_num] = {"field":field_num, "value":new_val[:len(new_val)-2]}
            full_records.append(splitLine[0])
            
            #Test to see if Type 4 or 14 record
            if field_num=="1.003":
               if field_val=="14":
                  type_14=1
 #                 print("Type 14 record detected") 
               elif field_val=="4":
                  type_14=0
 #                 print("Type 4 record detected") 


            full_values.append(new_val)

        fmt_file.close()

   if "include_finger_index" in convert_options and converted_fingers < len( convert_options['include_finger_index']):
     sys_logger.error("Not enough fingers converted: converted="+str(converted_fingers) + " versus the required " + str(len( convert_options['include_finger_index'])))
     shutil.rmtree(dir_path)   
     return None, None, None, None
    
   #TODO: JA fix this    
   with open(dir_path+"/"+in_file_name+".new.fmt", 'w') as fmt_out_file:
         for i in range(0,len(full_records)):
            fmt_out_file.write(full_records[i]+"="+full_values[i])
  
   if 'transform' in convert_options.keys() and convert_options['transform']==1:
     if out_file !='':         
       with open(os.devnull, 'wb') as devnull:
         proc = subprocess.call([nist_path+"txt2an2k", dir_path+"/"+in_file_name+".new.fmt" ,out_file], stdout=devnull, stderr=devnull)

       #os.system(nist_path+"txt2an2k "+dir_path+"/"+in_file_name+".new.fmt" +" "+out_file   ) 
       sys_logger.debug(nist_path+"txt2an2k "+dir_path+"/"+in_file_name+".new.fmt" +" "+out_file)
     else: 
       with open(os.devnull, 'wb') as devnull:
         proc = subprocess.call([nist_path+"txt2an2k", dir_path+"/"+in_file_name+".new.fmt" ,"new.eft"], stdout=devnull, stderr=devnull)
  
#      os.system(nist_path+"txt2an2k "+dir_path+"/"+in_file_name+".new.fmt" +" "+"new.eft" ) 
       sys_logger.debug(nist_path+"txt2an2k "+dir_path+"/"+in_file_name+".new.fmt" +" "+"new.eft")
       out_file="new.eft";

 
#   json_dict={"Header":header, "NFIQ":NFIQs, "Records": records, "Minutiae": minutiae, "Type 1 Def":record_type_1_to_map, 
#              "Type 2 Def":record_type_1_to_map, "Type 14 Def":record_type_1_to_map,
#              "Type 14 Def":record_type_1_to_map}
   json_dict={"Header":header, "Finger Data":fingers}

   with open(dir_path + '/'+'json.txt', 'w') as outfile:
        json.dump(json_dict, outfile)
   
   os.chdir(root_path) 
   shutil.rmtree(dir_path)   

   out_file_data=None
   if 'transform' in convert_options.keys() and convert_options['transform']==1:
     with open(out_file, "rb") as o_file:
       out_file_data=base64.b64encode(o_file.read())
   return out_file_data, NFIQs, minutiae, images 


#valid image formats for transformation
valid_image_formats=["jpg", "jpeg", "bmp", "png", "wsq", "tiff", "tmp"]

    
