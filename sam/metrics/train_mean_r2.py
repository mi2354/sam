import numpy as np
import sys


def train_mean_r2(true, predicted, train_mean):
    """
    Calculation of r2 with custom mean, so you can pass the mean from the train set.
    The idea is that calculating r2 over a test set is 'leaking' information to the mean benchmark.
    This is especially problematic if the test set is small compared to the train set.
    It is therefore more suitable to compare the model predictions to the mean estimated in the
    train set.

    Parameters
    ----------
    true: numpy array or pd.Series
        Actual timeseries
    predicted: numpy array or pd.Series
        Predicted timeseries
    train_mean: float
        Mean estimated from the train set

    Returns:
    -------
    r2: float
        Custom R2 with training mean
    """

    if len(true.shape) > 1:
        true_ravel = np.ravel(true)
        assert true_ravel.size == true.shape[0], 'true argument must be 1 dimensional'
        true = true_ravel
    if len(predicted.shape) > 1:
        predicted_ravel = np.ravel(predicted)
        assert predicted_ravel.size == predicted.shape[0],\
            'predicted argument must be 1 dimensional'
        predicted = predicted_ravel

    num = np.nansum((true - predicted)**2)
    denom = np.nansum((true - train_mean)**2)

    r2 = 1 - (num / (denom+sys.float_info.epsilon))

    return r2
