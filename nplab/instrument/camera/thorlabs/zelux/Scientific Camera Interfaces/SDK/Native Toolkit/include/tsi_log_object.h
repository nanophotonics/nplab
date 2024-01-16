#pragma once

#include <string>
#include <cstdarg>
#include <cstring>
#ifdef _WIN32
#include <Windows.h>
#endif
#ifdef __linux__
#include <dlfcn.h>
#endif // __linux__
#include "tsi_log.h"

#define __FILENAME__ (strrchr(__FILE__, '\\') ? strrchr(__FILE__, '\\') + 1 : __FILE__)
#define DEFAULT_CONFIG_FILE_NAME_ "thorlabs_tsi_logger.cfg"

class Tsi_log_object
{
public:
   explicit Tsi_log_object (const char* const moduleID) try
                                                      : m_handle (0)
                                                      , m_logger (nullptr)
                                                      , m_log (nullptr)
                                                      , m_status (false)
                                                      , m_moduleID (moduleID)
                                                      , m_groupID ("")
                                                      , m_configFileName(DEFAULT_CONFIG_FILE_NAME_)
   {
      init();
   }
   catch (...)
   {
   }

   Tsi_log_object (const char* const moduleID, const char* const groupID) try
                                                                      : m_handle (0)
                                                                      , m_logger (nullptr)
                                                                      , m_log(nullptr)
                                                                      , m_status (false)
                                                                      , m_moduleID (moduleID)
                                                                      , m_groupID (groupID)
                                                                      , m_configFileName(DEFAULT_CONFIG_FILE_NAME_)
   {
      init();
   }
   catch (...)
   {
   }

   Tsi_log_object(const char* const moduleID, const char* const groupID, const char* const configFileName) try
       : m_handle(0)
       , m_logger(nullptr)
       , m_log(nullptr)
       , m_status(false)
       , m_moduleID(moduleID)
       , m_groupID(groupID)
       , m_configFileName(configFileName)
   {
       init();
   }
   catch (...)
   {
   }

   ~Tsi_log_object()
   {
      try
      {
         if (m_handle)
         {
            // Clean up the logger.
#ifdef _WIN32
            if (const TSI_FREE_LOG tsiFreeLog = (TSI_FREE_LOG) ::GetProcAddress (m_handle, "tsi_free_log"))
#endif // _WIN32
#ifdef __linux__
            if (TSI_FREE_LOG tsiFreeLog = (TSI_FREE_LOG) dlsym (m_handle, "tsi_free_log"))
#endif // __linux__
               tsiFreeLog (m_moduleID.c_str(), m_groupID.c_str());

            // Free the log DLL.
#ifdef _WIN32
            ::FreeLibrary (m_handle);
#endif // _WIN32
#ifdef __linux__
            dlclose (m_handle);
#endif
         }
      }
      catch (...)
      {
      }
   }

   Tsi_log_object (Tsi_log_object&& other) : m_handle (other.m_handle)
                                           , m_logger (other.m_logger)
                                           , m_log (other.m_log)
                                           , m_status (other.m_status)
                                           , m_moduleID (std::move (other.m_moduleID))
                                           , m_groupID (std::move (other.m_groupID))
   {
      other.m_handle = NULL;
      other.m_logger = nullptr;
      other.m_log = nullptr;
   }

   // Get the logger status.
   operator bool() { return (m_status); }

   bool log (TSI_LOG_PRIORITY priority, const char* const file_name, int file_line, const char* const function_name, const char* const msg, ...)
   {
       if (!m_status) return (false);

       // Process the variadic argument list.
       std::string msg_buffer;
       va_list args;
       va_start(args, msg);
       va_list args2;
       va_copy(args2, args);

       // Compute the length of all the arguments in aggregate.
       const int length = vsnprintf(NULL, 0, msg, args);
       if (length < 0)
       {
           va_end(args);
           va_end(args2);
           return (false);
       }
       msg_buffer.resize(length);
       std::vsprintf(const_cast <char*> (msg_buffer.data()), msg, args2);
       va_end(args);
       va_end(args2);

       return (!m_log (m_logger, priority, file_name, file_line, function_name, msg_buffer.c_str()));
   }

   bool is_valid() const
   {
       return m_log != nullptr;
   }

private:
#ifdef _WIN32
   HMODULE m_handle;
#endif // _WIN32
#ifdef __linux__
   void* m_handle;
#endif // __linux__
   void* m_logger;
   TSI_LOG m_log;
   bool m_status;
   const std::string m_moduleID;
   const std::string m_groupID;
   const std::string m_configFileName;

   void init()
   {
      // Load the log DLL.
#ifdef _WIN32
      if (!(m_handle = ::LoadLibrary ("thorlabs_tsi_logger.dll"))) return;
#endif // _WIN32

#ifdef __linux__
      if (!(m_handle = dlopen ("libthorlabs_tsi_logger.so", RTLD_LAZY))) return;
#endif // __linux__

      // Get a handle to a logger;
#ifdef _WIN32
      if (const TSI_GET_LOG tsiGetLog = reinterpret_cast <TSI_GET_LOG> (::GetProcAddress (m_handle, "tsi_get_log")))
#endif // _WIN32
#ifdef __linux
      if (TSI_GET_LOG tsiGetLog = reinterpret_cast <TSI_GET_LOG> (dlsym (m_handle, "tsi_get_log")))
#endif // __linux
      {
         m_logger = tsiGetLog (m_moduleID.c_str(), m_groupID.c_str(), m_configFileName.c_str());
         if (!m_logger) return;
      }
      else return;

#ifdef _WIN32
      if (!(m_log = reinterpret_cast <TSI_LOG> (::GetProcAddress(m_handle, "tsi_log")))) return;
#endif // _WIN32
#ifdef __linux__
      if (!(m_log = reinterpret_cast <TSI_LOG> (dlsym (m_handle, "tsi_log")))) return;
#endif // __linux__

      // We succeeded!
      m_status = true;
   }
};
