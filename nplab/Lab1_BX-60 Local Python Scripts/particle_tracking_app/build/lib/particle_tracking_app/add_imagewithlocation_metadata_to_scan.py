from __future__ import division
from builtins import range
from past.utils import old_div
import nplab
from nplab.utils.image_with_location import ensure_2d, ensure_3d, ImageWithLocation
import numpy as np

nplab.datafile.set_current("2015-10-01_3.h5", mode='a')
df = nplab.current_datafile()
tiled_image = df['CameraStageMapper/tiled_image_2']
camera_point_to_sample_2D = tiled_image.attrs['camera_to_sample']
for tile in tiled_image.numbered_items('tile'):
    pos = tile.attrs['camera_centre_position']
    M = np.zeros((4, 4))  # NB M is never a matrix; that would create issues, as then all the vectors must be matrices
    M[:2,:2] = camera_point_to_sample_2D
    for i in range(2):
        M[i,:] /= tile.shape[i] # we're dealing in pixels now...
    datum_displacement = np.dot(old_div(ensure_3d(tile.shape[:2]),2), M[:3,:3])
    M[2,2] = 1 # Pass Z through uninterrupted
    M[3, 0:3] = pos - datum_displacement  # Ensure that the datum pixel transforms to here.
    tile.attrs['pixel_to_sample_matrix'] = M
    tile.attrs['datum_pixel'] = old_div(ensure_2d(tile.shape),2)
    # Below: debug code to check it's giving the right answer now (!)
#    print "camera_centre_position: {}".format(tile.attrs['camera_centre_position'])
#    iwl = ImageWithLocation(tile, tile.attrs)
#    print "iwl bottom-left d: {}".format(iwl.pixel_to_location((0,0)) - tile.attrs['camera_centre_position'])
#    print "iwl datum: {}".format(iwl.datum_location - tile.attrs['camera_centre_position'])
#    print "csm image diagonal displacement: {}".format(np.dot([1,1], camera_point_to_sample_2D))
#    print "csm image x displacement: {}".format(np.dot([1,0], camera_point_to_sample_2D))
#    print "csm image y displacement: {}".format(np.dot([0,1], camera_point_to_sample_2D))

df.close()
