
from sklearn import  model_selection
from sklearn.model_selection import StratifiedKFold, KFold
from sklearn.model_selection import GridSearchCV
from sklearn.linear_model import ElasticNet, Ridge, LinearRegression

from pylightgbm.models import GBMRegressor

from keras.callbacks import EarlyStopping, ModelCheckpoint

import xgboost as xgb

from models import *
from metric import *

import time

def search_model(train_x, train_y, est, param_grid, n_jobs, cv, refit=False):
    ##Grid Search for the best model
    model = GridSearchCV(estimator=est,
                         param_grid=param_grid,
                         scoring=log_mae_scorer,
                         verbose=10,
                         n_jobs=n_jobs,
                         iid=True,
                         refit=refit,
                         cv=cv)
    # Fit Grid Search Model
    model.fit(train_x, train_y)
    print("Best score: %0.3f" % model.best_score_)
    print("Best parameters set:", model.best_params_)
    print("Scores:", model.grid_scores_)
    return model




def search_model_mae(train_x, train_y, est, param_grid, n_jobs, cv, refit=False):
    ##Grid Search for the best model
    model = GridSearchCV(estimator=est,
                         param_grid=param_grid,
                         scoring='neg_mean_absolute_error',
                         verbose=10,
                         n_jobs=n_jobs,
                         iid=True,
                         refit=refit,
                         cv=cv)
    # Fit Grid Search Model
    model.fit(train_x, train_y)
    print("Best score: %0.3f" % model.best_score_)
    print("Best parameters set:", model.best_params_)
    print("Scores:", model.cv_results_)
    return model


## XGBoost blending function


def xgb_blend(estimators, train_x, train_y, test_x, fold, early_stopping_rounds=0):
    print("Blend %d estimators for %d folds" % (len(estimators), fold))
    skf = list(KFold(len(train_y), fold))

    train_blend_x = np.zeros((train_x.shape[0], len(estimators)))
    test_blend_x = np.zeros((test_x.shape[0], len(estimators)))
    scores = np.zeros((len(skf), len(estimators)))
    best_rounds = np.zeros((len(skf), len(estimators)))

    for j, est in enumerate(estimators):
        print("Model %d: %s" % (j + 1, est))
        test_blend_x_j = np.zeros((test_x.shape[0], len(skf)))
        for i, (train, val) in enumerate(skf):
            print("Model %d fold %d" % (j + 1, i + 1))
            fold_start = time.time()
            train_x_fold = train_x[train]
            train_y_fold = train_y[train]
            val_x_fold = train_x[val]
            val_y_fold = train_y[val]
            if early_stopping_rounds == 0:  # without early stopping
                est.fit(train_x_fold, train_y_fold)
                best_rounds[i, j] = est.n_estimators
                val_y_predict_fold = est.predict(val_x_fold)
                score = log_mae(val_y_fold, val_y_predict_fold, 200)
                print("Score: ", score)
                scores[i, j] = score
                train_blend_x[val, j] = val_y_predict_fold
                test_blend_x_j[:, i] = est.predict(test_x)
                print("Model %d fold %d fitting finished in %0.3fs" % (j + 1, i + 1, time.time() - fold_start))
            else:  # early stopping
                est.set_params(n_estimators=10000)
                est.fit(train_x_fold,
                        train_y_fold,
                        eval_set=[(val_x_fold, val_y_fold)],
                        eval_metric=xg_eval_mae,
                        early_stopping_rounds=early_stopping_rounds,
                        verbose=False
                        )
                best_round = est.best_iteration
                best_rounds[i, j] = best_round
                print("best round %d" % (best_round))
                val_y_predict_fold = est.predict(val_x_fold, ntree_limit=best_round)
                score = log_mae(val_y_fold, val_y_predict_fold, 200)
                print("Score: ", score)
                scores[i, j] = score
                train_blend_x[val, j] = val_y_predict_fold
                test_blend_x_j[:, i] = est.predict(test_x, ntree_limit=best_round)
                print("Model %d fold %d fitting finished in %0.3fs" % (j + 1, i + 1, time.time() - fold_start))

        test_blend_x[:, j] = test_blend_x_j.mean(1)
        print("Score for model %d is %f" % (j + 1, np.mean(scores[:, j])))
    print("Score for blended models is %f" % (np.mean(scores)))
    return (train_blend_x, test_blend_x, scores, best_rounds)


