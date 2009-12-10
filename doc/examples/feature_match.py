import matplotlib.pyplot as plt
import numpy as np
import os

from supreme.config import data_path
from supreme import transform
from supreme.io import imread, ImageCollection
from supreme.transform import matrix as homography
from supreme.feature import dpt

import supreme.register

# This used to do log polar transforms, but now
# we just match the distributions of the coefficients
from supreme.register.correspond import correspond

# ----------------------------------------------------------------------

ic = ImageCollection(os.path.join(data_path, 'toystory/toy*.png'), grey=True)
img0 = ic[0]
img1 = ic[1]

features = 300
window = 0
stack = True # Disable this to view the output without stacking
feature_method = 'dpt' # 'fast'
registration_method = 'RANSAC' # or iterative
win_size = None

# ----------------------------------------------------------------------

print "Getting feature coordinates."
def get_brightest_pulses(weight, area, N=100):
    """
    Return feature coordinates and areas.
    """
    sort_idx = np.argsort(weight.flat)
    not_brightest = sort_idx[:-N]
    brightest = sort_idx[-N:]

    weight.flat[not_brightest] = 0
    feat = zip(*np.nonzero(weight))
    area = area.flat[brightest]

    norm_inv_area = area/float(np.prod(weight.shape))

    return feat, norm_inv_area

if feature_method == 'dpt':
    import supreme.lib.dpt as dpt
    import supreme.lib.dpt.connected_region_handler as crh
    from supreme.feature.dpt import features as dpt_feat

    pulses = dpt.decompose(img0.astype(np.int))
    pulses_mod = dpt.decompose(img1.astype(np.int))

    weight, area = dpt_feat(pulses, img0.shape, win_size=window)
    weight_mod, area_mod = dpt_feat(pulses_mod, img1.shape, win_size=window)

    feat_coord, feat_area = get_brightest_pulses(weight, area, N=features)
    feat_mod_coord, feat_mod_area = get_brightest_pulses(weight_mod, area_mod,
                                                         N=features*1)
elif feature_method == 'fast':
    from supreme.lib import fast

    perm = np.random.permutation
    feat_coord = perm(fast.corner_detect(img0, barrier=20))[:features]
    feat_coord = [(i,j) for (j,i) in feat_coord]
    feat_mod_coord = perm(fast.corner_detect(img1, barrier=20))[:features]

    feat_area = np.ones(len(feat_coord)) * 2
    feat_mod_coord = [(i,j) for (j,i) in feat_mod_coord]
    feat_mod_area = np.ones(len(feat_mod_coord)) * 2
else:
    raise ValueError("Invalid feature extractor specified.")

import matplotlib.pyplot as plt

plt.subplot(121)
plt.hold(True)
plt.imshow(img0, cmap=plt.cm.gray, interpolation='nearest')
for (i, j), a in zip(feat_coord, feat_area):
    plt.plot(j, i, 'o', markersize=a)

plt.subplot(122)
plt.hold(True)
plt.imshow(img1, cmap=plt.cm.gray, interpolation='nearest')
for (i, j), a in zip(feat_mod_coord, feat_mod_area):
    plt.plot(j, i, 'o', markersize=a)
plt.show()

print "Finding tentative correspondences..."
if win_size is None:
    win_size = 255/2/np.mean(feat_mod_area)
    win_size = np.clip(win_size, 11, 31)
    print "Automatically determining window size...%d" % win_size

print "win_size=%.2f" % win_size
correspondences = correspond(feat_coord, img0.astype(np.uint8),
                             feat_mod_coord, img1.astype(np.uint8),
                             win_size=win_size)

if stack:
    pairs = np.array(correspondences)
    M, converged = supreme.register.sparse(pairs[:, 0, 0], pairs[:, 0, 1],
                                           pairs[:, 1, 0], pairs[:, 1, 1],
                                           mode=registration_method,
                                           confidence=0.9)
#                                           inliers_required=features/4)
    plt.subplot(2, 1, 2)
    stack = supreme.register.stack.with_transform((img0, img1),
                                                  (np.eye(3), M))
    plt.imshow(stack, cmap=plt.cm.gray, interpolation='nearest')


plt.subplot(2, 1, 1)
r0, c0 = img0.shape
r1, c1 = img1.shape
oshape = (max(r0, r1), c0 + c1)
side_by_side = np.zeros(oshape, dtype=img0.dtype)
side_by_side[0:r0, 0:c0] = img0
side_by_side[0:r1, c0:c0 + c1] = img1
plt.imshow(side_by_side, cmap=plt.cm.gray, interpolation='nearest')
for ((i,j), (m, n)) in correspondences:
    plt.plot([j, n + img0.shape[1]], [i, m], '-o')
plt.axis('image')


plt.show()
