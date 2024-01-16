#===============================================================================
# Fenrir Makefile for Windows
#===============================================================================
!include <win32.mak>


PROGRAM = tsi_test.exe

INC  = -I"..\..\tsi_sdk\inc" 
SRC  = main.cpp 
OBJ  = main.obj 
LIBS = Kernel32.lib version.lib DelayImp.lib opengl32.lib glu32.lib gdi32.lib User32.lib Advapi32.lib libcmt.lib winmm.lib 

#!IFNDEF TSI_PLATFORM
#!	IF ("$(PROCESSOR_ARCHITECTURE)" == "AMD64")
MANIFEST=fenrir.manifest
#!	ELSE
#MANIFEST=fenrir.x86.manifest
#!	ENDIF
#!ELSE
#!	IF ("$(TSI_PLATFORM)" == "AMD64")
#MANIFEST=fenrir.manifest
#!	ELSE
#MANIFEST=fenrir.x86.manifest
#!	ENDIF
#!ENDIF

FLAGS   = $(TSI_DEBUG) /O2 
LFLAGS  = /INCREMENTAL:NO /NODEFAULTLIB  /SUBSYSTEM:CONSOLE /debugtype:cv $(TSI_DEBUG) /MAP /MAPINFO:EXPORTS

#FLAGS   = $(TSI_DEBUG) /Zi /DEBUG /RTC1
#LFLAGS  = /INCREMENTAL:NO /NODEFAULTLIB  /SUBSYSTEM:CONSOLE /debugtype:cv $(TSI_DEBUG) /MAP /MAPINFO:EXPORTS /DEBUG

all: tsi_test.exe

tsi_test.exe: $(OBJ)
  $(link) $(LFLAGS) -out:tsi_test.exe $(OBJ) $(LIBS)
#   mt -manifest $(MANIFEST) -outputresource:fenrir.exe;1


main.obj: main.cpp
  $(cc) $(INC) $(FLAGS) -c main.cpp

release: all

debug: all

test:
   $(cc) /Zi /DEBUG $(INC) test_libgui.cpp

clean:
   del tsi_test.exe $(OBJ) 

install:
   copy tsi_test.exe w:\dist
   copy tsi_test.pdb w:\dist
#   copy fenrir.exe ..\edt_camera_link
#   copy fenrir.pdb ..\edt_camera_link
##   copy fenrir.exe ..\dist
#   copy fenrir.pdb ..\dist
