//=============================================================================
// libgfx
//------------------------------------------------------------------------------
//==============================================================================
//#ifndef WIN32_LEAN_AND_MEAN
//   #define WIN32_LEAN_AND_MEAN
//#endif
#include <windows.h>
#include <windowsx.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strsafe.h>
#include <stdio.h>
#include <conio.h>


#include "TsiSDK.h"
#include "TsiCamera.h"
#include "TsiImage.h"

//------------------------------------------------------------------------------
// INPUT_DATA
//------------------------------------------------------------------------------

#define MAX_CMD_STR								256

typedef struct
{
   int change;
   int mouse_x;
   int mouse_y;
   int mouse_left_button_state;
   int mouse_left_button_pressed;
   int mouse_left_button_released;
   int drag_active;
   int drag_x;
   int drag_y;
   float  orig_value;

   int select_active;
   int select[4];

   int  cmd_str_index;
   char cmd_str[MAX_CMD_STR];
} INPUT_DATA;

//------------------------------------------------------------------------------
// WIN32_WINDOW
//------------------------------------------------------------------------------
typedef struct WIN32_WINDOW 
{
   struct     WIN32_WINDOW *next;
   int x;
   int y;
   int w;
   int h;
   int terminate;

   void                  (*update)(struct WIN32_WINDOW *);
   HWND                  window_handle;
   DWORD                 window_style;
   HDC                   window_dc;
   WNDCLASSEX            window_class;
   PIXELFORMATDESCRIPTOR pixel_format_desc;
   char                  bitmapbuffer[sizeof(BITMAPINFO)+16];
   BITMAPINFO           *bitmap_header;


   int pixel_buffer_width;
   int pixel_buffer_height;
   int bitpix;
   int bytepix;
   int pixel_buffer_size_in_bytes;
   int num_pixels;
   int pixel_size;

   int vbin;
   int hbin;

   //unsigned short *pixel_buffer;
   //unsigned int   *pixel_buffer;
   union
   {
      void           *vptr;
      unsigned char  *ui8;
      unsigned short *ui16;
      unsigned int   *ui32;
   } pixel_buffer;

   int          num_gui_commands;

} WIN32_WINDOW;


// Multi-monitor support

typedef struct _WIN32_MONITOR {

	RECT Rect;

} WIN32_MONITOR, *PWIN32_MONITOR;

#define MAX_SUPPORTED_MONITORS					2

// Font used on image display window

