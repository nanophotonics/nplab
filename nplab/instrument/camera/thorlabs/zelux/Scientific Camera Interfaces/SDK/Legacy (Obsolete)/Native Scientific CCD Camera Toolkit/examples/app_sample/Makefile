#===============================================================================
# tsi_sample.exe Makefile for Windows
#===============================================================================
!include <win32.mak>

INC  = -I"..\tsi_sdk\inc"
SRC  = tsi_sample.cpp
OBJ  = tsi_sample.obj
LIBS = Kernel32.lib version.lib DelayImp.lib gdi32.lib User32.lib Advapi32.lib libcmt.lib User32.lib

!IFNDEF TSI_DEBUG
CPPFLAGS = /O2
LFLAGS  = /INCREMENTAL:NO /NODEFAULTLIB  /SUBSYSTEM:CONSOLE
!ELSE
CPPFLAGS = /Zi $(TSI_DEBUG)
LFLAGS  = /INCREMENTAL:NO /NODEFAULTLIB  /SUBSYSTEM:CONSOLE /debugtype:cv $(TSI_DEBUG)
!ENDIF
FLAGS   =  /NODEFAULTLIB /OPT:REF


!IFNDEF TSI_PLATFORM
!	IF ("$(PROCESSOR_ARCHITECTURE)" == "AMD64")
MANIFEST=tsi_sample.manifest
!	ELSE
MANIFEST=tsi_sample.x86.manifest
!	ENDIF
!ELSE
!	IF ("$(TSI_PLATFORM)" == "AMD64")
MANIFEST=tsi_sample.manifest
!	ELSE
MANIFEST=tsi_sample.x86.manifest
!	ENDIF
!ENDIF

all: tsi_sample.exe


tsi_sample.exe: $(OBJ)
  $(link) $(LFLAGS) -out:tsi_sample.exe $(OBJ) $(LIBS)
  mt -manifest $(MANIFEST) -outputresource:tsi_sample.exe;1

tsi_sample.obj: tsi_sample.cpp
   $(cc) $(INC) $(CPPFLAGS) -c tsi_sample.cpp

test:
   $(cc) $(INC) tsi_sample.c

clean:
   del $(OBJ) tsi_sample.exe

install:
   copy tsi_sample.exe ..\dist
   copy tsi_sample.pdb ..\dist