## LightGBM blending function
def gbm_blend(estimators, train_x, train_y, test_x, fold, early_stopping_rounds=0):
    print("Blend %d estimators for %d folds" % (len(estimators), fold))
    skf = list(KFold(len(train_y), fold))

    train_blend_x = np.zeros((train_x.shape[0], len(estimators)))
    test_blend_x = np.zeros((test_x.shape[0], len(estimators)))
    scores = np.zeros((len(skf), len(estimators)))
    best_rounds = np.zeros((len(skf), len(estimators)))

    for j, gbm_est in enumerate(estimators):
        print("Model %d: %s" % (j + 1, gbm_est))
        test_blend_x_j = np.zeros((test_x.shape[0], len(skf)))
        params = gbm_est.get_params()
        for i, (train, val) in enumerate(skf):
            print("Model %d fold %d" % (j + 1, i + 1))
            est = GBMRegressor()
            est.param = params
            #             est.exec_path='/users/cchen1/library/LightGBM/lightgbm'
            est.exec_path = '/Users/Jianhua/anaconda/lightgbm'
            print(est)
            fold_start = time.time()
            train_x_fold = train_x[train]
            train_y_fold = train_y[train]
            val_x_fold = train_x[val]
            val_y_fold = train_y[val]
            if early_stopping_rounds == 0:  # without early stopping
                est.fit(train_x_fold, train_y_fold)
                best_rounds[i, j] = est.num_iterations
                val_y_predict_fold = est.predict(val_x_fold)
                score = log_mae(val_y_fold, val_y_predict_fold, 200)
                print("Score: ", score, mean_absolute_error(val_y_fold, val_y_predict_fold))
                scores[i, j] = score
                train_blend_x[val, j] = val_y_predict_fold
                test_blend_x_j[:, i] = est.predict(test_x)
                print("Model %d fold %d fitting finished in %0.3fs" % (j + 1, i + 1, time.time() - fold_start))
            else:  # early stopping
                est.set_params(num_iterations=1000000)
                est.set_params(early_stopping_round=early_stopping_rounds)
                est.set_params(verbose=False)
                est.fit(train_x_fold,
                        train_y_fold,
                        test_data=[(val_x_fold, val_y_fold)]
                        )
                best_round = est.best_round
                best_rounds[i, j] = best_round
                print("best round %d" % (best_round))
                val_y_predict_fold = est.predict(val_x_fold)
                score = log_mae(val_y_fold, val_y_predict_fold, 200)
                print("Score: ", score, mean_absolute_error(val_y_fold, val_y_predict_fold))
                scores[i, j] = score
                train_blend_x[val, j] = val_y_predict_fold
                test_blend_x_j[:, i] = est.predict(test_x)
                print("Model %d fold %d fitting finished in %0.3fs" % (j + 1, i + 1, time.time() - fold_start))

        test_blend_x[:, j] = test_blend_x_j.mean(1)
        print("Score for model %d is %f" % (j + 1, np.mean(scores[:, j])))
    print("Score for blended models is %f" % (np.mean(scores)))
    return (train_blend_x, test_blend_x, scores, best_rounds)