static unsigned char _font8x8_basic[128][8] = {
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0000 (nul)
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0001
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0002
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0003
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0004
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0005
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0006
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0007
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0008
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0009
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+000A
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+000B
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+000C
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+000D
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+000E
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+000F
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0010
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0011
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0012
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0013
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0014
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0015
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0016
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0017
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0018
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0019
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+001A
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+001B
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+001C
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+001D
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+001E
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+001F
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0020 (space)
    { 0x18, 0x3C, 0x3C, 0x18, 0x18, 0x00, 0x18, 0x00}, // U+0021 (!)
    { 0x36, 0x36, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0022 (")
    { 0x36, 0x36, 0x7F, 0x36, 0x7F, 0x36, 0x36, 0x00}, // U+0023 (#)
    { 0x0C, 0x3E, 0x03, 0x1E, 0x30, 0x1F, 0x0C, 0x00}, // U+0024 ($)
    { 0x00, 0x63, 0x33, 0x18, 0x0C, 0x66, 0x63, 0x00}, // U+0025 (%)
    { 0x1C, 0x36, 0x1C, 0x6E, 0x3B, 0x33, 0x6E, 0x00}, // U+0026 (&)
    { 0x06, 0x06, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0027 (')
    { 0x18, 0x0C, 0x06, 0x06, 0x06, 0x0C, 0x18, 0x00}, // U+0028 (()
    { 0x06, 0x0C, 0x18, 0x18, 0x18, 0x0C, 0x06, 0x00}, // U+0029 ())
    { 0x00, 0x66, 0x3C, 0xFF, 0x3C, 0x66, 0x00, 0x00}, // U+002A (*)
    { 0x00, 0x0C, 0x0C, 0x3F, 0x0C, 0x0C, 0x00, 0x00}, // U+002B (+)
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C, 0x06}, // U+002C (,)
    { 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x00}, // U+002D (-)
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C, 0x00}, // U+002E (.)
    { 0x60, 0x30, 0x18, 0x0C, 0x06, 0x03, 0x01, 0x00}, // U+002F (/)
    { 0x3E, 0x63, 0x73, 0x7B, 0x6F, 0x67, 0x3E, 0x00}, // U+0030 (0)
    { 0x0C, 0x0E, 0x0C, 0x0C, 0x0C, 0x0C, 0x3F, 0x00}, // U+0031 (1)
    { 0x1E, 0x33, 0x30, 0x1C, 0x06, 0x33, 0x3F, 0x00}, // U+0032 (2)
    { 0x1E, 0x33, 0x30, 0x1C, 0x30, 0x33, 0x1E, 0x00}, // U+0033 (3)
    { 0x38, 0x3C, 0x36, 0x33, 0x7F, 0x30, 0x78, 0x00}, // U+0034 (4)
    { 0x3F, 0x03, 0x1F, 0x30, 0x30, 0x33, 0x1E, 0x00}, // U+0035 (5)
    { 0x1C, 0x06, 0x03, 0x1F, 0x33, 0x33, 0x1E, 0x00}, // U+0036 (6)
    { 0x3F, 0x33, 0x30, 0x18, 0x0C, 0x0C, 0x0C, 0x00}, // U+0037 (7)
    { 0x1E, 0x33, 0x33, 0x1E, 0x33, 0x33, 0x1E, 0x00}, // U+0038 (8)
    { 0x1E, 0x33, 0x33, 0x3E, 0x30, 0x18, 0x0E, 0x00}, // U+0039 (9)
    { 0x00, 0x0C, 0x0C, 0x00, 0x00, 0x0C, 0x0C, 0x00}, // U+003A (:)
    { 0x00, 0x0C, 0x0C, 0x00, 0x00, 0x0C, 0x0C, 0x06}, // U+003B (//)
    { 0x18, 0x0C, 0x06, 0x03, 0x06, 0x0C, 0x18, 0x00}, // U+003C (<)
    { 0x00, 0x00, 0x3F, 0x00, 0x00, 0x3F, 0x00, 0x00}, // U+003D (=)
    { 0x06, 0x0C, 0x18, 0x30, 0x18, 0x0C, 0x06, 0x00}, // U+003E (>)
    { 0x1E, 0x33, 0x30, 0x18, 0x0C, 0x00, 0x0C, 0x00}, // U+003F (?)
    { 0x3E, 0x63, 0x7B, 0x7B, 0x7B, 0x03, 0x1E, 0x00}, // U+0040 (@)
    { 0x0C, 0x1E, 0x33, 0x33, 0x3F, 0x33, 0x33, 0x00}, // U+0041 (A)
    { 0x3F, 0x66, 0x66, 0x3E, 0x66, 0x66, 0x3F, 0x00}, // U+0042 (B)
    { 0x3C, 0x66, 0x03, 0x03, 0x03, 0x66, 0x3C, 0x00}, // U+0043 (C)
    { 0x1F, 0x36, 0x66, 0x66, 0x66, 0x36, 0x1F, 0x00}, // U+0044 (D)
    { 0x7F, 0x46, 0x16, 0x1E, 0x16, 0x46, 0x7F, 0x00}, // U+0045 (E)
    { 0x7F, 0x46, 0x16, 0x1E, 0x16, 0x06, 0x0F, 0x00}, // U+0046 (F)
    { 0x3C, 0x66, 0x03, 0x03, 0x73, 0x66, 0x7C, 0x00}, // U+0047 (G)
    { 0x33, 0x33, 0x33, 0x3F, 0x33, 0x33, 0x33, 0x00}, // U+0048 (H)
    { 0x1E, 0x0C, 0x0C, 0x0C, 0x0C, 0x0C, 0x1E, 0x00}, // U+0049 (I)
    { 0x78, 0x30, 0x30, 0x30, 0x33, 0x33, 0x1E, 0x00}, // U+004A (J)
    { 0x67, 0x66, 0x36, 0x1E, 0x36, 0x66, 0x67, 0x00}, // U+004B (K)
    { 0x0F, 0x06, 0x06, 0x06, 0x46, 0x66, 0x7F, 0x00}, // U+004C (L)
    { 0x63, 0x77, 0x7F, 0x7F, 0x6B, 0x63, 0x63, 0x00}, // U+004D (M)
    { 0x63, 0x67, 0x6F, 0x7B, 0x73, 0x63, 0x63, 0x00}, // U+004E (N)
    { 0x1C, 0x36, 0x63, 0x63, 0x63, 0x36, 0x1C, 0x00}, // U+004F (O)
    { 0x3F, 0x66, 0x66, 0x3E, 0x06, 0x06, 0x0F, 0x00}, // U+0050 (P)
    { 0x1E, 0x33, 0x33, 0x33, 0x3B, 0x1E, 0x38, 0x00}, // U+0051 (Q)
    { 0x3F, 0x66, 0x66, 0x3E, 0x36, 0x66, 0x67, 0x00}, // U+0052 (R)
    { 0x1E, 0x33, 0x07, 0x0E, 0x38, 0x33, 0x1E, 0x00}, // U+0053 (S)
    { 0x3F, 0x2D, 0x0C, 0x0C, 0x0C, 0x0C, 0x1E, 0x00}, // U+0054 (T)
    { 0x33, 0x33, 0x33, 0x33, 0x33, 0x33, 0x3F, 0x00}, // U+0055 (U)
    { 0x33, 0x33, 0x33, 0x33, 0x33, 0x1E, 0x0C, 0x00}, // U+0056 (V)
    { 0x63, 0x63, 0x63, 0x6B, 0x7F, 0x77, 0x63, 0x00}, // U+0057 (W)
    { 0x63, 0x63, 0x36, 0x1C, 0x1C, 0x36, 0x63, 0x00}, // U+0058 (X)
    { 0x33, 0x33, 0x33, 0x1E, 0x0C, 0x0C, 0x1E, 0x00}, // U+0059 (Y)
    { 0x7F, 0x63, 0x31, 0x18, 0x4C, 0x66, 0x7F, 0x00}, // U+005A (Z)
    { 0x1E, 0x06, 0x06, 0x06, 0x06, 0x06, 0x1E, 0x00}, // U+005B ([)
    { 0x03, 0x06, 0x0C, 0x18, 0x30, 0x60, 0x40, 0x00}, // U+005C (\)
    { 0x1E, 0x18, 0x18, 0x18, 0x18, 0x18, 0x1E, 0x00}, // U+005D (])
    { 0x08, 0x1C, 0x36, 0x63, 0x00, 0x00, 0x00, 0x00}, // U+005E (^)
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF}, // U+005F (_)
    { 0x0C, 0x0C, 0x18, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+0060 (`)
    { 0x00, 0x00, 0x1E, 0x30, 0x3E, 0x33, 0x6E, 0x00}, // U+0061 (a)
    { 0x07, 0x06, 0x06, 0x3E, 0x66, 0x66, 0x3B, 0x00}, // U+0062 (b)
    { 0x00, 0x00, 0x1E, 0x33, 0x03, 0x33, 0x1E, 0x00}, // U+0063 (c)
    { 0x38, 0x30, 0x30, 0x3e, 0x33, 0x33, 0x6E, 0x00}, // U+0064 (d)
    { 0x00, 0x00, 0x1E, 0x33, 0x3f, 0x03, 0x1E, 0x00}, // U+0065 (e)
    { 0x1C, 0x36, 0x06, 0x0f, 0x06, 0x06, 0x0F, 0x00}, // U+0066 (f)
    { 0x00, 0x00, 0x6E, 0x33, 0x33, 0x3E, 0x30, 0x1F}, // U+0067 (g)
    { 0x07, 0x06, 0x36, 0x6E, 0x66, 0x66, 0x67, 0x00}, // U+0068 (h)
    { 0x0C, 0x00, 0x0E, 0x0C, 0x0C, 0x0C, 0x1E, 0x00}, // U+0069 (i)
    { 0x30, 0x00, 0x30, 0x30, 0x30, 0x33, 0x33, 0x1E}, // U+006A (j)
    { 0x07, 0x06, 0x66, 0x36, 0x1E, 0x36, 0x67, 0x00}, // U+006B (k)
    { 0x0E, 0x0C, 0x0C, 0x0C, 0x0C, 0x0C, 0x1E, 0x00}, // U+006C (l)
    { 0x00, 0x00, 0x33, 0x7F, 0x7F, 0x6B, 0x63, 0x00}, // U+006D (m)
    { 0x00, 0x00, 0x1F, 0x33, 0x33, 0x33, 0x33, 0x00}, // U+006E (n)
    { 0x00, 0x00, 0x1E, 0x33, 0x33, 0x33, 0x1E, 0x00}, // U+006F (o)
    { 0x00, 0x00, 0x3B, 0x66, 0x66, 0x3E, 0x06, 0x0F}, // U+0070 (p)
    { 0x00, 0x00, 0x6E, 0x33, 0x33, 0x3E, 0x30, 0x78}, // U+0071 (q)
    { 0x00, 0x00, 0x3B, 0x6E, 0x66, 0x06, 0x0F, 0x00}, // U+0072 (r)
    { 0x00, 0x00, 0x3E, 0x03, 0x1E, 0x30, 0x1F, 0x00}, // U+0073 (s)
    { 0x08, 0x0C, 0x3E, 0x0C, 0x0C, 0x2C, 0x18, 0x00}, // U+0074 (t)
    { 0x00, 0x00, 0x33, 0x33, 0x33, 0x33, 0x6E, 0x00}, // U+0075 (u)
    { 0x00, 0x00, 0x33, 0x33, 0x33, 0x1E, 0x0C, 0x00}, // U+0076 (v)
    { 0x00, 0x00, 0x63, 0x6B, 0x7F, 0x7F, 0x36, 0x00}, // U+0077 (w)
    { 0x00, 0x00, 0x63, 0x36, 0x1C, 0x36, 0x63, 0x00}, // U+0078 (x)
    { 0x00, 0x00, 0x33, 0x33, 0x33, 0x3E, 0x30, 0x1F}, // U+0079 (y)
    { 0x00, 0x00, 0x3F, 0x19, 0x0C, 0x26, 0x3F, 0x00}, // U+007A (z)
    { 0x38, 0x0C, 0x0C, 0x07, 0x0C, 0x0C, 0x38, 0x00}, // U+007B ({)
    { 0x18, 0x18, 0x18, 0x00, 0x18, 0x18, 0x18, 0x00}, // U+007C (|)
    { 0x07, 0x0C, 0x0C, 0x38, 0x0C, 0x0C, 0x07, 0x00}, // U+007D (})
    { 0x6E, 0x3B, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // U+007E (~)
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00} // U+007F
};


//------------------------------------------------------------------------------
// Help Topics
//------------------------------------------------------------------------------

char *help_help = 
	"==============================================================================\n"
	"Topic: Help On Help\n"
	"==============================================================================\n\n"
	"Typing 'help' by itself displays a window with basic help information in it.\n\n"
	"Typing 'help *' will list the available help topics in the console window.\n\n"
	"Typing 'help {topic}' will print help about that topic to the console window.\n\n"
	"\n\n";

char *help_expm =
	"==============================================================================\n"
	"Topic: EXPM - Set exposure time (in milliseconds)\n"
	"==============================================================================\n\n"
	"Typing 'expm' by itself will display the current exposure setting in both the\n"
	"image and console windows.\n\n"
	"Typing 'expm {value}' will set the exposure time to that value, and then query\n"
	"the value from the camera to verify the setting was accepted.\n\n"
	"Setting the exposure time increases or decreases the amount of time light has\n"
	"to fall on the sensor.  Longer exposure times are good for low light conditions,\n"
	"but will lead to smearing if the objects in the view of the camera move during\n"
	"the exposure time.\n\n";

char *help_vgagain =
	"==============================================================================\n"
	"Topic: vgagain - sets the VGA gain in the camera\n"
	"==============================================================================\n\n"
	"Typing 'vgagain' by itself will display the VGA gain setting in both the\n"
	"image and console windows.\n\n"
	"Typing 'vgagain {value}' will set the VGA gain to that value, and then query\n"
	"the value from the camera to verify the setting was accepted.\n\n"
	"Setting the VGA gain allows for shorter exposure times at the expense of higher\n"
	"read noise\n\n";

char *help_save =
	"==============================================================================\n"
	"Topic: save - saves the next 'n' images to disk\n"
	"==============================================================================\n\n"
	"Typing 'save {number}' will save the next {number} images to disk.  The data is\n"
	"stored in RAW format, and can be imported into many imaging programs as such. \n\n"
	"The images will be stored in the folder the program was run from, and will have\n"
	"a name in the format of tsi_sample_img_XXX_imgs.raw, where XXX is replaced by the\n"
	"number of images saved.\n\n"
	"No serious buffering is done in this routine, so the program may fail to keep up\n"
	"with the camera when trying to save large data sets.\n\n"
	"To view the saved image data, import it as raw data. For Example, in ImageJ, Pick\n"
	"'File' from the menu, then 'Import', then 'Raw', then pick the file you want to\n"
	"view.  In the dialog box that pops up, use the following parameters\n\n"
	"       Image type: 16-bit Unsigned.\n"
	"            Width: Use the ROI width you supplied on the command line divided by\n"
	"                   the horizontal binning factor in effect.\n"
	"           Height: Use the ROI height you supplied on the command line divided by\n"
	"                   the vertical binning factor in effect.\n"
	" Number of Images: You can set this to some number greater than the number of frames\n"
	"                   in the file, ImageJ will stop when it gets to the end of the file.\n"
	"    Little-endian: Check this box.\n\n"
	"All other values are zero, and all other checkboxes are unchecked.\n\n"
	"Other imaging programs will work similarly, but may need to be told what the number\n"
	"significant bits per pixel were produced by the camera.\n\n";

char *help_name =
	"==============================================================================\n"
	"Topic: name - allows you to name the camera\n"
	"==============================================================================\n\n"
	"Typing 'name' by itself displays the current name of the camera.\n\n"
	"If you have not yet named the camera, a default name is assigned.\n\n"
	"The name is not stored in the camera, and is local to the commputer it is\n"
	"installed on.\n\n"
	"Typing 'name {new name}' sets the name associated with the camera.  The name is\n"
	"associated with the camera model, firmware revision, and serial number\n\n";

char *help_list =
	"==============================================================================\n"
	"Topic: list - displays a list of the available TSI_PARAM_xxx parameter names\n"
	"==============================================================================\n\n"
	"Typing 'list' by itself will display a list of TSI SDK parameters that you can\n"
	"type into the program to either set or get camera parameters.\n\n"
	"Typing 'list verbose' will display a comprehensive list of all the TSI SDK\n"
	"parameters the camera supports, and the attributes known about each one.\n\n";

char *help_about =
	"==============================================================================\n"
	"Topic: about - displays comprehensive information about a TSI SDK parameter\n"
	"==============================================================================\n\n"
	"Typing 'about {parameter name or fragment}' will either display a list of matching\n"
	"TSI SDK parameters, or, if a single match is found, comprehensive information\n"
	"about that parameter\n\n"
	"For example, if you type 'about gain', you will get a list of the TSI parameters\n"
	"with the word gain in the parameter name.  Currently, TSI_PARAM_CDS_GAIN,\n"
	"TSI_PARAM_VGA_GAIN, and TSI_PARAM_GAIN all have gain in the parameter name.\n\n"
	"If you then type 'about VGA', which only appears in one parameter, TSI_PARAM_VGA_GAIN,\n"
	"comprehensive information about that parameter is displayed, including the current\n"
	"value for that parameter.\n\n";

char *help_quit =
	"==============================================================================\n"
	"Topic: quit, exit - Terminates the program\n"
	"==============================================================================\n\n"
	"You can type quit, exit, or press the escape key to exit the program.\n\n";

char *help_list_help_topics =
	"==============================================================================\n"
	"Topic: * - list the current help topics\n"
	"==============================================================================\n\n"
	"help            - help on using the help system.\n"
	"expm            - help on setting the exposure time in milliseconds.\n"
	"vgagain         - help on setting the VGA gain.\n"
	"save            - help on saving image data.\n"
	"name            - help on naming the camera.\n"
	"list            - help on listing the TSI SDK parameters the camera supports.\n"
	"about           - help on displaying information about a particular TSI SDK parameter.\n"
	"quit, exit      - help on exiting the program.\n"
	"SDK, params,\n"
	"   parameters   - help on the TSI SDK parameter support in the program.\n"
	"*               - this help on what topics are available.\n\n";

char *help_parameter =
	"==============================================================================\n"
	"Topic: SDK, params, parameters - help on getting, setting, or displaying\n"
	"       information about TSI SDK parameters\n"
	"==============================================================================\n\n"
	"While viewing image data, you can simply type the name of a TSI SDK parameter\n"
	"TSI_PARAM_XXX, or any portion of one to find out what parameters match or in the\n"
	"single match, you can set or get that parameter's value.\n\n"
	"For example, if you type 'gain', you will get a list of the TSI parameters\n"
	"with the word gain in the parameter name.  Currently, TSI_PARAM_CDS_GAIN,\n"
	"TSI_PARAM_VGA_GAIN, and TSI_PARAM_GAIN all have gain in the parameter name, and\n"
	"they will be listed as possible candidates.\n\n"
	"If you then type 'VGA', which only appears in one parameter, TSI_PARAM_VGA_GAIN,\n"
	"the value for that parameter is displayed.\n\n"
	"If you then type 'VGA {value}', TSI_PARAM_VGA_GAIN is the only parameter matching\n"
	"'VGA', so the TSI_PARAM_VGA_GAIN parameter is set to the value you supply.\n\n"
	"Sometimes, two parameters are very closely named, for example TSI_PARAM_SPEED_INDEX,\n"
	"and TSI_PARAM_SPEED.  Just typing in 'speed' will match both of these parameters,\n"
	"but you may want to just view the current speed value (TSI_PARAM_SPEED).  In this\n"
	"case, you would type 'speed.' (with the trailing period) to indicate you want to\n"
	"match on a parameter ending in 'speed'.  This will work for the 'about' command\n"
	"as well.\n\n";

//------------------------------------------------------------------------------
// File scope data.
//------------------------------------------------------------------------------
static WIN32_WINDOW *_curr_window    = 0;
static WIN32_WINDOW *_window_list    = 0;
static INPUT_DATA    _input			 = {0};

static HWND console_window_handle    = 0;
static int NumberOfMonitors          = 0;
static int ConsoleMonitor            = 0;
static int ImagingMonitor            = 0;

static WIN32_MONITOR MonitorData [MAX_SUPPORTED_MONITORS];

static int          _os_64bit        = 0;
static int          _app_64bit       = 0;
HMODULE             _tsi_dll_handle  = 0;

unsigned int        exposure_time_ms = 5;
unsigned int        exposure_unit_ms = TSI_EXP_UNIT_MILLISECONDS;

TsiCamera    *_camera							= 0;
bool		 camera_running						= false;
        
int resize_window(HWND hwnd, int w, int h);

#define					TEST_TIMER				100

CRITICAL_SECTION		ScreenUpdateCriticalSection; 

int						num_exposures           = 0;

bool					display_dimensions		= false;
int						images_to_save			= 0;
char					user_supplied_file_name [1024] = "";

char					help_str []             = "Type command or \x22help\x22 for list of commands >";
char					ptsi_str []             = "ptsi >";
char					info_msg_str [1024]		= "";
char					dimension_str [80]		= "";
bool                    display_event_info      = false;
CRITICAL_SECTION		CtlEventCriticalSection; 
volatile int			cur_ctl_event			= -1;
volatile TSI_FUNCTION_CAMERA_CONTROL_INFO cur_ctl_event_info = {0};
char					image_info_str [128]	= "";

char					script_file_name [MAX_PATH] = "";
FILE					*script_file				= NULL;
bool					script_active				= false;

TSI_ROI_BIN				initial_tsi_roi_bin;
TSI_ROI_BIN				current_tsi_roi_bin;

long					expected_image_size_in_bytes = 0;

bool					clear_display				= false;
bool					printf_prompt_required		= false;

#define					MAX_OP_MODES				4
char					*OperatingModeNames [MAX_OP_MODES + 1] =
							{
								"NORMAL",
								"PDX",
								"TOE",
								"TDI",
								"UNKNOWN"
							};


//==============================================================================
// is_os_64bit
//------------------------------------------------------------------------------
//==============================================================================
int is_os_64bit(void)
{

#if defined(_WIN64)

   return 1;  

#elif defined(_WIN32)

	int	    Wow64Process  = FALSE;
	PBOOL	pWow64Process = &Wow64Process;
	HANDLE	ProcessHandle;

	ProcessHandle = GetCurrentProcess();
	
	IsWow64Process(ProcessHandle, pWow64Process);

	return (int) ((Wow64Process == TRUE) ? 1 : 0);

#else

   return FALSE; 

#endif
}


//==============================================================================
// does_file_exist
//------------------------------------------------------------------------------
//==============================================================================
int does_file_exist(char *file)
{
FILE *fp = 0;

   fp = fopen(file, "r");
   if(fp == 0)
   {
      return 0;
   }

   fclose(fp);

   return 1;
}

/*
typedef struct _IMAGE_DOS_HEADER {  // DOS .EXE header
    USHORT e_magic;         // Magic number
    USHORT e_cblp;          // Bytes on last page of file
    USHORT e_cp;            // Pages in file
    USHORT e_crlc;          // Relocations
    USHORT e_cparhdr;       // Size of header in paragraphs
    USHORT e_minalloc;      // Minimum extra paragraphs needed
    USHORT e_maxalloc;      // Maximum extra paragraphs needed
    USHORT e_ss;            // Initial (relative) SS value
    USHORT e_sp;            // Initial SP value
    USHORT e_csum;          // Checksum
    USHORT e_ip;            // Initial IP value
    USHORT e_cs;            // Initial (relative) CS value
    USHORT e_lfarlc;        // File address of relocation table
    USHORT e_ovno;          // Overlay number
    USHORT e_res[4];        // Reserved words
    USHORT e_oemid;         // OEM identifier (for e_oeminfo)
    USHORT e_oeminfo;       // OEM information; e_oemid specific
    USHORT e_res2[10];      // Reserved words
    LONG   e_lfanew;        // File address of new exe header
  } IMAGE_DOS_HEADER, *PIMAGE_DOS_HEADER;

//==============================================================================
// is_lib_64bit
//------------------------------------------------------------------------------
//==============================================================================
int is_lib_64bit(char *file)
{
FILE *fp        = 0;
int   num_bytes = 0;

IMAGE_DOS_HEADER win32_file;

   fp = fopen(file, "r");
   if(fp == 0)
   {
      return 0;
   }

   num_bytes = fread(&win32_file, sizeof(IMAGE_DOS_HEADER), 1, fp);
   if(num_bytes != sizeof(IMAGE_DOS_HEADER))
   {
      fclose(fp);
      return 0;
   }

   

   fclose(fp);

   return 1;
}
*/

//==============================================================================
// control_callback
//------------------------------------------------------------------------------
//==============================================================================
void control_callback (int  ctl_event, TSI_FUNCTION_CAMERA_CONTROL_INFO *ctl_event_info, void *context)
{

	if (TryEnterCriticalSection(&CtlEventCriticalSection)) {

		cur_ctl_event      = ctl_event;

		memcpy ((void *) &cur_ctl_event_info, ctl_event_info, sizeof (cur_ctl_event_info));

		LeaveCriticalSection (&CtlEventCriticalSection);


	}

}

//==============================================================================
// add_to_window_list
//------------------------------------------------------------------------------
//==============================================================================
int add_to_window_list(WIN32_WINDOW *window)
{
WIN32_WINDOW *curr   = 0;

   if(_window_list == 0)
   {
      _window_list = window;
   }
   else
   {
      curr = _window_list;
      while(curr->next != (WIN32_WINDOW *)0) curr = curr->next;
      curr->next = window;
   }

   return 1;
}


//==============================================================================
// remove_from_window_list
//------------------------------------------------------------------------------
//==============================================================================
int remove_from_window_list(WIN32_WINDOW *window)
{
WIN32_WINDOW *prev   = 0;
WIN32_WINDOW *curr   = 0;

   if(_window_list == 0)
   {
      return 0;
   }

   curr = _window_list;
   while(curr != 0) 
   {
      if(curr == window)
      {
         if(prev == 0)   
         {
            _window_list = curr->next;
         } 
         else
         {
            prev->next = curr->next;   
         }

         return 1;
      }

      prev = curr;
      curr = curr->next;
   }

   return 0;
}

//==============================================================================
// get_window
//------------------------------------------------------------------------------
//==============================================================================
WIN32_WINDOW *get_window(HWND window_handle)
{
WIN32_WINDOW *curr   = 0;

   if(_window_list == 0) return 0;

   curr = _window_list;
   while(curr != 0) 
   {
      if(curr->window_handle == window_handle)
      {
         return curr;
      }

      curr = curr->next;
   }

   return 0;
}


//==============================================================================
// close_window
//------------------------------------------------------------------------------
//==============================================================================
int close_window(HWND hwnd)
{
WIN32_WINDOW *window = 0;

   window = get_window(hwnd);
   if(window == 0) return 0;

   window->terminate = 1;

   return 1;
}


//==============================================================================
// resize_window
//------------------------------------------------------------------------------
//==============================================================================
int resize_window(HWND hwnd, int w, int h)
{
WIN32_WINDOW *window = 0;
RECT          rect;
int width  = 0;
int height = 0;

   window = get_window(hwnd);
   if(window == 0) return 0;

   rect.top    = 0;
   rect.left   = 0; 
   rect.right  = width; 
   rect.bottom = height;
   //AdjustWindowRectEx(&rect, window->window_style, FALSE, 0);
   GetClientRect(window->window_handle, &rect);

   width     = rect.right  - rect.left;
   height    = rect.bottom - rect.top;

   //printf("resize_window - w:%d h:%d    width:%d height:%d\n", w, h, width, height);

   window->w        = width;
   window->h        = height;

   return 1;
}



char sub_image_str[256];

//==============================================================================
// draw_window
//------------------------------------------------------------------------------
//==============================================================================
int draw_window(HWND hwnd)
{
WIN32_WINDOW *window = 0;
RECT          rect;
int width  = 0;
int height = 0;


int src_width  = 0;
int src_height = 0;

   window = get_window(hwnd);
   if(window == 0) return 0;

   rect.top    = 0;
   rect.left   = 0; 
   rect.right  = width; 
   rect.bottom = height;
   GetClientRect(window->window_handle, &rect);

   width     = rect.right  - rect.left;
   height    = rect.bottom - rect.top;

   src_width  = window->pixel_buffer_width;
   src_height = window->pixel_buffer_height;

   if(window->pixel_buffer_width  >  width) src_width  = width;
   if(window->pixel_buffer_height > height) src_height = height;

   StretchDIBits(window->window_dc, 0, 0, src_width, src_height, 0, 0, 
                                                              src_width, 
                                                             src_height, 
                                              window->pixel_buffer.vptr, 
                                                  window->bitmap_header, 
                                                DIB_RGB_COLORS, SRCCOPY);

  //draw_gui_text(_text, window->window_dc, 0, 0);
  //DrawTextA(window->window_dc, sub_image_str, -1, &rect, DT_CENTER);

  ValidateRect(window->window_handle, NULL);

   return 1;
}


#define PIXEL_OFFSET(p, x, y, w) p[ pixel_offset_ex(p, x, y, w, window->pixel_buffer_width, window->pixel_buffer_height) ]

//==============================================================================
// pixel_offset
//------------------------------------------------------------------------------
//==============================================================================
int pixel_offset_ex (unsigned int *pixel_buffer, int x, int y, int w, int max_x, int max_y) 
{
	unsigned int return_value;

	int max_offset        = (max_x * max_y) - 1; 
	int calculated_offset; 

	if (x >= max_x) {
		x = max_x - 1;
	}
	
	if (y >= max_y) {
		y = max_y - 1;
	}

	calculated_offset = (y * w) + x; 

	if (calculated_offset <= max_offset) {
		return_value = calculated_offset;
	} else {
		return_value = max_offset;
	}

	return return_value;

}

//==============================================================================
// draw_line
//------------------------------------------------------------------------------
//==============================================================================
void draw_line(WIN32_WINDOW *window, int x0, int y0, int x1, int y1, int color, int num_levels, int intensity)
{
unsigned int *pixel_buffer = 0;
int           w            = 0;
int           h            = 0;

int delta_x = 0;
int delta_y = 0;
int xdir    = 0;
int temp    = 0;

int error_adj        = 0;
int error_accum      = 0;
int error_accum_temp = 0;
int weight           = 0;
int weight_mask      = 0;
int intensity_shift  = 0;

   w            = window->pixel_buffer_width;
   h            = window->pixel_buffer_height;
   pixel_buffer = window->pixel_buffer.ui32;

   if(x1 >= w) x1 = w;
   if(y1 >= h) y1 = h;

   //---------------------------------------------------------------------------
   // Make sure line runs from top to bottom.
   //---------------------------------------------------------------------------
   if(y0 > y1)
   {
      temp = y0; y0 = y1; y1 = temp;
      temp = x0; x0 = x1; x1 = temp;
   }

   PIXEL_OFFSET(pixel_buffer, x0, y0, w) = color; 

   if((delta_x = x1 - x0) >= 0)
   {
      xdir  = 1;
   }
   else 
   {
      xdir   = -1;
      delta_x = -delta_x;
   }

   //---------------------------------------------------------------------------
   // Horizontal line.
   //---------------------------------------------------------------------------
   if((delta_y = y1 - y0) == 0)
   {
      while(delta_x-- != 0)
      {
         x0 += xdir;
         PIXEL_OFFSET(pixel_buffer, x0, y0, w) = color;
      }

      return;
   }

   //---------------------------------------------------------------------------
   // Vertical line.
   //---------------------------------------------------------------------------
   if(delta_x == 0)
   {
      do
      {
         y0++;
         PIXEL_OFFSET(pixel_buffer, x0, y0, w) = color;
      }
      while(--delta_y != 0);

      return;
   }

   //---------------------------------------------------------------------------
   // Diagonal line.
   //---------------------------------------------------------------------------
   if(delta_x == delta_y)
   {
      do
      {
         x0 += xdir;
         y0++;
         PIXEL_OFFSET(pixel_buffer, x0, y0, w) = color;
      }
      while(--delta_y != 0);

      return;
   }

   error_accum     = 0;
   intensity_shift = 16 - intensity;
   weight_mask     = num_levels - 1;

   if(delta_y > delta_x)
   {
      error_adj = (delta_x << 16) / delta_y;

      while(--delta_y)
      {
         error_accum_temp = error_accum;
         error_accum     += error_adj;
         if(error_accum <= error_accum_temp)
         {
            x0 += xdir;
         }

         y0++;
         weight = error_accum >> intensity_shift;

         PIXEL_OFFSET(pixel_buffer, x0, y0, w) = color + weight;
         PIXEL_OFFSET(pixel_buffer, x0 + xdir, y0, w) = color + (weight ^ weight_mask);
      }

      PIXEL_OFFSET(pixel_buffer, x0, y0, w) = color;

      return;
   }

   error_adj = (delta_y << 16) / delta_x;
   while(--delta_x)
   {
      error_accum_temp = error_accum;
      error_accum     += error_adj;
      if(error_accum <= error_accum_temp)
      {
         y0++;
      }
 
      x0 += xdir;

      weight = error_accum >> intensity_shift;

      PIXEL_OFFSET(pixel_buffer, x0, y0, w) = color + weight;
      PIXEL_OFFSET(pixel_buffer, x0, y0+1, w) = color + (weight ^ weight_mask);
   }

   PIXEL_OFFSET(pixel_buffer, x0, y0, w) = color;
}


//==============================================================================
// draw_text
//------------------------------------------------------------------------------
//==============================================================================
void draw_text(WIN32_WINDOW *window, char *text, int x, int y, int color) 
{
unsigned int *pixel_buffer = 0;
int           w            = 0;
int           h            = 0;
int           i            = 0;
int           j            = 0;   

int index = 0;

unsigned char *f = 0;

   w            = window->pixel_buffer_width;
   h            = window->pixel_buffer_height;
   pixel_buffer = window->pixel_buffer.ui32;

   while(*text)
   {
      f = _font8x8_basic[*text++];

      for(i=0;i<8;i++)
      {
         for(j=0;j<8;j++)
         {
            if(f[i] & 1 << j)
            {
               pixel_buffer[((y+i)*w)+(x+j)] = color;
            }
         }
      }   
      x+=9;
   }

}



//==============================================================================
// draw_rect
//------------------------------------------------------------------------------
//==============================================================================
void draw_rect(WIN32_WINDOW *window, int x0, int y0, int x1, int y1, int color)
{
   if(window->bitpix == 32)
   {
      draw_line(window, x0, y0, x1, y0, color, 0, 0);
      draw_line(window, x1, y0, x1, y1, color, 0, 0);
      draw_line(window, x1, y1, x0, y1, color, 0, 0);
      draw_line(window, x0, y1, x0, y0, color, 0, 0);
   }
}


//==============================================================================
// draw_rect_solid
//------------------------------------------------------------------------------
//==============================================================================
void draw_rect_solid(WIN32_WINDOW *window, int x0, int y0, int w, int h, int color)
{
int i;
int x1;

   if(window->bitpix == 32)
   {
      if(w > 0)
      {
         x1 = x0 + w - 1;
         for(i=0;i < h;i++)
            draw_line(window, x0, y0+i, x1, y0+i, color, 0, 0);
      }
   }
}

//==============================================================================
// handle_error 
//------------------------------------------------------------------------------
//==============================================================================
void handle_error (char *Msg)
{

	TSI_ERROR_CODE  ErrorCode;
	char			ErrorStr [256];
	int				ErrorStrLength = 256;
	
	if (_camera) {

		ErrorCode = _camera->GetErrorCode ();

		if (_camera->GetErrorStr (ErrorCode, ErrorStr, ErrorStrLength)) {
			sprintf (info_msg_str, "Error %u (%s) %s\n", ErrorCode, ErrorStr, Msg);
		} else {
			sprintf (info_msg_str, "Error %u %s\n", ErrorCode, Msg);
		}

		printf (info_msg_str);

		_camera->ClearError ();

	} else {
		sprintf (info_msg_str, "%s", Msg);
		printf ("%s\n", info_msg_str);
	}

}

//==============================================================================
// TDI_supported
//------------------------------------------------------------------------------
//==============================================================================
bool TDI_supported (void)
{

	bool return_value = false;


	if (_camera) {

		TSI_PARAM_ATTR_ID	ParamAttrID;
		uint32_t			MaxModes;

		ParamAttrID.ParamID = TSI_PARAM_OP_MODE;

		// Get the parameter max

		ParamAttrID.AttrID  = TSI_ATTR_MAX_VALUE;	
		if (_camera->SetParameter(TSI_PARAM_CMD_ID_ATTR_ID, &ParamAttrID)) {
			if (_camera->GetParameter(TSI_PARAM_ATTR, sizeof(MaxModes), &MaxModes)) {
				return_value = (MaxModes >= 3);  // TDI mode == 3
			} else {
				handle_error ("retrieving the max value for TSI_PARAM_OP_MODE");
	 		}
		} else {
			handle_error ("setting up to retrieve the max value for TSI_PARAM_OP_MODE");
		}

	}

	return return_value;

}

//==============================================================================
// get_or_set_param 
//------------------------------------------------------------------------------
//==============================================================================
int get_or_set_param (TSI_PARAM_ID param, char *param_name, char *input_str, bool verbose)
{

	uint32_t			uResult[6]				= {0};
	int32_t				*Result					= (int32_t *) uResult;
	int					ResultCount				= 0;
	char				tsi_param_name [40]		= "TSI_PARAM_UNKNOWN";
	TSI_DATA_TYPE		tsi_param_data_type		= TSI_TYPE_NONE;
	uint32_t			tsi_param_array_count	= 0;
	uint32_t			tsi_param_flags			= 0;
	bool				tsi_param_read_only		= false;
	bool				tsi_param_supported		= false;

	TSI_PARAM_ATTR_ID	AttributeDescriptor;

	if (_camera) {

		AttributeDescriptor.ParamID = (TSI_PARAM_ID) param;

		// Get the flags for this parameter so we can determine whether it is supported or read only.

		AttributeDescriptor.AttrID  = TSI_ATTR_FLAGS;

		if (!_camera->SetParameter (TSI_PARAM_CMD_ID_ATTR_ID, &AttributeDescriptor)) {
			handle_error ("Error: Unable to SetParameter (TSI_PARAM_CMD_ID_ATTR_ID, TSI_ATTR_FLAGS");
			goto Exit;
		} else if (!_camera->GetParameter (TSI_PARAM_ATTR, sizeof (tsi_param_flags), &tsi_param_flags)) {

			// Could be this parameter is not supported on this camera...

			handle_error ("Error: GetParameter (TSI_PARAM_ATTR) failed... Parameter is not supported on this camera\n");

			tsi_param_supported = false;

		} else {
			tsi_param_supported = ((tsi_param_flags & TSI_FLAG_UNSUPPORTED) == 0);
			tsi_param_read_only	= ((tsi_param_flags & TSI_FLAG_READ_ONLY) > 0);
		}

		// If this parameter is not supported on this camera...

		if (tsi_param_supported) {
			if (!script_active) {
				printf (
					"Parameter %u is Supported, %s\n", 
					(uint32_t) AttributeDescriptor.ParamID,
					(tsi_param_read_only ? "Read Only" : "Read Write")
					);
			}
		} else {
			printf (
				"Parameter %u is Not Supported\n", 
				(uint32_t) AttributeDescriptor.ParamID
				);
		}

		// If we weren't passed in a name the app wanted to use for display, we'll just use
		// the name the API supplies.

		if (NULL == param_name) {

			AttributeDescriptor.AttrID  = TSI_ATTR_NAME;

			if (!_camera->SetParameter (TSI_PARAM_CMD_ID_ATTR_ID, &AttributeDescriptor)) {
				handle_error ("Error: Unable to SetParameter (TSI_PARAM_CMD_ID_ATTR_ID, TSI_ATTR_NAME\n");
				goto Exit;
			} else if (!_camera->GetParameter (TSI_PARAM_ATTR, sizeof (tsi_param_name), tsi_param_name)) {
				char temp_msg_str [128];
				sprintf (temp_msg_str , "Error: Unable to GetParameter(TSI_PARAM_ATTR, TSI_ATTR_NAME) @ %s:%u\n", __FUNCTION__, __LINE__);
				handle_error (temp_msg_str);
				goto Exit;
			} else {
				param_name = tsi_param_name;
			}

		}

		// If this parameter is not supported on this camera...

		if (!tsi_param_supported) {

			if (verbose) {

				printf ("\n");
				if (NULL == param_name) {
					printf ("       Ordinal: %u - Not supported on this camera\n", (uint32_t) AttributeDescriptor.ParamID);
				} else {
					printf ("       %s - Ordinal: %u - Not supported on this camera\n", param_name, (uint32_t) AttributeDescriptor.ParamID);
				}

			}

			goto Exit;

		}

		// Get the data type, so we can determine whether this parameter refers to a text
		// or numeric value.

		AttributeDescriptor.AttrID  = TSI_ATTR_DATA_TYPE;

		if (!_camera->SetParameter (TSI_PARAM_CMD_ID_ATTR_ID, &AttributeDescriptor)) {
			handle_error ("Error: Unable to SetParameter (TSI_PARAM_CMD_ID_ATTR_ID\n");
			goto Exit;
		} else if (!_camera->GetParameter (TSI_PARAM_ATTR, sizeof (tsi_param_data_type), &tsi_param_data_type)) {

			char temp_msg_str [128];
			printf ("\n");

			if (verbose) {
				printf ("\n");
				if (NULL == param_name) {
					printf ("       Ordinal: %u - Error: Unable to get data type for this parameter\n", (uint32_t) AttributeDescriptor.ParamID);
				} else {
					printf ("       %s - Ordinal: %u - Error: Unable to get data type for this parameter\n", param_name, (uint32_t) AttributeDescriptor.ParamID);
				}
			}

			sprintf (temp_msg_str, "Error: Unable to GetParameter(TSI_PARAM_ATTR, TSI_ATTR_DATA_TYPE) @ %s:%u\n", __FUNCTION__, __LINE__);
			handle_error (temp_msg_str);

			goto Exit;

		} else {
			tsi_param_read_only	= ((tsi_param_flags & TSI_FLAG_READ_ONLY) > 0);
		}

		// Get either the length of the string, or the repeat count for the number of items if it's an array of things.

		AttributeDescriptor.AttrID  = TSI_ATTR_ARRAY_COUNT;

		if (!_camera->SetParameter (TSI_PARAM_CMD_ID_ATTR_ID, &AttributeDescriptor)) {

			char temp_msg_str [128];

			printf ("\n");

			if (NULL == param_name) {
				printf ("       Ordinal: %u - ", (uint32_t) AttributeDescriptor.ParamID);
			} else {
				printf ("       %s - Ordinal: %u - ", param_name, (uint32_t) AttributeDescriptor.ParamID);
			}

			sprintf (temp_msg_str, "Error: Unable to SetParameter (TSI_PARAM_CMD_ID_ATTR_ID, TSI_ATTR_ARRAY_COUNT\n");
			handle_error (temp_msg_str);

			goto Exit;

		} else if (!_camera->GetParameter (TSI_PARAM_ATTR, sizeof (tsi_param_array_count), &tsi_param_array_count)) {

			char temp_msg_str [128];
			printf ("\n");

			if (NULL == param_name) {
				printf ("       Ordinal: %u - ", (uint32_t) AttributeDescriptor.ParamID);
			} else {
				printf ("       %s - Ordinal: %u - ", param_name, (uint32_t) AttributeDescriptor.ParamID);
			}

			sprintf (temp_msg_str, "Error: Unable to GetParameter(TSI_PARAM_ATTR, TSI_ATTR_ARRAY_COUNT) @ %s:%u\n", __FUNCTION__, __LINE__);
			handle_error (temp_msg_str);

			goto Exit;

		} else {
			tsi_param_read_only	= ((tsi_param_flags & TSI_FLAG_READ_ONLY) > 0);
		}

		if (tsi_param_read_only) {
			sprintf (info_msg_str, "Parameter %s is read only\n", param_name);
			printf (info_msg_str);
		} else if (!tsi_param_supported) {
			sprintf (info_msg_str, "Parameter %s is not supported\n", param_name);
			printf (info_msg_str);
		} else if ((TSI_TYPE_UNS32 == tsi_param_data_type) || (TSI_TYPE_INT32 == tsi_param_data_type)) {

			// If we can get an integer parameter from the command line, it must be the user
			// wants to set a parameter, not display its value
			
			ResultCount = sscanf(input_str, "%*s %d", &Result[0]);

			if (ResultCount > 0) {

				printf ("%d Parameters Converted: %d %d %d %d %d %d", ResultCount, Result[0], Result[1], Result[2], Result[3], Result[4], Result[5]);

				if (TSI_TYPE_UNS32 == tsi_param_data_type) {
					ResultCount = sscanf(input_str, "%*s %d %d %d %d %d %d", &Result[0], &Result[1], &Result[2], &Result[3], &Result[4], &Result[5]);
				} else if (TSI_TYPE_INT32 == tsi_param_data_type) {
					ResultCount = sscanf(input_str, "%*s %u %u %u %u %u %u", &uResult[0], &uResult[1], &uResult[2], &uResult[3], &uResult[4], &uResult[5]);
				}

				// We're only supporting setting scalar (not vector) values at the current time.

				if (tsi_param_array_count > 6) {
					sprintf (info_msg_str, "Setting array parameters > 6 not supported: %s has %u elements\n", param_name, tsi_param_array_count);
					printf (info_msg_str);
				} else {

					sprintf (info_msg_str, "Setting parameter %s\n", param_name);

					if (!_camera->SetParameter(param, Result)) {
						sprintf (info_msg_str, "Error: Failed to set %s to: %d\n", param_name, *Result);
						printf (info_msg_str);
					}
				}
			}

		} else if (TSI_TYPE_TEXT == tsi_param_data_type) {

			char StringResult [1024] = "";

			ResultCount = sscanf(input_str, "%*s %s", StringResult);

			if (ResultCount > 0) {

				sprintf (info_msg_str, "Set %s to: %s\n", param_name, StringResult);
				printf (info_msg_str);

				if (!_camera->SetParameter(param, StringResult)) {
					sprintf (info_msg_str, "Error: Failed to set %s to: %s\n", param_name, StringResult);
					printf (info_msg_str);
				}

			}

		}

		// If we're being verbose, display all the information about the parameter in the text
		// pane.

		if (verbose) {

			printf ("\n");

			printf ("       Ordinal: %u\n", (uint32_t) AttributeDescriptor.ParamID);
			printf ("          Name: %s\n", param_name);

			printf ("     Data Type: ");
			switch (tsi_param_data_type) {

				case TSI_TYPE_NONE  : printf ("TSI_TYPE_NONE");  break;
				case TSI_TYPE_UNS8  : printf ("TSI_TYPE_UNS8");  break;
				case TSI_TYPE_UNS16 : printf ("TSI_TYPE_UNS16"); break;
				case TSI_TYPE_UNS32 : printf ("TSI_TYPE_UNS32"); break;
				case TSI_TYPE_UNS64 : printf ("TSI_TYPE_UNS64"); break;
				case TSI_TYPE_INT8  : printf ("TSI_TYPE_INT8");  break;
				case TSI_TYPE_INT16 : printf ("TSI_TYPE_INT16"); break;
				case TSI_TYPE_INT32 : printf ("TSI_TYPE_INT32"); break;
				case TSI_TYPE_INT64 : printf ("TSI_TYPE_INT64"); break;
				case TSI_TYPE_TEXT  : printf ("TSI_TYPE_TEXT");  break;
				case TSI_TYPE_FP    : printf ("TSI_TYPE_FP");    break;
				default             : printf ("UNKNOWN - %u", tsi_param_data_type); break;
				   
			}
			printf ("\n");

			printf ("   Array Count: %d\n", tsi_param_array_count);

			uint32_t flag = 1;

			printf ("         Flags: ");
			while (flag < 0x8000000) {

				switch (tsi_param_flags & flag) {

					case TSI_FLAG_READ_ONLY		: printf ("TSI_FLAG_READ_ONLY ");		break;
					case TSI_FLAG_WRITE_ONLY	: printf ("TSI_FLAG_WRITE_ONLY ");		break;
					case TSI_FLAG_UNSUPPORTED	: printf ("TSI_FLAG_UNSUPPORTED ");		break;
					case TSI_FLAG_VALUE_CHANGED	: printf ("TSI_FLAG_VALUE_CHANGED ");	break;

				}

				flag <<= 1;

			}

			printf ("\n");

		}

		// In either case, get the current value for the parameter - that way, we can make
		// sure the API/Camera accepted the setting, or we can simply display what the current
		// setting is.

		// In this example, we're only supporting getting single 32 bit integer or text values...

		if (TSI_TYPE_NONE != tsi_param_data_type) {

			uint8_t     *param_data         = NULL;
			uint8_t     *pdata				= NULL;
			size_t		param_value_size	= 0;
			size_t		param_buffer_size	= 0;
			bool		skip_min_max		= false;

			switch (tsi_param_data_type) {

				case TSI_TYPE_NONE  : skip_min_max = true;                  break;
				case TSI_TYPE_UNS8  : param_value_size = sizeof (uint8_t);  break;
				case TSI_TYPE_UNS16 : param_value_size = sizeof (uint16_t); break;
				case TSI_TYPE_UNS32 : param_value_size = sizeof (uint32_t); break;
				case TSI_TYPE_UNS64 : param_value_size = sizeof (uint64_t); break;
				case TSI_TYPE_INT8  : param_value_size = sizeof (int8_t);   break;
				case TSI_TYPE_INT16 : param_value_size = sizeof (int16_t);  break;
				case TSI_TYPE_INT32 : param_value_size = sizeof (int32_t);  break;
				case TSI_TYPE_INT64 : param_value_size = sizeof (int64_t);  break;
				case TSI_TYPE_FP    : param_value_size = sizeof (float);    break;
				case TSI_TYPE_TEXT  : param_value_size = 1; skip_min_max = true; break;
				   
			}

			param_buffer_size	= param_value_size * tsi_param_array_count;
			param_data			= (uint8_t *) malloc (param_buffer_size);

			// if verbose, get the min, max, and default.

			if (verbose && !skip_min_max) {

				for (uint32_t Attribute = TSI_ATTR_MIN_VALUE; Attribute <= TSI_ATTR_DEFAULT_VALUE; Attribute++) {

					AttributeDescriptor.AttrID = (TSI_ATTR_ID) Attribute;

					if (!_camera->SetParameter (TSI_PARAM_CMD_ID_ATTR_ID, &AttributeDescriptor)) {
						sprintf (info_msg_str, "Error: Unable to SetParameter (TSI_PARAM_CMD_ID_ATTR_ID\n");
						printf (info_msg_str);
						goto Exit;
					} else if (!_camera->GetParameter (TSI_PARAM_ATTR, param_buffer_size, param_data)) {
						continue;
					} else {

						char *attribute_name;

						switch (AttributeDescriptor.AttrID) {
							case TSI_ATTR_MIN_VALUE     :	attribute_name = "Min"; break;
							case TSI_ATTR_MAX_VALUE     :	attribute_name = "Max"; break;
							case TSI_ATTR_DEFAULT_VALUE :	attribute_name = "Def"; break;
							default :						attribute_name = "Err"; break;
						}

						// Print out the value(s)

						printf ("           %3s: ", attribute_name);

						pdata = param_data;

						if (TSI_TYPE_TEXT == tsi_param_data_type) {
							printf ("%s", (char *) pdata);
						} else {

							for (uint32_t i = 0; i < tsi_param_array_count; i++) {

								if (i > 0) {
									printf (", ");
								}

								switch (tsi_param_data_type) {

									case TSI_TYPE_UNS8   : printf ("%u", *((uint8_t  *) pdata)); break;
									case TSI_TYPE_UNS16  : printf ("%u", *((uint16_t *) pdata)); break;
									case TSI_TYPE_UNS32  : printf ("%u", *((uint32_t *) pdata)); break;
									case TSI_TYPE_UNS64  : printf ("%u", *((uint64_t *) pdata)); break;
									case TSI_TYPE_INT8   : printf ("%d", *((uint8_t  *) pdata)); break;
									case TSI_TYPE_INT16  : printf ("%d", *((uint16_t *) pdata)); break;
									case TSI_TYPE_INT32  : printf ("%d", *((uint32_t *) pdata)); break;
									case TSI_TYPE_INT64  : printf ("%d", *((uint64_t *) pdata)); break;
									case TSI_TYPE_FP     : printf ("%f", *((float    *) pdata)); break;

								}

								pdata += param_value_size;

								// Limit the output to the first 10 values

								if (i > 10) {
									printf ("...");
									break;
								}

							}

						}

						printf ("\n");

					}

				}

				printf ("\n");

			} else if (verbose) {

				printf ("\n");

			}

			if ((tsi_param_flags & TSI_FLAG_WRITE_ONLY) == 0) {

				// Display the current value

				if (!_camera->GetParameter(param, param_buffer_size, param_data)) {

					sprintf (info_msg_str, "Error: Failed to get %s\n", param_name);
					printf (info_msg_str);

				} else {

					char temp_msg [1024] = "";
					char *p = temp_msg;

					// Print out the value(s) 

					pdata = param_data;

					if (TSI_TYPE_TEXT == tsi_param_data_type) {
						sprintf (p, "%s", (char *) pdata);
						p += strlen (p);
					} else {

						for (uint32_t i = 0; i < tsi_param_array_count; i++) {

							if (i > 0) {
								sprintf (p, ", ");
								p += strlen (p);
							}

							switch (tsi_param_data_type) {

								case TSI_TYPE_UNS8   : sprintf (p, "%u", *((uint8_t  *) pdata)); break;
								case TSI_TYPE_UNS16  : sprintf (p, "%u", *((uint16_t *) pdata)); break;
								case TSI_TYPE_UNS32  : sprintf (p, "%u", *((uint32_t *) pdata)); break;
								case TSI_TYPE_UNS64  : sprintf (p, "%u", *((uint64_t *) pdata)); break;
								case TSI_TYPE_INT8   : sprintf (p, "%d", *((uint8_t  *) pdata)); break;
								case TSI_TYPE_INT16  : sprintf (p, "%d", *((uint16_t *) pdata)); break;
								case TSI_TYPE_INT32  : sprintf (p, "%d", *((uint32_t *) pdata)); break;
								case TSI_TYPE_INT64  : sprintf (p, "%d", *((uint64_t *) pdata)); break;
								case TSI_TYPE_FP     : sprintf (p, "%f", *((float    *) pdata)); break;

							}

							// Currently only returning the first value in an array.

							if (0 == i) {
								Result [0] = *((int *) pdata);
							}

							// Limit the output to the first 10 values

							if (i > 10) {
								sprintf (p, "...");
								p += strlen (p);
								break;
							}

							p     += strlen (p);
							pdata += param_value_size;

						}

					}

					sprintf (p, "\n");

					sprintf (info_msg_str, "Current %s: %s\n", param_name, temp_msg);

					if (verbose) {
						printf ("           %s", info_msg_str);
					} else {
						printf ("\n%s", info_msg_str);
					}


				}
			}

			if (param_data != NULL) {
				free (param_data);
				param_data = NULL;
			}

		} else if (verbose) {
			printf ("\n");
		}

	}

Exit:

	if (verbose) {

		printf ("\n=================================================\n");

	}

	return Result [0];

}

//==============================================================================
// find_tsi_param 
//------------------------------------------------------------------------------
//==============================================================================

int find_tsi_param (char *input_str, TSI_PARAM_ID &param_ID)
{

	uint32_t			current_param_ID;
	char				tsi_param_name [40];
	char				user_param_name [40];
	char				user_tsi_param_name [40] = "TSI_PARAM_";

	char				*p;
	char				*match_point;

	int					matches			= 0;
	bool				use_exact_match = false;

	TSI_PARAM_ATTR_ID	AttributeDescriptor;

	if (sscanf(input_str, "%s", &user_param_name) > 0) {

		size_t end_of_string_index = strlen (user_param_name) - 1; 

		if ('.' == user_param_name [end_of_string_index]) {
			user_param_name [end_of_string_index] = 0;
			use_exact_match = true;
		}

		if (_strnicmp (user_param_name, user_tsi_param_name, strlen (user_tsi_param_name)) == 0) {
			strcpy (user_tsi_param_name, user_param_name);
		} else {
			strcat (user_tsi_param_name, user_param_name);
		}

	}

	p = user_param_name;
	while (*p) {
		*p = (char) toupper ((int) *p);
		p++;
	}

	p = user_tsi_param_name;
	while (*p) {
		*p = (char) toupper ((int) *p);
		p++;
	}

	for (current_param_ID = 0; current_param_ID < TSI_MAX_PARAMS; current_param_ID++) {

		AttributeDescriptor.ParamID = (TSI_PARAM_ID) current_param_ID;
		AttributeDescriptor.AttrID  = TSI_ATTR_NAME;

		if (!_camera->SetParameter (TSI_PARAM_CMD_ID_ATTR_ID, &AttributeDescriptor)) {
			sprintf (info_msg_str, "Error: Unable to SetParameter (TSI_PARAM_CMD_ID_ATTR_ID\n");
			printf (info_msg_str);
			break;
		} else if (!_camera->GetParameter (TSI_PARAM_ATTR, sizeof (tsi_param_name), tsi_param_name)) {
			sprintf (info_msg_str, "Error: Unable to GetParameter (TSI_PARAM_ATTR\n");
			printf (info_msg_str);
			break;
		} else {

			p = tsi_param_name;
			while (*p) {
				*p = (char) toupper ((int) *p);
				p++;
			}

		}

		match_point = strstr (tsi_param_name, user_tsi_param_name);
		if (match_point  != NULL) {

			if (0 == matches) {
				if (!script_active) {
					sprintf (info_msg_str, "Matching TSI Parameter(s): %s", tsi_param_name);
				}
			} else if (matches < 5) {
				strcat (info_msg_str, ", ");
				strcat (info_msg_str, tsi_param_name);
			}

			if (use_exact_match) {

				if (strlen (match_point) == strlen (user_tsi_param_name)) {
					param_ID = AttributeDescriptor.ParamID;
					matches++;
					break;
				}

			} else {

				param_ID = AttributeDescriptor.ParamID;
				matches++;

			}


		} else {
			
			match_point = strstr (tsi_param_name, user_param_name);
			if (match_point  != NULL) {

				if (0 == matches) {
					if (!script_active) {
						sprintf (info_msg_str, "Matching Parameter(s): %s", tsi_param_name);
					}
				} else if (matches < 5) {
					strcat (info_msg_str, ", ");
					strcat (info_msg_str, tsi_param_name);
				}

				if (use_exact_match) {

					if (strlen (match_point) == strlen (user_param_name)) {
						param_ID = AttributeDescriptor.ParamID;
						matches++;
						break;
					}
					
				} else {

					param_ID = AttributeDescriptor.ParamID;
					matches++;

				}

			}
		}

	}

	if (matches >= 5) {
		char more_str [20];
		sprintf (more_str, ", and %d more...", (matches - 5));
		strcat (info_msg_str, more_str);
	}

	printf ("%s\n", info_msg_str);

	return (1 == matches);

}

//==============================================================================
// list_tsi_params 
//------------------------------------------------------------------------------
//==============================================================================

void list_tsi_params (bool verbose, char *param_str)
{

	uint32_t			current_param_ID;
	char				tsi_param_name [40];


	TSI_PARAM_ATTR_ID	AttributeDescriptor;
	TSI_PARAM_ID		param_to_list			= TSI_MAX_PARAMS;

	// Check for listing a single parameter...

	if (NULL != param_str) {
		if (param_str [0] != 0) {
			if (!find_tsi_param (param_str, param_to_list)) {
				param_to_list = TSI_MAX_PARAMS;
			}
		}
	}

	printf ("\n");
	printf ("==============================================================================\n");
	printf ("                            TSI Parameter List                                \n");
	printf ("==============================================================================\n");

	for (current_param_ID = 0; current_param_ID < TSI_MAX_PARAMS; current_param_ID++) {

		// If we're listing something in particular, limit the display to that.

		if (param_to_list != TSI_MAX_PARAMS) {
			if (current_param_ID != param_to_list) {
				continue;
			}
		}

		AttributeDescriptor.ParamID = (TSI_PARAM_ID) current_param_ID;
		AttributeDescriptor.AttrID  = TSI_ATTR_NAME;

		if (!_camera->SetParameter (TSI_PARAM_CMD_ID_ATTR_ID, &AttributeDescriptor)) {
			printf ("Error: Unable to SetParameter (TSI_PARAM_CMD_ID_ATTR_ID)\n");
		} else if (!_camera->GetParameter (TSI_PARAM_ATTR, sizeof (tsi_param_name), tsi_param_name)) {
			printf ("Error: Unable to GetParameter (TSI_PARAM_ATTR)\n");
		} else if (verbose) {
#if 0
			printf (
				"current_param_ID: %u == %d\n", 
				current_param_ID,
				get_or_set_param (AttributeDescriptor.ParamID, NULL, tsi_param_name, true)
				);
#else
			get_or_set_param (AttributeDescriptor.ParamID, NULL, tsi_param_name, true);
#endif

		} else {
			printf ("%s\n", tsi_param_name);
		}

#if 0
		if (current_param_ID >= TSI_PARAM_FW_VER) {
			break;
		}
#endif

	}

	printf ("==============================================================================\n");
	printf ("                           End of Parameter List                              \n");
	printf ("==============================================================================\n");

	sprintf (info_msg_str, "Check the text window for the list of commands");

	return;

}

//==============================================================================
// about_tsi_param
//------------------------------------------------------------------------------
//==============================================================================

void about_tsi_param (char *input_str)
{

	TSI_PARAM_ID param_ID;

	// Skip to the first space, this is after the word "about".

	while (*input_str != ' ') {

		// If we're at the end of the string, bail.
		if (*input_str == 0) {
			return;
		}

		input_str++;

	}

	// Eat up all the white space

	while (*input_str == ' ') {

		// If we're at the end of the string, bail.
		if (*input_str == 0) {
			return;
		}

		input_str++;

	}

	// Truncate anything past the parameter we're asking about

	char *p = input_str;

	while (*p != 0) {

		if (' ' == *p) {
			*p = 0;
			break;
		}

		p++;

	}

	// Display all the info about the parameter.

	if (find_tsi_param (input_str, param_ID)) {

		get_or_set_param (param_ID, NULL, input_str, true);

	}

}

//==============================================================================
// check_tsi_param 
//------------------------------------------------------------------------------
//==============================================================================

void check_tsi_param (char *input_str)
{

	TSI_PARAM_ID param_ID;

	if (find_tsi_param (input_str, param_ID)) {

		get_or_set_param (param_ID, NULL, input_str, false);

	}

}

//==============================================================================
// swap_monitors 
//------------------------------------------------------------------------------
//==============================================================================
void swap_monitors (void)
{

	if (NumberOfMonitors > 1) {

		RECT ConsoleWindowRect;
		RECT ImagingWindowRect;

		if (!GetWindowRect(console_window_handle, &ConsoleWindowRect)) {
			goto Exit;
		}

		if (!GetWindowRect(_curr_window->window_handle, &ImagingWindowRect)) {
			goto Exit;
		}

		int tempMonitor = ConsoleMonitor;
		ConsoleMonitor = ImagingMonitor;
		ImagingMonitor = tempMonitor;

		SetWindowPos(
			console_window_handle,
			HWND_TOP,
			MonitorData [ConsoleMonitor].Rect.left,
			MonitorData [ConsoleMonitor].Rect.top,
			ConsoleWindowRect.right - ConsoleWindowRect.left,
			ConsoleWindowRect.bottom - ConsoleWindowRect.top,
			SWP_SHOWWINDOW
			);

		SetWindowPos(
			_curr_window->window_handle,
			HWND_TOP,
			MonitorData [ImagingMonitor].Rect.left,
			MonitorData [ImagingMonitor].Rect.top,
			ImagingWindowRect.right - ImagingWindowRect.left,
			ImagingWindowRect.bottom - ImagingWindowRect.top,
			SWP_SHOWWINDOW
			);

	}

Exit:

	return;

}

//==============================================================================
// process_command
//------------------------------------------------------------------------------
//==============================================================================
bool process_command (HWND hwnd)
{

	bool result = true;
	int  value;

	if(_strnicmp(_input.cmd_str, "quit", 4) == 0)
	{
		result = false;
		goto Exit;
	}

	if(_strnicmp(_input.cmd_str, "q", 1) == 0)
	{
		result = false;
		goto Exit;
	}

	if(_strnicmp(_input.cmd_str, "exit", 4) == 0)
	{
		result = false;
		goto Exit;
	}

	if(_strnicmp(_input.cmd_str, "swap", 4) == 0)
	{
		swap_monitors ();
		goto Exit;
	}

	if(_strnicmp(_input.cmd_str, "expm", 4) == 0)
	{

		exposure_time_ms = get_or_set_param (TSI_PARAM_EXPOSURE_TIME, "exposure time", _input.cmd_str, false);

		goto Exit;

	}

	if(_strnicmp(_input.cmd_str, "vgagain", 7) == 0)
	{

		get_or_set_param (TSI_PARAM_VGA_GAIN, "vga gain", _input.cmd_str, false);

		goto Exit;

	}

	if(_strnicmp(_input.cmd_str, "name", 4) == 0)
	{

		if (_camera) {

			char *pName = strtok (_input.cmd_str, " ");
			if (pName) {

				pName = strtok (NULL, " ");

				if (NULL == pName) {
					strncpy(info_msg_str, _camera->GetCameraName(), 256);
				} else {
					_camera->SetCameraName (pName);
				}

			} else {
				strncpy(info_msg_str, _camera->GetCameraName(), 256);
			}

			printf ("Camera Name %s\n", _camera->GetCameraName());

		}

		goto Exit;

	}

	if(_strnicmp(_input.cmd_str, "start", 5) == 0)
	{

		if(_camera) {
			camera_running	= _camera->Start();
			result			= camera_running;
			if (!result) {
				sprintf (info_msg_str, "Camera failed to start, error %u\n", _camera->GetErrorCode ());
				printf  (info_msg_str);
					_camera->ClearError ();
			} else {
				printf ("Camera started\n");
				strcpy (info_msg_str, "Camera started\n");
			}
		}

		clear_display  = true;

		goto Exit;

	}

	if(_strnicmp(_input.cmd_str, "stop", 4) == 0)
	{

		TsiImage     *image       = 0;

		if (_camera) {

			// Tell the camera to stop

			result = _camera->Stop();

			// Consume all the pending frames

			do {

				image = _camera->GetPendingImage(); 
				if (NULL != image) {
					_camera->FreeImage (image);
				}

			} while (NULL != image);

			if (!result) {
				printf ("Camera failed to stop\n");
				strcpy (info_msg_str, "Error: Camera failed to stop\n");
			} else {
				printf ("Camera stopped\n");
				strcpy (info_msg_str, "Camera stopped\n");
			}

		}

		camera_running = false;

		goto Exit;

	}

	if(_strnicmp(_input.cmd_str, "mode", 4) == 0)
	{

		char text_value [128];
		bool parameter_found;
		int  current_value;

		parameter_found = (sscanf(_input.cmd_str,"%*s %s", &text_value) > 0);

		if (parameter_found) {

			// BUGBUG: GAH - need an enum in the API for operating modes

			if(_strnicmp(text_value, "normal", 6) == 0) {
				value = 0;
			} else {
				if (sscanf(_input.cmd_str,"%*s %d", &value) == 0) {
					printf ("Invalid operating mode %s\n", text_value);
					sprintf (info_msg_str, "Error: Invalid operating mode %s\n", text_value);
					goto Exit;
				}
			}

			if (!TDI_supported ()) {
				printf ("TDI not supported on this camera\n");
				sprintf (info_msg_str, "Error: TDI not supported on this camera\n");
				goto Exit;
			} 

			if (_camera) {

				if (!_camera->SetParameter(TSI_PARAM_OP_MODE, (void *)&value)) {
					printf ("Failed to set operating mode to %d\n", value);
					sprintf (info_msg_str, "Error: Failed to set operating mode to %d\n", value);
				}

			}

		}

		if (_camera) {

			if (!_camera->GetParameter(TSI_PARAM_OP_MODE, sizeof (current_value), (void *)&current_value)) {
				printf ("Failed to get operating mode\n");
				sprintf (info_msg_str, "Error: Failed to get operating mode\n");
			} else {
				if (parameter_found) {
					if (value == current_value) {
						printf ("Current Operating mode %s\n", ((current_value < MAX_OP_MODES) ? OperatingModeNames [current_value] : OperatingModeNames [MAX_OP_MODES]));
						sprintf (info_msg_str, "Current Operating mode %s\n", ((current_value < MAX_OP_MODES) ? OperatingModeNames [current_value] : OperatingModeNames [MAX_OP_MODES]));
					} else {
						printf ("Camera did not accept new operating mode - Current operating mode %s\n", ((current_value < MAX_OP_MODES) ? OperatingModeNames [current_value] : OperatingModeNames [MAX_OP_MODES]));
						sprintf (info_msg_str, "Error: Camera did not accept new operating mode - Current operating mode %s\n", ((current_value < MAX_OP_MODES) ? OperatingModeNames [current_value] : OperatingModeNames [MAX_OP_MODES]));
					}
				} else {
					printf ("Current Operating mode %s\n", ((current_value < MAX_OP_MODES) ? OperatingModeNames [current_value] : OperatingModeNames [MAX_OP_MODES]));
					sprintf (info_msg_str, "Current Operating mode %s\n", ((current_value < MAX_OP_MODES) ? OperatingModeNames [current_value] : OperatingModeNames [MAX_OP_MODES]));
				}
			}

		}

		goto Exit;

		if(_strnicmp(_input.cmd_str, "taps", 4) == 0)
		{
		
			if (_camera) {

				bool GetTapsInfo = true;

				if (sscanf(_input.cmd_str,"%*s %d",&value) > 0) {

					if (!_camera->SetParameter(TSI_PARAM_TAPS_INDEX, (void *)&value)) {

						printf ("Failed to set Taps Index to %d\n", value);
						sprintf (info_msg_str, "Error: Failed to set Taps Index to %d\n", value);

						GetTapsInfo = false;

					}

				}

				if (GetTapsInfo) {

					uint32_t TapsIndex = 0;
					uint32_t TapsValue = 0;

					if (!_camera->GetParameter(TSI_PARAM_TAPS_INDEX, sizeof(TapsIndex), (void *)&TapsIndex)) {
						printf ("Failed to get Taps Index\n");
						sprintf (info_msg_str, "Error: Failed to get Taps Index\n");
					} else if (!_camera->GetParameter(TSI_PARAM_TAPS_VALUE, sizeof(TapsValue), (void *)&TapsValue)) {
						printf ("Failed to get Taps Value\n");
						sprintf (info_msg_str, "Error: Failed to get Taps Value\n");
					} else {
						printf ("Current Taps Index: %u, Value: %u\n", TapsIndex, TapsValue);
						sprintf (info_msg_str, "Current Taps Index: %u, Value: %u\n", TapsIndex, TapsValue);
					}

				}

			}

			goto Exit;

		}

		if(_strnicmp(_input.cmd_str, "name", 4) == 0)
		{

			if (_camera) {

				char *pName = strtok (_input.cmd_str, " ");
				if (pName) {

					pName = strtok (NULL, " ");

					if (NULL == pName) {
						strncpy(info_msg_str, _camera->GetCameraName(), 256);
					} else {
						_camera->SetCameraName (pName);
					}

				} else {
					strncpy(info_msg_str, _camera->GetCameraName(), 256);
				}

				printf ("Camera Name %s\n", _camera->GetCameraName());

			}

			goto Exit;

		}


	}

	if(_strnicmp(_input.cmd_str, "help", 4) == 0)
	{

		char help_topic [40];

		if (sscanf(_input.cmd_str, "%*s %s", help_topic) == 0) {

			MessageBox(
				hwnd, 
				"expm #\t\t- Set the exposure time in ms\n"
				"vgagain #\t- Set the VGA gain (0-1023)\n"
				"save #\t\t- Save the next # images to an ImageJ import file\n"
				"name {name}\t- Get/Set the camera name\n"
				"list [verbose]\t- List all the TSI parameters - verbose lists attributes\n"
				"about {TSI Param}\t- Display info about a TSI param (will match partial)\n"
				"swap \t\t- Swaps the monitors the Console and Image Windows are on\n"
				"help\t\t- [{topic}|*]\t\t- This help or help on one of the above commands\n"
				"quit,\n"
				"exit\t\t- Exit the program\n\n"
				"{param}\t\t- Type in part of a TSI_PARAM to see what matches\n",
				"Program Help",
				MB_OK
				);

		} else {

			if(_strnicmp(help_topic, "help", 4) == 0) {
				printf (help_help);
			} else if(_strnicmp(help_topic, "expm", 4) == 0) {
				printf (help_expm);
			} else if(_strnicmp(help_topic, "vgagain", 7) == 0) {
				printf (help_vgagain);
			} else if(_strnicmp(help_topic, "save", 4) == 0) {
				printf (help_save);
			} else if(_strnicmp(help_topic, "name", 4) == 0) {
				printf (help_name);
			} else if(_strnicmp(help_topic, "list", 4) == 0) {
				printf (help_list);
			} else if(_strnicmp(help_topic, "about", 5) == 0) {
				printf (help_about);
			} else if(_strnicmp(help_topic, "quit", 4) == 0) {
				printf (help_quit);
			} else if(_strnicmp(help_topic, "exit", 4) == 0) {
				printf (help_quit);
			} else if(_strnicmp(help_topic, "SDK", 3) == 0) {
				printf (help_parameter);
			} else if(_strnicmp(help_topic, "params", 6) == 0) {
				printf (help_parameter);
			} else if(_strnicmp(help_topic, "parameters", 10) == 0) {
				printf (help_parameter);
			} else if(_strnicmp(help_topic, "*", 1) == 0) {
				printf (help_list_help_topics);
			} else {
				printf (help_parameter);
			}

		}

		goto Exit;

	}

	if(_strnicmp(_input.cmd_str, "save", 4) == 0)
	{

		sscanf(_input.cmd_str, "%*s %d %s", &images_to_save, user_supplied_file_name);
		goto Exit;

	}

	if(_strnicmp(_input.cmd_str, "list", 4) == 0)
	{

		char argument1 [40] = "";
		char argument2 [40] = "";

		sscanf(_input.cmd_str, "%*s %s %s", argument1, argument2);

		list_tsi_params ((_strnicmp(argument1, "verbose", 6) == 0), argument2);

		goto Exit;

	}

	if(_strnicmp(_input.cmd_str, "about", 5) == 0)
	{

		about_tsi_param (_input.cmd_str);

		goto Exit;

	}

	if(_strnicmp(_input.cmd_str, "reset", 5) == 0)
	{

		if (!_camera->Stop ()) {
			handle_error ("stopping camera");
		} else {
			Sleep (500);
			if (!_camera->ResetCamera ()) {
				handle_error ("resetting camera");
			} else if (!_camera->SetParameter(TSI_PARAM_FRAME_COUNT, (void *)&num_exposures)) {
				handle_error("Unable to set frame count\n");
			} else if (!_camera->SetParameter(TSI_PARAM_EXPOSURE_TIME, (void *)&exposure_time_ms)) {
				handle_error("Unable to set exposure time");
			} else if (!_camera->Start ()) {
				handle_error ("starting camera");
			} else {
				sprintf (info_msg_str, "Reset sent to camera\n");
				printf (info_msg_str);
			}
		}

		goto Exit;

	}

	if(_strnicmp(_input.cmd_str, "dims", 4) == 0)
	{

		char dims_setting_str [80];

		printf ("\n");

		if (sscanf(_input.cmd_str, "%*s %s", dims_setting_str) > 0) {

			if ((_strnicmp(dims_setting_str, "ON", 2) == 0) ||
				(_strnicmp(dims_setting_str, "1", 2)  == 0)) {

				display_dimensions = true;

			} else if ((_strnicmp(dims_setting_str, "OFF", 2) == 0) ||
				(_strnicmp(dims_setting_str, "0", 2)  == 0)) {

				display_dimensions = false;

			}

			printf ("Display Dimensions: %s\n", (display_dimensions ? "ON" : "OFF"));
			
		} else {

			printf ("Display Dimensions - unknown or missing parameter value - %s [ON|OFF]\n", _input.cmd_str);

		}

		if (display_dimensions) {
			display_event_info = false;
		}

	}

	if(_strnicmp(_input.cmd_str, "events", 6) == 0)
	{
		display_event_info = !display_event_info;
		if (display_event_info) {
			display_dimensions = false;
		}
	}

	check_tsi_param (_input.cmd_str);

Exit:

	if (printf_prompt_required) {
		if (!script_active) {
			printf_prompt_required = false;
			printf ("%s", help_str);
		}
	}

	return result;

}


//==============================================================================
// event_handler 
//------------------------------------------------------------------------------
//==============================================================================
static HRESULT WINAPI event_handler(HWND hwnd, UINT type, WPARAM wparam, LPARAM lparam) 
{

    switch(type)
    {
	case WM_CREATE:
        {
           resize_window(hwnd, 0, 0);
        }
	break;

	case WM_SIZE:
        {
           resize_window(hwnd, 0, 0);
        }
	break;

	case WM_PAINT:
        {
           //BeginPaint(hwnd, &p);
           draw_window(hwnd);
           //EndPaint(hwnd, &p);
        }
        break;

	case WM_CLOSE:
        {
           close_window(hwnd);
        }
        break;

	case WM_ERASEBKGND:
        return 1;

	case WM_KEYDOWN:
	case WM_SYSKEYDOWN:
            if(wparam == VK_ESCAPE)
            {
               close_window(hwnd);
            }

	    if(wparam!=VK_HOME) goto def;
	    break;

	case WM_CHAR:
        {
           //printf("%c (0x%02x)\n", (char) wparam, (char)wparam);
           if(((char)wparam) == 0x08)
           {
              _input.cmd_str_index--;
              if(_input.cmd_str_index < 0) _input.cmd_str_index = 0;
             
              _input.cmd_str[_input.cmd_str_index] = 0;
           }
           else if((char)wparam == 0x0d)
           {

		     if (!process_command (hwnd)) {
               close_window(hwnd);
			 }

              memset(_input.cmd_str, 0, 256);
              _input.cmd_str_index = 0;

           }
           else
           {
              if(_input.cmd_str_index < 256)
              {
                 _input.cmd_str[_input.cmd_str_index++] = (char)wparam;
              }
           }

		   if (_input.cmd_str_index > 0) {
			   info_msg_str [0] = 0;
		   }

        }
        break;

	case WM_SYSCHAR:
	    break;

        case WM_LBUTTONDOWN:
        {
           _input.select_active = 0;
           _input.drag_x = GET_X_LPARAM(lparam);
           _input.drag_y = GET_Y_LPARAM(lparam);
           _input.drag_active   = 1;
        }
        break;

        case WM_LBUTTONUP:
        {
           _input.drag_active   = 0;
           _input.select_active = 1;
           _input.select[0]     = _input.drag_x;
           _input.select[1]     = _input.drag_y;
           _input.select[2]     = _input.mouse_x;
           _input.select[3]     = _input.mouse_y;
        }
        break;

        case WM_RBUTTONUP:
        {
           _input.select_active = 0;
        }
        break;

        case WM_MOUSEMOVE:
        {
           _input.mouse_x = GET_X_LPARAM(lparam);
           _input.mouse_y = GET_Y_LPARAM(lparam);
        }
        break;

        case WM_TIMER:
        {
        }
        break;

	default:
	def:
	    return (HRESULT) DefWindowProc(hwnd,type,wparam,lparam);
    }

    return 0;
}



//==============================================================================
// update_window 
//------------------------------------------------------------------------------
//==============================================================================
void update_window(WIN32_WINDOW *window)
{
MSG msg;

   InvalidateRect(window->window_handle, NULL, TRUE);

   SendMessage(window->window_handle, WM_PAINT, 0, 0);

    while(PeekMessage(&msg, window->window_handle, 0, 0, PM_REMOVE))
    {
        TranslateMessage(&msg);
        DispatchMessage (&msg);
    }

   //while(PeekMessage(&msg,NULL,0,0, PM_NOREMOVE))
   //{
   //   GetMessage       (&msg,NULL,0,0);
   //   TranslateMessage (&msg);
   //   DispatchMessage  (&msg);
   //}

   //Sleep(0);

   return;
}


//==============================================================================
// destroy_window 
//------------------------------------------------------------------------------
//==============================================================================
void destroy_window(WIN32_WINDOW *window)
{
   return;
}


BOOL CALLBACK MonitorInfoEnumProc (
	HMONITOR hMonitor,  // handle to display monitor
	HDC hdcMonitor,     // handle to monitor DC
	LPRECT lprcMonitor, // monitor intersection rectangle
	LPARAM dwData       // data
	)
{

	if (NULL != lprcMonitor) {

		if (NumberOfMonitors < MAX_SUPPORTED_MONITORS) {
			MonitorData [NumberOfMonitors++].Rect = *lprcMonitor;
		}

	}

	return TRUE;

}

#ifdef __cplusplus
extern "C" {
#endif


//==============================================================================
// [EXPORTED FUNCTION] - create_window
//------------------------------------------------------------------------------
//==============================================================================
WIN32_WINDOW *create_window(int x, int y, int w, int h, int bitpix, char *name)
{
int           success   = 0;
WIN32_WINDOW *window    = 0;
RECT          rect;

int i      = 0;
int width  = 0;
int height = 0;

	memset (MonitorData, 0, sizeof (MonitorData));

	if (EnumDisplayMonitors(NULL, NULL, (MONITORENUMPROC) MonitorInfoEnumProc, 0)) {

		printf ("EnumDisplayMonitors call successful\n");

		printf ("At least %d monitor(s) detected\n", NumberOfMonitors);
		for (int i = 0; i < NumberOfMonitors; i++) {
			printf (
				"   Monitor %d - Rect: top(%u), left(%u), bottom(%u), right(%u)\n", 
				i,
				MonitorData [i].Rect.top,
				MonitorData [i].Rect.left,
				MonitorData [i].Rect.bottom,
				MonitorData [i].Rect.right
				);
		}

	} else {
		printf ("EnumDisplayMonitors call failed - error %u\n", GetLastError ());
	}

   window = (WIN32_WINDOW *)malloc(sizeof(WIN32_WINDOW));
   if(window == 0) return 0;

   memset(window, 0, sizeof(WIN32_WINDOW));

   _curr_window                        =   window;
   window->terminate                   =   0;
   window->window_class.cbSize         =   sizeof(WNDCLASSEX); 
   window->window_class.style          =   CS_DBLCLKS|CS_HREDRAW|CS_VREDRAW|CS_OWNDC;
   window->window_class.lpfnWndProc    =   (WNDPROC) event_handler;
   window->window_class.hInstance      =   GetModuleHandle(NULL);
   window->window_class.hIcon          =
   window->window_class.hIconSm        =   LoadIcon(GetModuleHandle(NULL),TEXT("Example"));
   window->window_class.hCursor        =   LoadCursor(NULL,IDC_ARROW);
   window->window_class.lpszClassName  =   name;

   window->bitpix                      = bitpix;
   window->bytepix                     = bitpix/8;

   RegisterClassEx(&(window->window_class));

   // For resizing window style
   window->window_style = WS_CLIPSIBLINGS | WS_CLIPCHILDREN | WS_VISIBLE| WS_OVERLAPPEDWINDOW;

   // For non-resizing window style
   //window->window_style = WS_OVERLAPPED|WS_BORDER|WS_CAPTION|WS_VISIBLE|WS_SYSMENU;

   rect.top    = 0;
   rect.left   = 0; 
   rect.right  = w; 
   rect.bottom = h;
   AdjustWindowRectEx(&rect, window->window_style, FALSE, 0);

   window->x = rect.left;
   window->y = rect.top;
   width     = rect.right  - rect.left;
   height    = rect.bottom - rect.top;

   if (NumberOfMonitors > 1) {

	   RECT CurrentRect;

	   ConsoleMonitor = 0;
	   ImagingMonitor = 1;

	   if (GetWindowRect(console_window_handle, &CurrentRect)) {

		   SetWindowPos(
			   GetForegroundWindow(),
			   HWND_TOP,
			   MonitorData [0].Rect.left,
			   MonitorData [0].Rect.top,
			   CurrentRect.right - CurrentRect.left,
			   CurrentRect.bottom - CurrentRect.top,
			   SWP_SHOWWINDOW
			   );

	   }
   }

//printf("create_window - x:%d y:%d w:%d h:%d    width:%d height:%d\n", x, y, w, h, width, height);
   window->window_handle = 
	   CreateWindowEx(
	      WS_EX_ACCEPTFILES,
		  name, 
		  name,
		  window->window_style,
		  x + MonitorData [ImagingMonitor].Rect.left, 
		  y + MonitorData [ImagingMonitor].Rect.top, 
		  width, 
		  height, 
		  0, 
		  NULL, 
		  NULL, 
		  0
		  );

   window->w                   = w;
   window->h                   = h;
   window->update              = update_window;
   window->pixel_buffer_width  = w;
   window->pixel_buffer_height = h;
   window->num_pixels          = w * h;
   window->pixel_buffer.vptr   = (unsigned int *)malloc(window->num_pixels * window->bytepix);

   memset(window->pixel_buffer.vptr, 0, window->num_pixels * window->bytepix);

      // create bitmap header 
   for(i = 0; i < sizeof(BITMAPINFOHEADER)+16; i++)  window->bitmapbuffer[i] = 0;
   window->bitmap_header                                  = (BITMAPINFO *)&(window->bitmapbuffer);
   window->bitmap_header->bmiHeader.biSize                = sizeof(BITMAPINFOHEADER);
   window->bitmap_header->bmiHeader.biPlanes              = 1;
   window->bitmap_header->bmiHeader.biBitCount            = window->bitpix;
   window->bitmap_header->bmiHeader.biCompression         = BI_BITFIELDS;
   window->bitmap_header->bmiHeader.biWidth               =  window->pixel_buffer_width;
   window->bitmap_header->bmiHeader.biHeight              = -window->pixel_buffer_height;  // note well

   if(window->bitpix == 32)
   {
      ((unsigned long *)window->bitmap_header->bmiColors)[0] = 0x00FF0000;
      ((unsigned long *)window->bitmap_header->bmiColors)[1] = 0x0000FF00;
      ((unsigned long *)window->bitmap_header->bmiColors)[2] = 0x000000FF;
   }
   else
   {
      ((unsigned long *)window->bitmap_header->bmiColors)[0] = 0x0000F800;
      ((unsigned long *)window->bitmap_header->bmiColors)[1] = 0x000007E0;
      ((unsigned long *)window->bitmap_header->bmiColors)[2] = 0x0000001F;
      //0x001F, the green mask is 0x07E0, and the red mask is 0xF800.
   }

   // get window dc
   window->window_dc = GetDC(window->window_handle);

   add_to_window_list(window);

   return (window);
}


/*
int bin_image(int w, int h, int bitpix, int bytpix, int vbin, int hbin, void *pixel_buffer)
{
int i = 0;
int j = 0;

   // Bin horizontal first.
   for(i=0;i<h;i++)
   {
      for(j=0;j<w;j++)
      {
         if(j%hbin == 0) pix_accum = 0; 
         dest[index] = 
      }
   }

   // Bin vertical.

} 

*/
//==============================================================================
// display_begin
//------------------------------------------------------------------------------
//==============================================================================
void display_begin(WIN32_WINDOW *window)
{
}

//==============================================================================
// display_end
//------------------------------------------------------------------------------
//==============================================================================
void display_end(WIN32_WINDOW *window)
{
}

//==============================================================================
// display_clear
//------------------------------------------------------------------------------
//==============================================================================
void display_clear(WIN32_WINDOW *window)
{
int i     = 0;
int j     = 0;
int win_w = 0;
int win_h = 0;
int index = 0;

   win_w = window->pixel_buffer_width;
   win_h = window->pixel_buffer_height;

   for(i=0;i<win_h;i++)
   {
      for(j=0;j<win_w;j++)
      {
         index = (i * win_w) + j;
         window->pixel_buffer.ui32[index] = 0;
      }
   }
   ///memset(window->pixel_buffer.ui32, 1, window->pixel_buffer_size_in_bytes);
}

//==============================================================================
// display_gui
//------------------------------------------------------------------------------
//==============================================================================
void display_gui(WIN32_WINDOW *window)
{

   char *prompt;

   if(_input.drag_active == 1)
   {
      draw_rect(window, _input.drag_x, _input.drag_y, _input.mouse_x, _input.mouse_y, 0x00FF00FF);
   }
   else if(_input.select_active == 1)
   {
      draw_rect(window, _input.select[0], _input.select[1], _input.select[2], _input.select[3], 0x0000FF00); 
      //draw_rect_solid(window, _input.select[0], _input.select[1], 100, 100, 0x000FFF00); 
   }

   if (_input.cmd_str [0] != 0) {

		prompt = _input.cmd_str;

   } else if (info_msg_str [0] != 0) {

		prompt = info_msg_str;

   } else {

		prompt = help_str;

   }

   if (prompt == _input.cmd_str) {

	   draw_text(window, ">",  4, 11, 0x00000000); 
	   draw_text(window, ">",  2,  9, 0x00000000); 
	   draw_text(window, ">",  4,  9, 0x00000000); 
	   draw_text(window, ">",  2, 11, 0x00000000); 
	   draw_text(window, ">",  3, 10, 0x00FFFF00); 

   }

   draw_text(window, prompt, 11, 11, 0x00000000); 
   draw_text(window, prompt,  9,  9, 0x00000000); 
   draw_text(window, prompt, 11,  9, 0x00000000); 
   draw_text(window, prompt,  9, 11, 0x00000000); 
   draw_text(window, prompt, 10, 10, 0x00FFFF00); 

   if (dimension_str [0] > 0) {
	   draw_text(window, dimension_str, 11, 31, 0x00000000); 
	   draw_text(window, dimension_str,  9, 29, 0x00000000); 
	   draw_text(window, dimension_str, 11, 29, 0x00000000); 
	   draw_text(window, dimension_str,  9, 31, 0x00000000); 
	   draw_text(window, dimension_str, 10, 30, 0x00FFFF00); 
   }

   if (display_event_info) {

	   char event_info_str [256];

       EnterCriticalSection(&CtlEventCriticalSection);

	   sprintf (
		   event_info_str, 
		   "%3d: Frame(%d) - %02d-%02d-%02d %02d:%02d:%02d.%02d.%02d\n",
		   cur_ctl_event,
		   cur_ctl_event_info.FrameNumber,
		   cur_ctl_event_info.TimeStamp.Year,
		   cur_ctl_event_info.TimeStamp.Month,
		   cur_ctl_event_info.TimeStamp.Day,
		   cur_ctl_event_info.TimeStamp.Hour,
		   cur_ctl_event_info.TimeStamp.Min,
		   cur_ctl_event_info.TimeStamp.Sec,
		   cur_ctl_event_info.TimeStamp.MS,
		   cur_ctl_event_info.TimeStamp.US
		   );

		LeaveCriticalSection (&CtlEventCriticalSection);

		draw_text(window, event_info_str, 11, 31, 0x00000000); 
		draw_text(window, event_info_str,  9, 29, 0x00000000); 
		draw_text(window, event_info_str, 11, 29, 0x00000000); 
		draw_text(window, event_info_str,  9, 31, 0x00000000); 
		draw_text(window, event_info_str, 10, 30, 0x00FFFF00); 
		
		draw_text(window, image_info_str, 11, 41, 0x00000000); 
		draw_text(window, image_info_str,  9, 39, 0x00000000); 
		draw_text(window, image_info_str, 11, 39, 0x00000000); 
		draw_text(window, image_info_str,  9, 41, 0x00000000); 
		draw_text(window, image_info_str, 10, 40, 0x00FFFF00); 

   }

}


//==============================================================================
// display_image
//------------------------------------------------------------------------------
//==============================================================================
int display_image(WIN32_WINDOW *window, TsiImage *image)
{
unsigned int i = 0;
unsigned int j = 0;
unsigned int value = 0;
unsigned int width = 0;

unsigned int src_index = 0;
unsigned int dst_index = 0;

unsigned int win_w = 0;
unsigned int win_h = 0;

unsigned int pix_max = 0;
unsigned int pix_min = 0;

   if((window == 0) || (image == 0)) return 0;

   if((window->pixel_buffer_width  != image->m_Width ) ||
      (window->pixel_buffer_height != image->m_Height))
   {

      free(window->pixel_buffer.vptr);

      window->pixel_buffer.vptr   = 0;
      window->pixel_buffer_width  = 0;
      window->pixel_buffer_height = 0;

      window->pixel_buffer.vptr = (unsigned int *)malloc(image->m_SizeInPixels * window->bytepix);
      if(window->pixel_buffer.vptr == 0)
      {
         return 0;
      }

      window->num_pixels                        = image->m_SizeInPixels;
      window->pixel_buffer_size_in_bytes        = image->m_SizeInPixels * window->bytepix;

      window->pixel_buffer_width                = image->m_Width;
      window->pixel_buffer_height               = image->m_Height;

      window->bitmap_header->bmiHeader.biWidth  =  window->pixel_buffer_width;
      window->bitmap_header->bmiHeader.biHeight = -window->pixel_buffer_height;

   }

   if (display_dimensions) {
	   sprintf (dimension_str, "Image: %u, %u", image->m_Width, image->m_Height);
   } else {
	   dimension_str [0] = 0;
   }

   if (display_event_info) {
	   sprintf (image_info_str, "Img: Frame(%d)\n", image->m_FrameNumber);
   } else {
	   image_info_str [0] = 0;
   }

   win_w = window->pixel_buffer_width;
   win_h = window->pixel_buffer_height;

   if(image->m_BytesPerPixel == 2)
   {
      if(window->bitpix == 16)
      {
         for(i = 0; i < (unsigned int) window->num_pixels; i++)
         {
            value = (image->m_PixelData.ui16[i] & 0x001F);
            value = (value | (value << 6) | (value << 11));
            window->pixel_buffer.ui16[i] = value;
         }
      }
      else if(window->bitpix == 32)
      {
      //------------------------------------------------------------------------
         pix_max = 0;
         pix_min = 0xFFFF;
         for(i=0;i<image->m_SizeInPixels;i++)
         {
            if(image->m_PixelData.ui16[i] < pix_min) pix_min = image->m_PixelData.ui16[i];
            if(image->m_PixelData.ui16[i] > pix_max) pix_max = image->m_PixelData.ui16[i];
         }

         for(i=0;i<win_h;i++)
         {
            for(j=0;j<win_w;j++)
            {
               dst_index = (i * win_w) + j;

               if((i < image->m_Height) && (j < image->m_Width))
               {
                  src_index = (i * image->m_Width) + j;
				  if ((pix_max - pix_min) > 0) {
					value = (image->m_PixelData.ui16[src_index] - pix_min) * 255 / (pix_max - pix_min);
				  } else {
					value = 0;
				  }
               }
               else
               {
                  value = 0x00FF0000;
               }
               
               //value = value & 0x000000FF;

               value = value | (value << 8) | (value << 16);
               window->pixel_buffer.ui32[dst_index] = value ;
            }
         }
      }
   }

   return 1;
}


void _tWinMainCRTStartup(void)
{
}



//------------------------------------------------------------------------------
// get_tsi_sdk
//------------------------------------------------------------------------------
static TsiSDK *get_tsi_sdk(char *path)
{
TsiSDK        *tsi_sdk        = 0;
TSI_CREATE_SDK tsi_create_sdk = 0;

DWORD  last_error = 0;
char *msgbuf = 0;

   _tsi_dll_handle = LoadLibraryA("thorlabs_ccd_tsi_sdk.dll"); 
   if(_tsi_dll_handle == 0)  
   {
      printf("***ERROR***: LoadLibraryA(\"thorlabs_ccd_tsi_sdk.dll\") failed  - ");
      last_error = GetLastError(); 
      FormatMessageA( FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM,
                     0,
                     last_error,
                     MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
                     msgbuf,
                     sizeof(msgbuf)/sizeof(msgbuf[0]),
                     NULL );

      if(msgbuf != 0)
      {
         printf("%s", msgbuf);
      }
      else
      {
         printf("can't find thorlabs_ccd_tsi_sdk.dll\n");
      }

      LocalFree(msgbuf);
      return tsi_sdk; 
   }

   tsi_create_sdk = (TSI_CREATE_SDK)GetProcAddress(_tsi_dll_handle, "tsi_create_sdk");
   if(tsi_create_sdk == 0)
   {
      FreeLibrary(_tsi_dll_handle);
      _tsi_dll_handle = 0;
      return tsi_sdk;
   }

   tsi_sdk = tsi_create_sdk();

   return tsi_sdk; 
}

//------------------------------------------------------------------------------
// release_tsi_sdk
//------------------------------------------------------------------------------
static void release_tsi_sdk(TsiSDK *tsi_sdk)
{
TSI_DESTROY_SDK tsi_destroy_sdk = 0;

   if(_tsi_dll_handle != 0)
   {
      tsi_destroy_sdk = (TSI_DESTROY_SDK)GetProcAddress(_tsi_dll_handle, "tsi_destroy_sdk");
      if(tsi_destroy_sdk != 0)
      {
         tsi_destroy_sdk(tsi_sdk);
      }

      FreeLibrary(_tsi_dll_handle);
      _tsi_dll_handle = 0;
   }
}



//==============================================================================
// check_script 
//------------------------------------------------------------------------------
//==============================================================================
bool check_script (WIN32_WINDOW *window)
{

	bool return_value = true;

	script_active = false;

	if (NULL != script_file) {

		if (!feof (script_file)) {

			int i = 0;

			script_active = true;

			fgets (_input.cmd_str, MAX_CMD_STR, script_file);
			printf ("\nScript Command: %s\n", _input.cmd_str);

			// comments on a line

			for (int i = 0; i < (MAX_CMD_STR - 2); i++) {
				if (strncmp(&_input.cmd_str [i], "//", 2) == 0) {
					_input.cmd_str [i] = 0;
					break;
				}
			}

			// If there's something to process (not a blank line or comment)

			if (strlen(_input.cmd_str) > 0) {

				return_value = process_command (window->window_handle);

				if (!return_value) {
					fclose (script_file);
					script_file = NULL;
				}

			}

			memset(_input.cmd_str, 0, 256);
			_input.cmd_str_index = 0;			

		} else {

			fclose (script_file);
			script_file = NULL;

		}
	}

	return return_value;

}

//==============================================================================
// main
//------------------------------------------------------------------------------
//==============================================================================

HANDLE _console_handle = 0;

int main(int argc, char *argv[])
{
	WIN32_WINDOW *window            = 0;
	TsiSDK       *sdk               = 0;
	int           num_cameras       = 0;
	int           key               = 0;
	bool          success           = false;
	TsiImage     *image             = 0;
	TsiImage     *prev_image        = 0;

	uint16_t	 *error_fill_image  = NULL;

	RECT rect;

	int num_loops                   = -1;

	int i                           = 0;
	int w                           = 0;
	int h                           = 0;
	int value                       = 0;

	char *platform[2] = {"32bit", "64bit"};

	char str[256]		            = "";
	int hbin                        = 1;
	int vbin                        = 1;

	int camera_index                = -1;
	int quit                        = 1;

	int subimage[4];

	int speed_index		            = -1;

	int return_value                = 0;

	int save_image_num	            = 0;
	FILE *output_file               = NULL;

	subimage[0] = -1;
	subimage[1] = -1;
	subimage[2] = -1;
	subimage[3] = -1;

	_os_64bit = is_os_64bit();

#ifdef _WIN64
	_app_64bit = 1;
#endif

	printf("\ntsi_sample - %s app running on a %s OS\n", platform[_app_64bit], platform[_os_64bit]);

	memset(&_input, 0, sizeof(INPUT_DATA));

	// Initialize the test critical section one time only.

	if (!InitializeCriticalSectionAndSpinCount(&ScreenUpdateCriticalSection, 0x0) ) {
		printf ("Could not initialize screen update critical section\n");
		return 0;
	}

	if (!InitializeCriticalSectionAndSpinCount(&CtlEventCriticalSection, 0x0) ) {
		printf ("Could not initialize control event critical section\n");
		return 0;
	}

	// Echo command line

	printf ("\nCommand Line: >");
	for (int param_num = 0; param_num < argc; param_num++) {
		printf ("%s ", argv [param_num]);
	}
	printf ("\n\n");

	// Process command line

	if(argc > 1) {

		if ('*' == *argv[1]) {
			camera_index = -1;
		} else {
			camera_index     = atoi(argv[1]);
		}

	} else {

		printf("usage  : tsi_sample <camera_index> <exposure_time_ms> <num_frames> <hbin> <vbin> <x1> <y1> <x2> <y2>\n");  
		printf("example: tsi_sample 1 1000 10 2 2 0 0 512 512\n");

		camera_index = -1;

	}

	if(argc > 2){
		exposure_time_ms = atoi(argv[2]); 
	} else {
		exposure_time_ms = 5; 
	}

	if (-1 == camera_index) {
		printf (
			"Camera Index (*), Exposure Time (%u ms), Exposures (%u)\n",
			exposure_time_ms,
			num_exposures
			);
	} else {
		printf (
			"Camera Index (%u), Exposure Time (%u ms), Exposures (%u)\n",
			camera_index,
			exposure_time_ms,
			num_exposures
			);
	}

	if(argc > 3){
		num_exposures    = atoi(argv[3]); 
	}

	if(argc > 4){
		hbin             = atoi(argv[4]);
	}

	if(argc > 5){
		vbin             = atoi(argv[5]);
	}

	printf (
		"hbin (%u), vbin (%u)\n",
		hbin, 
		vbin
		);

	if(argc > 9){

		subimage[0]      = atoi(argv[6]);
		subimage[1]      = atoi(argv[7]);
		subimage[2]      = atoi(argv[8]);
		subimage[3]      = atoi(argv[9]);

		printf (
			"roi: XOrigin(%u), YOrigin(%u), XSize(%u), YSize(%u)\n",
			subimage[0],
			subimage[1],
			subimage[2],
			subimage[3] 
		);

	} else {

		printf ("roi: Automatic / Full Frame\n");

	}

	if(argc == 11) {
		speed_index = atoi(argv[10]);
		if (speed_index < 2) {
			printf (
				"speed index (%u)\n",
				speed_index
				);
		} else {
			printf (
				"invalid speed index (%u) - must be 0-20Mhz, or 1-40Mhz\n",
				speed_index
				);
			speed_index = -1;
		}
	}

	if(argc == 12) {
		if(_strnicmp(argv [10], "-script", 7) == 0) {
			strncpy (script_file_name, argv [11], MAX_PATH);
			script_file = fopen (script_file_name, "rt");
			if (NULL == script_file) {
				printf ("Error %d: Could not open script file %s\n", errno, script_file_name);
				return_value = 0;
				goto Exit;
			}
		}
	}

	sdk = get_tsi_sdk(0);
	if(sdk == 0)
	{
		printf("***ERROR***: get_tsi_sdk() failed\n");
		return_value = 0;
		goto Exit;
	}

	if (!sdk->Open()) {
		printf("***ERROR***: sdk->Open() failed\n");
		return_value = 0;
		goto Exit;
	}

	num_cameras = sdk->GetNumberOfCameras();
	printf("num_cameras:%d\n", num_cameras);
	if (num_cameras == 0)
	{
		return_value = 0;
		goto Exit;
	}

	if (-1 == camera_index) {

		bool done;

		printf("\n");
		printf("=====================================\n");
		printf(" Available Cameras\n");
		printf("=====================================\n");

		for (int i = 0; i < num_cameras; i++) {

			_camera = sdk->GetCamera(i);

			if (0 == _camera) {
				printf("***ERROR***: could not get camera handle for camera number %d\n", i);
				goto Exit;
			} else {

				if (_camera->Open ()) {

					char *CameraName			= _camera->GetCameraName ();
					char *CameraGlobalName;
					char *CameraInterfaceName	= sdk->GetCameraInterfaceTypeStr (i);

					char CameraNameBuffer [1024] = {0};

					if (NULL == CameraName) {
						printf("***ERROR***: could not get camera name for camera number %d\n", i);
						goto Exit;
					} else {

						if (!_camera->GetParameter (TSI_PARAM_GLOBAL_CAMERA_NAME, sizeof(CameraNameBuffer), CameraNameBuffer)) {
							sprintf (CameraNameBuffer, "Camera %d", i);
						}

						if (0 == *CameraName) {
							CameraName = CameraNameBuffer;
						}

						CameraGlobalName = CameraNameBuffer;

					}

					printf ("  %3d: %s - %s - %s\n", i + 1, CameraName, CameraGlobalName, CameraInterfaceName);

					_camera->Close ();

				}

			}

		}
		
		printf("=====================================\n\n");

		do {

			printf("  Select a camera (1..%u), q to exit... > ", num_cameras);

			int ch = _getch ();

			ch = toupper (ch);

			if ((ch >= ' ') && (ch <= '~')) {
				printf("%c", (char) ch);
			} else if (ch == '\x1B') {
				printf("Esc/Quit");
			} else {
				printf("???");
			}

			done = true;

			if ((ch >= '1') && (ch <= '9')) {
				camera_index = ch - '0' - 1;
			} else if (('Q' == ch) || ('\x1B' == ch)) {
				printf (" - Program Exiting\n\n");
				goto Exit;
			} else {
				printf (" - Invalid Selection");
				done = false;
			}

			printf("\n\n");

		} while (!done);

	} else if((camera_index >= num_cameras) || (camera_index < 0)) {

		printf("***ERROR***: camera_index:%d is not valid\n", camera_index);
		return_value = 0;
		goto Exit;

	}

	_camera = sdk->GetCamera(camera_index);
	if(_camera == 0)
	{
		printf("error: sdk->GetCamera(%d) returned 0\n", camera_index);
		sdk->Close();
		return_value = 0;
		goto Exit;
	}

	if (!_camera->Open()) {
		handle_error ("Could not open camera");
		goto Exit;
	} else {

		char CameraName [128];

		if (strncpy (CameraName, _camera->GetCameraName(), 127)) {
			printf ("Camera %d Name: %s\n", camera_index, CameraName);
		} else {
			handle_error ("Could not retrieve Camera Name\n");
		}

		str [0] = 0;
		if (_camera->GetParameter(TSI_PARAM_FW_VER,     256, str)) {
			printf("Firmware Version     :%s\n", str);
		} else {
			handle_error("Could not retrieve Firmware Version");
		}

		str [0] = 0;
		if (_camera->GetParameter(TSI_PARAM_HW_VER,     256, str)) {
			printf("Hardware Version     :%s\n", str);
		} else {
			handle_error("Could not retrieve Hardware Version");
		}

		str [0] = 0;
		if (_camera->GetParameter(TSI_PARAM_HW_MODEL,   256, str)) {
			printf("Hardware Model       :%s\n", str);
		} else {
			handle_error("Could not retrieve Hardware Model\n");
			_camera->ClearError ();
		}

		str [0] = 0;
		if (_camera->GetParameter(TSI_PARAM_HW_SER_NUM, 256, str)) {
			printf("Hardware Serial Num  :%s\n", str);
		} else {
			handle_error("Could not retrieve Hardware Serial Num, error %u");
		}

		if (!_camera->SetParameter(TSI_PARAM_EXPOSURE_UNIT, (void *)&exposure_unit_ms)) {
			handle_error("Unable to set exposure time");
		}

		if (!_camera->SetParameter(TSI_PARAM_EXPOSURE_TIME, (void *)&exposure_time_ms)) {
			handle_error("Unable to set exposure time");
		}

		if (_camera->GetParameter(TSI_PARAM_HW_SER_NUM, 256, str)) {
			printf("Hardware Serial Num  :%s\n", str);
		} else {
			handle_error("Could not retrieve Hardware Serial Num");
		}

		if (-1 == subimage[0]) {

			// Discover sensor dimensions

			subimage[0] = 0;
			subimage[1] = 0;

			if (!_camera->GetParameter(TSI_PARAM_HSIZE, sizeof (subimage[2]), &subimage[2])) {
				subimage[2] = 1392;
			}

			if (!_camera->GetParameter(TSI_PARAM_VSIZE, sizeof (subimage[3]), &subimage[3])) {
				subimage[3] = 1040;
			}

		}

		memset(&initial_tsi_roi_bin, 0, sizeof(TSI_ROI_BIN));

		initial_tsi_roi_bin.XBin    = hbin;
		initial_tsi_roi_bin.YBin    = vbin;
		initial_tsi_roi_bin.XOrigin = subimage[0];
		initial_tsi_roi_bin.YOrigin = subimage[1];
		initial_tsi_roi_bin.XPixels = subimage[2];
		initial_tsi_roi_bin.YPixels = subimage[3];

		current_tsi_roi_bin = initial_tsi_roi_bin;

		expected_image_size_in_bytes	= 
			(current_tsi_roi_bin.XPixels / current_tsi_roi_bin.XBin) *
			(current_tsi_roi_bin.YPixels / current_tsi_roi_bin.YBin) * 2;  // 2 bytes per pixel

		// Build an "error" image with pseudo-snow

		error_fill_image = (uint16_t *) malloc (expected_image_size_in_bytes);
		if (NULL == error_fill_image) {
			printf("Unable to allocate error_fill_image\n");
			return_value = 0;
			goto Exit;
		}

		srand ((int) GetTickCount ());

		// This is for a 12 bit camera...

		for (int i = 0; i < (expected_image_size_in_bytes / 2); i++) {
			error_fill_image [i] = ((uint16_t) rand ()) & 0x0FFF;
		}

		if (!_camera->SetParameter(TSI_PARAM_ROI_BIN, (void *)&initial_tsi_roi_bin)) {
			handle_error("Unable to set ROI\n");
		}

		if (!_camera->SetParameter(TSI_PARAM_FRAME_COUNT, (void *)&num_exposures)) {
			handle_error("Unable to set frame count\n");
		}

		//camera->RegisterEventHandler(camera_event_handler, 0);
		//camera->RegisterForEvent(CAMERA_EVENT_SEQUENCE_COMPLETE);

		console_window_handle = GetForegroundWindow();

		window = create_window(0, 0, 1392, 1040, 32, "TSI_SAMPLE  -  Press \'Esc\' to exit");
		if(window == 0) {
			return_value = 0;
			goto Exit;
		}

		if ((speed_index == 0) || (speed_index == 1)) {
			_camera->SetParameter(TSI_PARAM_READOUT_SPEED_INDEX, (void *)&speed_index);
		}
		_camera->SetCameraControlCallbackEx (control_callback, NULL);

		rect.top    = 100;
		rect.left   = 100;
		rect.right  = 150;
		rect.bottom = 150;

		camera_running = _camera->Start();
		if (!camera_running) {
			printf("Camera failed to start, error %u\n", _camera->GetErrorCode ());
			_camera->ClearError ();
			window->terminate = 1;
		}

		printf ("\n\n");
		printf ("%s", help_str);
		printf_prompt_required = true;

		while(window->terminate == 0)
		{

			// If someone types a key in the main (text) window, route it to the graphics window for
			// for processing.

			if (_kbhit ()) {

				unsigned char ch = (unsigned char) _getch ();

				// Echo the character as appropriate

				switch (ch) {

					case 0x08 :
						if (0 != *_input.cmd_str) {
							_putch (ch);
							_putch (' ');
							_putch (ch);
						}
						break;

					case 0x0D :
						printf ("\n");
						printf_prompt_required = true;
						break;

					case VK_ESCAPE :
						window->terminate = 1;
						break;

					default :
						if ((ch >= ' ') && (ch <= '~')) {
							_putch (ch);
						}
						break;

				}

				// Send it to the graphics window

				LRESULT Result = SendMessage (window->window_handle, WM_CHAR, (WPARAM) ch, 0);
				if (Result != 0) {
					printf ("Return Code %d\n", Result);
				}

			}

			EnterCriticalSection(&ScreenUpdateCriticalSection);

			window->update(window);

			display_begin(window);

			image = _camera->GetPendingImage(); 
			if(image != 0)
			{

				clear_display = false;

				if (images_to_save) {

					if (save_image_num == 0) {

						char output_file_name [64];

						if (user_supplied_file_name [0] != 0) {
							strncpy (output_file_name, user_supplied_file_name, sizeof (output_file_name));
							user_supplied_file_name [0] = 0;
						} else {
							sprintf (output_file_name, "tsi_sample_img_%d_imgs.raw", images_to_save);
						}

						output_file = fopen (output_file_name, "wb");

						if (NULL == output_file) {
							printf ("Save Error (%u): Opening %s\n", errno, output_file_name);
							images_to_save = 0;
							save_image_num = 0;
						}

					}

					if (output_file) {

						size_t BytesToWrite = expected_image_size_in_bytes;
						size_t BytesToFill  = 0;

						if (image->m_SizeInBytes != expected_image_size_in_bytes) {

							printf ("Error: Saving image %d - size in bytes (%u) - expected bytes (%u)\n", save_image_num, image->m_SizeInBytes, expected_image_size_in_bytes);

							if (0 == image->m_SizeInBytes) {
								printf ("Substituting snow filled frame for zero byte frame\n");
								BytesToWrite = 0;
								BytesToFill  = expected_image_size_in_bytes;
							} else if ((long) image->m_SizeInBytes > expected_image_size_in_bytes) {
								printf ("Truncating oversize frame\n");
							} else {
								printf ("Padding short frame with snow\n");
								BytesToWrite = image->m_SizeInBytes;
								BytesToFill  = expected_image_size_in_bytes - image->m_SizeInBytes;
							}

						} else {
							printf ("Saving image %d - size in bytes (%u)\n", save_image_num, image->m_SizeInBytes);
						}

						fwrite (image->m_PixelData.vptr, 1, BytesToWrite, output_file);
						fwrite (error_fill_image,        1, BytesToFill,  output_file);

						save_image_num++;
						images_to_save--;

					}

					if (images_to_save == 0) {

						sprintf (info_msg_str, "%u images saved\n", save_image_num);

						if (output_file) {
							fclose (output_file);
						}

						save_image_num = 0;

					}

				}

				if(prev_image)
				{
					_camera->FreeImage(prev_image);
				}
				prev_image = image;

			}

			if (0 == images_to_save) {
				if (!check_script (window)) {
					close_window(window->window_handle);
				}

			}

			if (clear_display) {
				display_clear(window);
			} else {
				if (prev_image) {
					display_image(window, prev_image);
				} else {
					display_clear(window);
				}
			}

			display_gui(window);
			display_end(window);

			LeaveCriticalSection(&ScreenUpdateCriticalSection);

		}

		_camera->Stop();

		_camera->Close();

	}

Exit :

	if (NULL != sdk) {

		sdk->Close();

		release_tsi_sdk(sdk);

	}

	if (NULL != script_file) {
		fclose (script_file);
	}

	// Release resources used by the critical section objects.

	DeleteCriticalSection (&ScreenUpdateCriticalSection);
	return return_value;

} // main

#ifdef __cplusplus
}
#endif
