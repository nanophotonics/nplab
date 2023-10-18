/*
* Copyright 2019 by Thorlabs, Inc.  All rights reserved.  Unauthorized use (including,
* without limitation, distribution and copying) is strictly prohibited.  All use requires, and is
* subject to, explicit written authorization and nondisclosure agreements with Thorlabs, Inc.
*/

#pragma once

/*! \file tl_polarization_processor_enums.h
*   \brief This file includes the declarations of all the enumerations used by the TSI polarization processor component.
*/

/*! The TL_POLARIZATION_PROCESSOR_POLAR_PHASE enumeration lists all the possible values (in degrees)
*   that a pixel in a polarization sensor could assume.
*
*   The polarization phase pattern is
*
*   <pre>
*   -----------------------
*   |          |          |
*   |    0     |   -45    |
*   |          |          |
*   -----------------------
*   |          |          |
*   |    45    |    90    |
*   |          |          |
*   -----------------------
*   </pre>
*
*
*   The primitive pattern shown above represents the fundamental polarization phase arrangement in a polarization
*   sensor.  The basic pattern would extend in the X and Y directions in a real polarization sensor containing
*   millions of pixels.
*
*   Notice that the phase of the origin (0, 0) pixel logically determines the phase of every other pixel.
*
*   It is for this reason that the phase of this origin pixel is termed the polarization "phase" because it represents
*   the reference point for the phase determination of all other pixels.
*
*   Every TSI polarization camera provides the sensor specific polarization phase of the full frame origin pixel as a discoverable parameter.
*/
enum TL_POLARIZATION_PROCESSOR_POLAR_PHASE
{
    TL_POLARIZATION_PROCESSOR_POLAR_PHASE_0_DEGREES /*!< 0 degrees polarization phase */
  , TL_POLARIZATION_PROCESSOR_POLAR_PHASE_45_DEGREES /*!< 45 degrees polarization phase */
  , TL_POLARIZATION_PROCESSOR_POLAR_PHASE_90_DEGREES /*!< 90 degrees polarization phase */
  , TL_POLARIZATION_PROCESSOR_POLAR_PHASE_135_DEGREES /*!< 135 (-45) degrees polarization phase */
  , TL_POLARIZATION_PROCESSOR_POLAR_PHASE_MAX /*!< A sentinel value (DO NOT USE). */
};
