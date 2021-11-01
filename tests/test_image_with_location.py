from __future__ import print_function

from builtins import range, str

import numpy as np

from nplab.instrument.camera.camera_with_location import ImageWithLocation


def test_metadata_slicing():
    # Make a sample image
    sample_image = np.zeros((100,100,3),dtype=np.uint8)
    sample_iwl = ImageWithLocation(sample_image)
    sample_iwl.datum_pixel = (44,56)
    sample_iwl.pixel_to_sample_matrix = np.zeros((4,4), dtype=np.float)
    for i in range(4):
        sample_iwl.pixel_to_sample_matrix[i,i] = 1
    sample_iwl.pixel_to_sample_matrix[3,:3] = [42, 63, 59]
    # Make the datum pixel white
    sample_iwl[tuple(sample_iwl.datum_pixel)] = 255
    metadata_string = str(sample_iwl.attrs)

    # Test that the metadata are correctly updated on slicing
    sliced_iwl = sample_iwl[30:60,30:60]
    assert np.all(sliced_iwl[tuple(sliced_iwl.datum_pixel)] == 255), "The datum pixel wasn't the same (not white)"
    assert np.all(sliced_iwl.datum_location == sample_iwl.datum_location), \
        "The position shift was incorrect ({} != {})".format(sliced_iwl.datum_location, sample_iwl.datum_location)
    assert metadata_string == str(sample_iwl.attrs), "The original metadata got changed :("

    # Check it for a 3-axis slice (should be the same)
    sliced_iwl = sample_iwl[30:60,30:60,0]
    assert sliced_iwl[tuple(sliced_iwl.datum_pixel)] == 255, "The datum pixel wasn't the same (not white)"
    assert np.all(sliced_iwl.datum_location == sample_iwl.datum_location), "The position shift was incorrect"

    # Check the scaling is correct for a slice with non-unity stride
    sliced_iwl = sample_iwl[30:60:2,30:60:2,0]
    assert sliced_iwl[tuple(sliced_iwl.datum_pixel)] == 255, "The datum pixel wasn't the same (not white) for step==2"
    assert np.all(sliced_iwl.datum_location == sample_iwl.datum_location), \
        "The position shift was incorrect for step==2"

if __name__ == "__main__":
    try:
        test_metadata_slicing()
    except Exception as e:
        print(e)