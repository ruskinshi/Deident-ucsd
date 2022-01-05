#!/usr/bin/env python

'''
This is the user interface to the Cardiac Atlas Project's Deidentification
software.  It it currently being written with the assumption that it will
be used on Windows only. 
'''

import sys
import re
import copy
import os
from datetime import datetime
import parselist
import time
import dicom
import pydicom
import cProfile
import batch_helper
import utils
import shutil
from itertools import groupby
from operator import itemgetter
from processdicom import ProcessDicom
from PySide import QtCore, QtGui
from random import randint
import pandas as pd
from pandas import ExcelWriter
from pandas import ExcelFile

class MainCanvas(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.history = []
        self.numPages = 0

        self.setWindowTitle(self.tr("CAP Batch Deidentification Interface"))
        
        self.cancel_button = QtGui.QPushButton(self.tr("Exit"))
        self.finish_button = QtGui.QPushButton(self.tr("&Deidentify"))
        self.help_button = QtGui.QPushButton(self.tr("Help"))
    
        button_layout = QtGui.QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(self.help_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.finish_button)
   
    
        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.addLayout(button_layout)
        self.setLayout(self.main_layout)

        # Show the features
        self.features = Features(self)
        self.main_layout.insertWidget(0, self.features)
        self.features.show()
        self.features.setFocus()

        ######  CONNECTIONS  ######   
        self.connect(self.cancel_button, QtCore.SIGNAL("clicked()"), self, QtCore.SLOT("reject()"))
        self.connect(self.finish_button, QtCore.SIGNAL("clicked()"), self.features.accept)

        #### SIZE ####
        self.setGeometry(3,30,400,100)
        self.resize(600,250)
        
        

class DisplayMessage(QtGui.QDialog):
    def __init__(self, parent=None, message=None):
        QtGui.QDialog.__init__(self, parent)

        self.setWindowTitle(self.tr("Display a long message"))
        
        self.exit_button = QtGui.QPushButton(self.tr("Exit"))
    
        button_layout = QtGui.QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(self.exit_button)
    
        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.addLayout(button_layout)
        self.setLayout(self.main_layout)

        # Show the message
        #QtGui.QPlainTextEdit(message)
        msg_area = QtGui.QTextBrowser()
        msg_area.setPlainText(self.tr(message))        
        self.main_layout.insertWidget(0, msg_area)
        msg_area.show()
        msg_area.setFocus()

        ######  CONNECTIONS  ######
        self.connect(self.exit_button, QtCore.SIGNAL("clicked()"), self, QtCore.SLOT("reject()"))

class Features(QtGui.QWidget):
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # init some variables
        self.setup()
         
        # Show some output in the console window
        print("Running Deidentification Interface")

        self.top_label = QtGui.QLabel(self.tr("<center>"
                                             "<p>This will deidentify the Dicom images found "
                                             "in all subdirectories of the folder specified.</center>"))

        self.top_label.setWordWrap(False)
        frameStyle = QtGui.QFrame.Sunken | QtGui.QFrame.Panel   

        # Specify the input for the existing dicom images
        self.existing_directory_label = QtGui.QLabel()
        self.existing_directory_label.setFrameStyle(frameStyle)
        self.existing_directory_label.setText(self.default_dir)
        self.existing_directory_button = QtGui.QPushButton(self.tr("Set Folder Containing Subdirectories with Identified Existing Original DICOM Files"))
        
    
        # Specify the output for the deidentified images
        self.new_directory_label = QtGui.QLabel()
        self.new_directory_label.setFrameStyle(frameStyle)
        self.new_directory_label.setText(self.output_dir)
        self.new_directory_button = QtGui.QPushButton(self.tr("Set Folder for Output Structure"))

        #New Generate Random Identifier Button
        self.random_number_button = QtGui.QPushButton(self.tr("Generate new Identifiers (Optional)"))

        # Specify how many/which images to de-ident
        self.num_images_label = QtGui.QLabel()
        self.set_which_images_label(self.get_num_images())
        self.num_images_line_edit = QtGui.QLineEdit()
        self.num_images_label.setBuddy(self.num_images_line_edit)    

        # Set the number of images to deident, default is all
        # Keep it read-only until we know how many images exist
        if self.existing_directory_label.text() == '':
            self.num_images_line_edit.setReadOnly(True)
        else:
            self.num_images_line_edit.setReadOnly(False)

        self.num_images = QtGui.QLabel()
            

        # Specify the unique identifier to be used by the deident software 
        self.user_id_label = QtGui.QLabel()
        self.user_id_label.setText("                                                                        CHD ID Generated: ")
        self.user_id_line_edit = QtGui.QLabel()
        self.user_id_line_edit.setFrameStyle(frameStyle)
        self.user_id_line_edit.setText('')
        #self.user_id_label.setBuddy(self.user_id_line_edit)
        # Allow the user to be able to specify the memory requirements
        #self.memory_label = QtGui.QLabel()
        #self.memory_label.setText("Enter memory required\n(Ex: 800m is 800 MB)")
        #self.memory_line_edit = QtGui.QLineEdit()
        #self.memory_label.setBuddy(self.memory_line_edit)         
        # Set the default value
        #self.memory_line_edit.setText('800m')

        #self.deident_single = QtGui.QRadioButton('Deidentify Single Patient')
        #self.deident_batch = QtGui.QRadioButton('Deidentify Batch')
        

        # Connect everything to their methods
        self.connect(self.existing_directory_button, QtCore.SIGNAL("clicked()"), self.set_existing_directory)
        self.connect(self.new_directory_button, QtCore.SIGNAL("clicked()"), self.set_new_directory)
        #self.connect(self.deident_single, QtCore.SIGNAL("clicked()"), self.btnstate)
        #self.connect(self.deident_batch, QtCore.SIGNAL("clicked()"), self.btnstate)

        self.connect(self.random_number_button,QtCore.SIGNAL("clicked()"),self.generate_random_number)
        
        layout = QtGui.QGridLayout()
        layout.addWidget(self.top_label, 0, 0, 1, 2)
        layout.setRowMinimumHeight(1, 10)
        layout.addWidget(self.existing_directory_label, 2, 1)
        layout.addWidget(self.existing_directory_button, 2, 0)
        layout.addWidget(self.new_directory_label, 3, 1)
        layout.addWidget(self.new_directory_button, 3, 0)
        layout.addWidget(self.num_images_label, 5, 0)
        layout.addWidget(self.num_images_line_edit, 5, 1, 1, 2)
        layout.addWidget(self.user_id_line_edit, 4, 1)
        layout.addWidget(self.user_id_label, 4, 0)
        layout.addWidget(self.num_images,2,2)
        #layout.addWidget(self.memory_label, 6, 0)
        #layout.addWidget(self.memory_line_edit, 6, 1, 1, 2)

        self.num_images_label.setVisible(False)
        self.num_images_line_edit.hide()
        #self.deident_single.setChecked(True)
        layout.addWidget(self.random_number_button,0,2)
        layout.setRowStretch(1, 1)
        self.setLayout(layout)

    def setup(self):
        '''
        Initialize some variables
        '''
        self.MESSAGE_LIMIT = 2500
        self.num_existing_images = 0
        self.existing_file_names = ''
        self.output_directory = ''
     

        # Very Windows specific
        # Setting the default directoy when opening our file browser
        # otherwise, it starts from where ever the source files
        # are installed
        self.default_dir = os.path.join(os.environ['SYSTEMDRIVE'] + os.path.sep,
            "Users", 
            os.environ['USERNAME'],
            "Desktop")
        if os.path.exists('init.txt'):
            with open('init.txt','a+') as f:
                line = f.readline()
                self.output_dir = (line)
        else:
            self.output_dir = ''
        
    def btnstate(self):
        #if self.deident_single.isChecked():
        #    self.random_number_button.setVisible(True)
        #    self.user_id_line_edit.show()
        #    self.user_id_label.show()
        #    self.new_directory_button.setText('Set Folder for Output Structure')
        #    self.existing_directory_button.setText('Set Folder Containing Identified Existing Original DICOM Files')
        #     
        
        self.random_number_button.setVisible(True)
        self.user_id_line_edit.hide()
        self.user_id_label.hide()
        self.new_directory_button.setText('Set Folder for Output Structure')
        self.existing_directory_button.setText('Set Directory Containing All Patient Folders')
        
    #Generates random identifiers to give to other hospitals, and stores in the second sheet.
    def generate_random_number(self):
        num,msgBox = QtGui.QInputDialog.getInt(self,"integer input dialog","Enter Number of Patient Identifiers to Create")        
        
        if num >= 0:
            try:
                xls = pd.ExcelFile('CAP Patient list template.xlsx')
                df1 = pd.read_excel(xls,'Sheet1',index=False)
                df2 = pd.read_excel(xls,'Sheet2',index = False)
            except IOError:
                utils.display_gui_message(self, "De-identification Notice.", "Excel File Not Found")

            for i in range(num):
                n = 5
                range_start = 10**(n-1)
                range_end = (10**n)-1
                random_num = randint(range_start,range_end)
                patid = ('CHD%s%s') % (str(random_num),'01')
                today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                if patid in df2['CAP ID'].values:
                    i = i-1
                elif patid in df1['CAP ID'].values:
                    i = i-1
                else:
                    df2.loc[len(df2)] = [patid,today,' ',' ',' ',' ',' ','To Be Assigned',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ']

            try:
                writer = pd.ExcelWriter('CAP Patient list template.xlsx')
                df1.to_excel(writer,'Sheet1',index=False)
                df2.to_excel(writer,'Sheet2',index=False)
                writer.save()
                utils.display_gui_message(self, "De-identification Notice.", "%d Numbers Generated!"%(num))
            except IOError: 
                utils.display_gui_message(self, "De-identification Notice.", "Excel File Is Open. Close the File and Re-try")
                exit

        else:
            utils.display_gui_message(self, "De-identification Notice.", "Please Enter a Number Greater than 0")    


    def set_which_images_label(self, num_images):
        self.num_images_label.setText("Which images to deidentify (%s found)\n(Ex: 1-10 or 1,4,5, or 1-5,7,9)" % num_images)

    def set_existing_directory(self):    
        directory = QtGui.QFileDialog.getExistingDirectory(self,
                                          '',
                                          self.existing_directory_label.text(),
                                          QtGui.QFileDialog.DontResolveSymlinks | QtGui.QFileDialog.ShowDirsOnly)
        if len(directory) > 0:
            self.existing_directory_label.setText(directory)

            # stored the filenames in a dict with some image info
            self.dicom_image_name_dict = utils.read_in_files(self, self.existing_directory_label.text())

            # do a natural sort of the file names
            self.dicom_image_name_list = utils.human_sort_files(self.dicom_image_name_dict.keys())

            # display on the GUI how many DICOM files we found
            self.set_num_images(len(self.dicom_image_name_list))
            self.num_images.setText('%d Images Found'%(len(self.dicom_image_name_list)))
            if len(self.dicom_image_name_list) == 0:
                self.num_images.setText('Batch Mode!')

        

    def set_new_directory(self):    
        directory = QtGui.QFileDialog.getExistingDirectory(self,
                                          '',
                                          self.new_directory_label.text(),
                                          QtGui.QFileDialog.DontResolveSymlinks | QtGui.QFileDialog.ShowDirsOnly)

        if len(directory) > 0:
            self.new_directory_label.setText(directory)
            self.output_directory = directory

        with open('init.txt','w+') as f:
                f.write(directory)
        
        
    def get_num_images(self):
        #self.get_existing_image_info()
        return self.num_existing_images

    def get_file_names(self):
        #self.get_existing_image_info()
        return self.existing_file_names

    def disable_user_image_selection(self):
        self.num_images_line_edit.setText('All')
        self.num_images_line_edit.setReadOnly(True)

    def set_num_images(self, total_num_images):
        ''' 
        This will simply display the number of images the user can deident 
        '''
        self.num_existing_images = total_num_images
        if total_num_images > 0:
            #self.num_images_line_edit.setText('All')
            self.num_images_line_edit.setText('1 - %s' % total_num_images)
            self.num_images_line_edit.setReadOnly(False)
        else:
            self.num_images_line_edit.setText('%s' % total_num_images)
            self.num_images_line_edit.setReadOnly(True)

        # update the GUI to show how many we found
        self.set_which_images_label(total_num_images)

    def accept(self):
        '''
        This will handle the actions once the user wants to process
        the images.
        '''
        try:
            writer = open('CAP Patient list template.xlsx','a+')
        except IOError:
            utils.display_gui_message(self, "De-identification Notice.", "Excel File Is Open. Close the File and Re-try")
            return
            
        original_text = self.new_directory_label.text()
        d = batch_helper.createBatchDictionary(self.existing_directory_label.text())

        #For each one of the MR id's, go through the list of file locations and generate
        for x in d:
            
            self.new_directory_label.setText(original_text);
            #Check if any images are in the directory
         
            #Make sure that the number is not re-used
            xls = pd.ExcelFile('CAP Patient list template.xlsx')
            df1 = pd.read_excel(xls,'Sheet1')
            df2 = pd.read_excel(xls,'Sheet2')

            df1['CAP ID'] = df1['CAP ID'].astype(str)
            df2['CAP ID'] = df2['CAP ID'].astype(str)
            df1['MR #'] = df1['MR #'].astype(str)

            patid = ''
            while(True):
                n = 5
                range_start = 10**(n-1)
                range_end = (10**n)-1
                random_num = randint(range_start,range_end)
                patid = ('CHD%s') % (str(random_num))
                    
                
                if patid in df1['CAP ID'].values:
                    pass
                elif patid in df2['CAP ID'].values:
                    pass
                else:
                    break

            isInMR = False
            
            

            for idx,j in enumerate(d[x]):

                xls = pd.ExcelFile('CAP Patient list template.xlsx')
                df1 = pd.read_excel(xls,'Sheet1',index = False)
                df2 = pd.read_excel(xls,'Sheet2', index = False)
                
                df1['CAP ID'] = df1['CAP ID'].astype(str)
                df2['CAP ID'] = df2['CAP ID'].astype(str)
                df1['MR #'] = df1['MR #'].astype(str)

                if x in df1['MR #'].values:
                    count = (df1['MR #'] == x).sum()
                    print('COUNT IS AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA: %s'%(str(count)))
                    patid = df1.loc[df1['MR #'] == x,'CAP ID'].iloc[0]
                    isInMR = True

                    if len(str(count)) == 1:
                        patid = ('%s%s%s')%(patid[:-2],'0',count)
                    else:
                        patid = ('%s%s')%(patid[:-2],count)

                if isInMR == True:
                    if int(patid[-2:]) + 1 < 10:
                        ID2 = ('%s%s%s')%(patid[:-2],'0',str(int(patid[-2:]) + 1))
                    else:
                        ID2 = ('%s%s')%(patid[:-2],str(int(patid[-2:]) + 1))
                                
                    print('patid: %s'%(patid))
                else:
                    if idx+1 < 10:
                        ID2 = ('%s%s%s')%(patid,'0',str(idx+1))
                    else:
                        ID2 = ('%s%s')%(patid,str(idx+1))
                        
                self.user_id_line_edit.setText(ID2)
                self.existing_directory_label.setText(j)
                self.new_directory_label.setText(original_text)

                # stored the filenames in a dict with some image info
                self.dicom_image_name_dict = utils.read_in_files(self, self.existing_directory_label.text())

                # do a natural sort of the file names
                self.dicom_image_name_list = utils.human_sort_files(self.dicom_image_name_dict.keys())

                # display on the GUI how many DICOM files we found
                self.set_num_images(len(self.dicom_image_name_list))
                

                # make sure they entered an identifier
                if not len(self.user_id_line_edit.text()) > 0:
                    # display error message
                    message = "Please enter a new patient identifier."
                    utils.display_gui_message(self, "No indentification entered.", message)
                    return

                
                #Create output folder and change the directory
                '''directory = QtGui.QFileDialog.getExistingDirectory(self,'',self.new_directory_label.text(), QtGui.QFileDialog.DontResolveSymlinks | QtGui.QFileDialog.ShowDirsOnly)
                 
                if not os.path.exists("%s/%s"%(directory,self.user_id_line_edit.text()[:-2])):
                     os.makedirs("%s/%s"%(directory,self.user_id_line_edit.text()[:-2]))
                self.new_directory_label.setText('%s/%s'%(directory,self.user_id_line_edit.text()[:-2]))
                '''
                
                directory = self.new_directory_label.text()
                ID = ID2

                #Create the two output folders
                deidentified_directory = ('%s/Deidentified Data'%(directory))
                identified_directory = ('%s/Identified Data'%(directory))
                
                if not os.path.exists(deidentified_directory):
                    os.makedirs(deidentified_directory);
                if not os.path.exists(identified_directory):
                    os.makedirs(identified_directory);

                original_directory = self.existing_directory_label.text()
                #Create subfolders in the identified_directory
                if len(original_directory) > 0:
         
                    #Create Base CHD ID folder
                    if not os.path.exists(('%s/%s')%(identified_directory,ID[:-2])):
                        os.makedirs(("%s/%s")%(identified_directory,ID[:-2]))
                                          
                    sub_directory = ("%s/%s")%(identified_directory,ID[:-2])

                    
                    #Create the standard subdirectories    
                    folders = ["/Cath","/CMR","/Clinic Notes","/ECG","/ECHO","/OP Notes","/Other"]
                    for i in folders:
                        if not os.path.exists("%s%s"%(sub_directory,i) ):
                            print("%s%s"%(sub_directory,i))
                            os.makedirs("%s%s"%(sub_directory,i))
                                          
                    sub_directory = ('%s%s')%(sub_directory,'/CMR/');

                    #Create Subfolder with test number (E.X. '01', or '02')
                    if not os.path.exists(('%s/%s')%(sub_directory,ID)):
                        os.makedirs(("%s/%s")%(sub_directory,ID))
                                          
                    sub_directory = ("%s/%s")%(sub_directory,ID)

                    original_directory = ('%s/')%(original_directory)
                    files = os.listdir(original_directory)

                    for f in files:
                        shutil.copy(original_directory+f,sub_directory)
                    
                #Create subfolders in output directory ###################TODO FIX #########################                             
                
                if len(deidentified_directory) > 0:

                    #Create Base CHD ID folder
                    if not os.path.exists("%s/%s"%(deidentified_directory,ID[:-2])):
                        os.makedirs("%s/%s"%(deidentified_directory,ID[:-2]))
                        
                    sub_directory = "%s/%s"%(deidentified_directory,ID[:-2])

                    #Create Subfolder with test number (E.X. '01', or '02')
                    if not os.path.exists("%s/%s"%(sub_directory,ID)):
                        self.new_directory_label.setText("%s/%s"%(sub_directory,ID))
                        os.makedirs("%s/%s"%(sub_directory,ID))
                        
                    sub_directory = "%s/%s"%(sub_directory,ID)

                print('SUB DIRECTORY IS %s' % (sub_directory))
                    
                # get the image numbers that the user entered
                image_num_wanted = \
                      parselist.parse_list_reg_exp(self.num_images_line_edit.text())

                # get the filenames for the images
                image_name_wanted = []
                utils.display_message("%s files wanted..." % len(image_num_wanted))
                for num in image_num_wanted:
                    try:
                        # we allow users to enters image numbers starting 
                        # at 1, so we need to get them back to base-zero 
                        # so, subtract one
                        image_name_wanted.append(self.dicom_image_name_list[num-1])
                        utils.display_message("File index %s\t : Orig filename %s" %\
                                             (num, self.dicom_image_name_list[num-1]))
                    except Exception as msg:
                        message = "Invalid range of images wanted, image %s not in image stack" %(num)
                        utils.display_message("%s" % message)
                        utils.display_gui_message(self, "Invalid range of images", message)
                        self.set_num_images(len(self.dicom_image_name_list))
                        return


                # Set up the progress bar
                # Can't get this to work as needed
                #progress = QtGui.QProgressDialog("de-identifying files...", 
                #                                 "Abort", 
                #                                 100, 
                #                                 100, 
                #                                 self)

                #progress.setMinimumDuration(0)
                #progress.setWindowModality(QtCore.Qt.WindowModal)
                ##progress.forceShow()
                ##progress.open()
                ##progress.setVisible(True)
                ##progress.setRange(0,1)
                #progress.setValue(0)
                #progress.setRange(0,0)
                #progress.show()

                t0 = time.time()
                # now process the images
                #QtGui.qApp.processEvents() # this would get the bar to display, just not move
                self.process_image = ProcessDicom(self.existing_directory_label.text(),
                                             sub_directory,
                                             image_name_wanted,
                                             image_num_wanted,
                                             self.user_id_line_edit.text(),
                                             '800m')

                result = self.process_image.process()

               

                ##progress.done()
                ##progress.finished()
                ##progress.update()
                #progress.cancel()
                copy = pd.ExcelWriter('Backups\CAP Patient list template-Backup-%s.xlsx'%((datetime.now().strftime('%Y-%m-%d %H-%M-%S'))), engine='xlsxwriter')
                df1.to_excel(copy,'Sheet1',index=False)
                df2.to_excel(copy,'Sheet2',index=False)
                copy.save()
                
  

                #Get the data from the DICOM Files
                filename = os.listdir(original_directory)[0]
                filename = ('%s/%s')%(original_directory,filename)
                ds = pydicom.dcmread(filename)
                name = ds.PatientName  
                sex = ds.PatientSex
                birthday = ds.PatientBirthDate
                scanday = ds.StudyDate
                try:
                    doctor = ds.ReferringPhysicianName
                except AttributeError:
                    doctor = ''
                try:
                    location = ds.InstitutionName
                except AttributeError:
                    location = ''
                patientid = ds.PatientID                

                #Format the name
                try:
                    reg = re.split('[  ^]',name.lower().title())
                    if len(reg) == 2:
                        name = reg[0] + ', ' + reg[1]
                    else:
                        name = reg[0] + ', ' + reg[1] + ' ' + reg[2] 
                except IndexError:
                    pass

            
                #Find the age of the patient
                try:
                    d1 = datetime.strptime(ds.StudyDate, '%Y%m%d')
                    d2 = datetime.strptime(ds.PatientBirthDate,'%Y%m%d')
                    age = (d1-d2).total_seconds() / (365*24*60*60)
                    d1 = d1.strftime("%m/%d/%Y")
                    d2 = d2.strftime("%m/%d/%Y")
                except ValueError:
                    d1 = ''
                    d2 = ''
                    age = ''

                today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                df1.loc[len(df1)] = [ID,today,name,patientid,d2,'',d1,'','',ID,'','',age,sex,'',doctor,location,'','']

                try:
                    writer = pd.ExcelWriter('CAP Patient list template.xlsx', engine='xlsxwriter')
                    df1.to_excel(writer,'Sheet1',index=False)
                    df2.to_excel(writer,'Sheet2',index=False)

                    writer.save()
                except IOError:
                    utils.display_gui_message(self, "De-identification Notice.", "Excel File Is Open. Close the File and Re-try")
                    exit
                    
        if not result:
            message = 'De-identification completed with issues, see console.'
            gui_message = 'De-identification completed <b>with issues</b>, see console.'
        else:
            message = 'De-identification completed successfully.'
            gui_message = 'De-identification completed <b>successfully.</b>'

        # Let the user know we're done with this batch
        utils.display_message(message)
        utils.display_gui_message(self, "De-identification Notice.", gui_message)
        self.new_directory_label.setText(original_text);
        self.existing_directory_label.setText(' ');


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    wizard = MainCanvas()
    wizard.show()
    sys.exit(wizard.exec_())
