#===============================================================================
# tsi_sample.exe Makefile for Windows
#===============================================================================
!include <win32.mak>

INC  = -I"..\..\tsi_sdk\inc" 
SRC  = wait_for_image.cpp
OBJ  = wait_for_image.obj
LIBS = Kernel32.lib version.lib DelayImp.lib gdi32.lib User32.lib Advapi32.lib libcmt.lib User32.lib

#-------------------------------------------------------------------------------
# Release
#-------------------------------------------------------------------------------
CPPFLAGS = /O2
LFLAGS  = /INCREMENTAL:NO /NODEFAULTLIB  /SUBSYSTEM:CONSOLE

#-------------------------------------------------------------------------------
# Debug
#-------------------------------------------------------------------------------
#CPPFLAGS = /Zi 
#LFLAGS  = /INCREMENTAL:NO /NODEFAULTLIB  /SUBSYSTEM:CONSOLE /debugtype:cv 
#FLAGS   =  /NODEFAULTLIB /OPT:REF


all: wait_for_image.exe


wait_for_image.exe: $(OBJ)
  $(link) $(LFLAGS) -out:wait_for_image.exe $(OBJ) $(LIBS)
#  mt -manifest $(MANIFEST) -outputresource:tsi_sample.exe;1

wait_for_image.obj: wait_for_image.cpp
   $(cc) $(INC) $(CPPFLAGS) -c wait_for_image.cpp

test:

clean:
   del $(OBJ) wait_for_image.exe

install:
   copy wait_for_image.exe ..\dist
   copy wait_for_image.pdb ..\dist