def nn_blend_data(train_x, train_y, test_x, fold, early_stopping_rounds=0, batch_size=128):
    print("Blend %d estimators for %d folds" % (len(parameters), fold))
    skf = list(KFold(len(train_y), fold))
    # setup callbacks and checkpoint functions
    early_stop = EarlyStopping(monitor='val_mae_log', patience=5, verbose=0, mode='auto')
    checkpointer = ModelCheckpoint(filepath="../tmp/weights.hdf5", monitor='val_mae_log', verbose=0, save_best_only=True,
                                   mode='min')
    bagging_num = 10
    nn_parameters = []

    nn_parameter =  { 'input_size' :400, 'input_dim' : train_x.shape[1], 'input_drop_out':0.5,
                      'hidden_size' : 200, 'hidden_drop_out' :0.3, 'learning_rate': 0.1, 'optimizer': 'adadelta' }

    for i in range(bagging_num):
        nn_parameters.append(nn_parameter)


    train_blend_x = np.zeros((train_x.shape[0], len(parameters)))
    test_blend_x = np.zeros((test_x.shape[0], len(parameters)))
    scores = np.zeros((len(skf), len(parameters)))
    best_rounds = np.zeros((len(skf), len(parameters)))

    for j, nn_params in enumerate(parameters):
        print("Model %d: %s" % (j + 1, nn_params))
        test_blend_x_j = np.zeros((test_x.shape[0], len(skf)))
        for i, (train, val) in enumerate(skf):
            print("Model %d fold %d" % (j + 1, i + 1))
            fold_start = time.time()
            train_x_fold = train_x[train]
            train_y_fold = train_y[train]
            val_x_fold = train_x[val]
            val_y_fold = train_y[val]

            # early stopping
            model = nn_model(nn_params)
            print(model)
            fit = model.fit_generator(generator=batch_generator(train_x_fold, train_y_fold, batch_size, True),
                                      nb_epoch=70,
                                      samples_per_epoch=train_x_fold.shape[0],
                                      validation_data=(val_x_fold.todense(), val_y_fold),
                                      verbose=0,
                                      callbacks=[
                                          # EarlyStopping(monitor='val_mae_log'
                                          #, patience=early_stopping_rounds, verbose=0, mode='auto'),
                                          ModelCheckpoint(filepath="../tmp/weights.hdf5"
                                                          , monitor='val_mae_log',
                                                          verbose=1, save_best_only=True, mode='min')
                                                ]
                                      )

            best_round = sorted([[id, mae] for [id, mae] in enumerate(fit.history['val_mae_log'])], key=lambda x: x[1],
                                reverse=False)[0][0]
            best_rounds[i, j] = best_round
            print("best round %d" % (best_round))

            model.load_weights("../tmp/weights.hdf5")
            # Compile model (required to make predictions)
            model.compile(loss='mae', metrics=[mae_log], optimizer=nn_params['optimizer'])

            # print (mean_absolute_error(np.exp(y_val)-200, pred_y))
            val_y_predict_fold = model.predict_generator(generator=batch_generatorp(val_x_fold, batch_size, True),
                                                         val_samples=val_x_fold.shape[0]
                                                         )

            score = log_mae(val_y_fold, val_y_predict_fold, 200)
            print("Score: ", score, mean_absolute_error(val_y_fold, val_y_predict_fold))
            scores[i, j] = score
            train_blend_x[val, j] = val_y_predict_fold.reshape(val_y_predict_fold.shape[0])

            model.load_weights("../tmp/weights.hdf5")
            # Compile model (required to make predictions)
            model.compile(loss='mae', metrics=[mae_log], optimizer=nn_params['optimizer'])
            test_blend_x_j[:, i] = model.predict_generator(generator=batch_generatorp(test_x, batch_size, True),
                                                           val_samples=test_x.shape[0]
                                                           ).reshape(test_x.shape[0])
            print("Model %d fold %d fitting finished in %0.3fs" % (j + 1, i + 1, time.time() - fold_start))

        test_blend_x[:, j] = test_blend_x_j.mean(1)
        print("Score for model %d is %f" % (j + 1, np.mean(scores[:, j])))
    print("Score for blended models is %f" % (np.mean(scores)))
    return (train_blend_x, test_blend_x, scores, best_rounds)



def batch_generator(X, y, batch_size, shuffle):
        number_of_batches = np.ceil(X.shape[0]/batch_size)
        counter = 0
        sample_index = np.arange(X.shape[0])
        if shuffle:
                np.random.shuffle(sample_index)
        while True:
                batch_index = sample_index[batch_size*counter:batch_size*(counter+1)]
                X_batch = X[batch_index,:].toarray()
                y_batch = y[batch_index]
                counter += 1
                yield X_batch, y_batch
                if (counter == number_of_batches):
                        if shuffle:
                                np.random.shuffle(sample_index)
                        counter = 0


def batch_generatorp(X, batch_size, shuffle):
        number_of_batches = X.shape[0] / np.ceil(X.shape[0]/batch_size)
        counter = 0
        sample_index = np.arange(X.shape[0])
        while True:
                batch_index = sample_index[batch_size * counter:batch_size * (counter + 1)]
                X_batch = X[batch_index, :].toarray()
                counter += 1
                yield X_batch
                if (counter == number_of_batches):
                        counter = 0

def ridge_blend(train_models):
        param_grid = { 'alpha':[0,0.00001,0.00003,0.0001,0.0003,0.001,0.003,0.01,
                                 0.03,0.1,0.3,1,3,10,15,20,25,30,35,40,45,50,55,60,70]}
        model = search_model(np.hstack(train_models)
                             , train_y
                             , Ridge()
                             , param_grid
                             , n_jobs=1
                             , cv=4
                             , refit=True)

        print ("best subsample:", model.best_params_)
       
        pred_y_ridge = np.exp(model.predict(np.hstack(test_models))) - lift
        return pred_y_ridge

def gblinear_blend(train_models, test_models):
        params = { 'eta': 0.1, 'booster': 'gblinear', 'lambda': 0, 'alpha': 0,
                   'lambda_bias' : 0, 'silent': 0, 'verbose_eval': True, 'seed': 1234 }

        xgb.cv(params, xgb.DMatrix(np.hstack(train_models)
                                , label=train_y,missing=np.nan)
                                , num_boost_round=100000, nfold=4
                                , feval=xg_eval_mae
                                , seed=1234
                                , callbacks=[xgb.callback.early_stop(500)])

        xgtrain_blend = xgb.DMatrix(np.hstack(train_models), label=train_y, missing=np.nan)

        xgb_model=xgb.train(params, xgtrain_blend,
                            num_boost_round=<best round of xgb.cv from above>,
                            feval=xg_eval_mae)

        pred_y_gblinear = np.exp(xgb_model.predict(xgb.DMatrix(np.hstack(test_models)))) - lift

        return pred_y_gblinear
