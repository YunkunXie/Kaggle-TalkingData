import time
import random
import numpy as np
import matplotlib.pyplot as plt
import math

import tensorflow as tf
import pandas as pd

from preprocess import *
from models import *
from preprocess import *
from pipelines import *






start = time.time()

train_file = '../input/train_cut.csv'
test_file = '../input/test_cut.csv'

train_data, test_data = loadData_from_file(train_file, test_file)
train_size=train_data.shape[0]
test_size=test_data.shape[0]

full_data = merge_train_test(train_data, test_data)
del( train_data, test_data)
print ("Full Data set created.")

id_col, target_col, cat_cols, num_cols = data_features(full_data)
print ("feature extracted.")

full_data = category_encoding(full_data, cat_cols)
data_sparse = one_hot_encoding(full_data, cat_cols)

full_data = process_num_data(full_data, num_cols)


train_x, train_y, test_x = train_test_data(full_data, cat_cols, num_cols, train_size)

# lightgbm blend
(train_blend_x_gbm_le,
 test_blend_x_gbm_le,
 blend_scores_gbm_le,
 best_rounds_gbm_le) = gbm_blend(est_GBM_reg, train_x, train_y, test_x, 2, 10)

print (np.mean(blend_scores_gbm_le,axis=0))
print (np.mean(best_rounds_gbm_le,axis=0))
np.savetxt("../input/train_blend_x_gbm_le.csv",train_blend_x_gbm_le, delimiter=",")
np.savetxt("../input/test_blend_x_gbm_le.csv",test_blend_x_gbm_le, delimiter=",")

# XGB blend
(train_blend_x_xgb_le,
 test_blend_x_xgb_le,
 blend_scores_xgb_le,
 best_rounds_xgb_le) = xgb_blend(est_XGB_reg, train_x, train_y, test_x, 2, 10)

print(np.mean(blend_scores_xgb_le, axis=0))
print(np.mean(best_rounds_xgb_le, axis=0))
np.savetxt("../input/train_blend_x_xgb_le.csv", train_blend_x_xgb_le, delimiter=",")
np.savetxt("../input/test_blend_x_xgb_le.csv", test_blend_x_xgb_le, delimiter=",")

train_x, train_y, test_x = sparse_train_test_data(data_sparse, full_data, num_cols, train_size)

# lightgbm blend for OHE+num
(train_blend_x_gbm_ohe, 
 test_blend_x_gbm_ohe, 
 blend_scores_gbm_ohe,
 best_rounds_gbm_ohe) = gbm_blend(est_GBM_reg, train_x, train_y, test_x, 2, 10)

print (np.mean(blend_scores_gbm_ohe,axis=0))
print (np.mean(best_rounds_gbm_ohe,axis=0))
np.savetxt("../input/train_blend_x_gbm_ohe.csv",train_blend_x_gbm_ohe, delimiter=",")
np.savetxt("../input/test_blend_x_gbm_ohe.csv",test_blend_x_gbm_ohe, delimiter=",")

# XGB blend for OHE+num
(train_blend_x_xgb_ohe,
 test_blend_x_xgb_ohe, 
 blend_scores_xgb_ohe,
 best_rounds_xgb_ohe) = xgb_blend(est_XGB_reg, train_x, train_y, test_x, 2, 10)

print(np.mean(blend_scores_xgb_ohe, axis=0))
print(np.mean(best_rounds_xgb_ohe, axis=0))
np.savetxt("../input/train_blend_x_xgb_ohe.csv", train_blend_x_xgb_ohe, delimiter=",")
np.savetxt("../input/test_blend_x_xgb_ohe.csv", test_blend_x_xgb_ohe, delimiter=",")


# NN model
(train_blend_x_ohe_mlp, 
 test_blend_x_ohe_mlp, 
 blend_scores_ohe_mlp,
 best_round_ohe_mlp) = nn_blend_data(train_x, train_y, test_x, 2, 2)

print (np.mean(blend_scores_ohe_mlp,axis=0))
print (np.mean(best_round_ohe_mlp,axis=0))
print ( log_mae(np.mean(train_blend_x_ohe_mlp,axis=1).reshape(train_size,1),train_y))
np.savetxt("../input/train_blend_x_ohe_mlp.csv",train_blend_x_ohe_mlp, delimiter=",")
np.savetxt("../input/test_blend_x_ohe_mlp.csv",test_blend_x_ohe_mlp, delimiter=",")


print  ("Blending.")

train_models = (train_blend_x_gbm_le,
                train_blend_x_xgb_le,
                train_blend_x_xgb_ohe,
                train_blend_x_gbm_ohe,
                np.mean(train_blend_x_ohe_mlp,axis=1).reshape(train_size,1))

test_models  = (test_blend_x_gbm_le,
                test_blend_x_xgb_le,
                test_blend_x_xgb_ohe,
                test_blend_x_gbm_ohe,
                np.mean(test_blend_x_ohe_mlp,axis=1).reshape(test_x.shape[0],1))

pred_y_ridge = ridge_blend(train_models, test_models, train_y)
results = pd.DataFrame()
results['id'] = full_data[train_size:].id
results['loss'] = pred_y_ridge
results.to_csv("../output/sub_ridge_blended.csv", index=False)
print ("Submission created.")


pred_y_gblinear = gblinear_blend(train_models, test_models, train_y)
results = pd.DataFrame()
results['id'] = full_data[train_size:].id
results['loss'] = pred_y_gblinear
results.to_csv("../output/sub_xgb_gblinear.csv", index=False)
print ("Submission created.")

## Final submission
#  weights: [0.5,0.5]

pred_y = pred_y_ridge*0.5 + pred_y_gblinear*0.5

results = pd.DataFrame()
results['id'] = full_data[train_size:].id
results['loss'] = pred_y
results.to_csv("../output/sub_final.csv", index=False)

endtime = time.time()
print ("Submission created.")