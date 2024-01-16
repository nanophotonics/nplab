#pragma once

//------------------------------------------------------------------------------
// Platform specific defines.
//------------------------------------------------------------------------------
#if defined(_MSC_VER)                                            
   #define FORCE_INLINE  __forceinline
   #define NEVER_INLINE  __declspec(noinline)

#ifdef DISABLE_STDINT_DEFINES
#else

#if _MSC_VER >= 1800
#include <cstdint>
#else
   typedef char				int8_t;
   typedef short			int16_t;
   typedef long				int32_t;

   typedef unsigned char    uint8_t;
   typedef unsigned short   uint16_t;
   typedef unsigned long    uint32_t;

   #if _MSC_VER   <= 1400 
   typedef unsigned __int64   uint64_t;
   #else
   typedef unsigned long long uint64_t;
   #endif
#endif

#endif // DISABLE_STDINT_DEFINES

#else
   #define FORCE_INLINE __attribute__((always_inline))
   #define NEVER_INLINE __attribute__((noinline))

   #include <stdint.h>
#endif
