import pandas as pd

from sam.preprocessing import sam_format_to_wide

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from sklearn.experimental import enable_iterative_imputer  # noqa F401
from sklearn.impute import IterativeImputer


def preprocess_data_for_benchmarking(data, column_filter, targetcol, test_size=0.3,
                                     resample='auto', resample_freq='auto', ffill_limit=5):
    '''
    Function that takes a dataframe in SAM format, and converts it to
    X_train/X_test/y_train/y_test, while
    taking some liberties when it comes to 'faithfulness' of the underlying data.
    This function should NEVER be used in an actual project, but only for benchmarking models.
    For example, you want to compare two feature engineering methods to each other on a dataset in
    SAM format, but don't feel like properly reshaping/imputing/resampling the dataset yourself.

    Parameters
    ----------
    data: pd.DataFrame
        data in SAM format (TIME, TYPE, ID, VALUE columns)
    column_filter: function
        Function that takes in a column name (string) and returns a boolean, if this column should
        be included in the result.
        The column names will be after reshaping, so in the form ID_TYPE
        The column 'TIME' and the targetcol will be accepted regardless of this function.
    targetcol: string
        The column to use as the target.
    test_size: float, optional (default=0.3)
        The portion of the data to use as testdata. This is always the last portion. So by default,
        the first 70% is train, the last 30% is test
    resample: boolean, optional (default='auto')
        Whether or not to resample the data. By default, resample if the data is not monospaced yet
    resample_freq: string, optional (default='auto')
        If resample, the frequency to resample to. By default, use the median frequency of the data
    ffill_limit: int, optional (default=5)
        If resample, the maximum number of values to ffill. By default, only ffill 5 values.
        This means the data won't be exactly monospaced, but will prevent extremely long flatlines
        if there are gaps in the data
    '''
    # Convert to wide format
    data = sam_format_to_wide(data)
    # Select only relevant columns for 1 city
    data = data[filter(lambda x: x == 'TIME' or x == targetcol or column_filter(x), data.columns)]
    cols = data.columns  # Backup for after imputer\

    if resample == 'auto':
        monospaced = data['TIME'].diff()[1:].unique().size == 1
        resample = not monospaced
    if resample and resample_freq == 'auto':
        resample_freq = data['TIME'].diff()[1:].median()

    if resample:
        data = (data.set_index('TIME').resample(resample_freq).pad(
            limit=ffill_limit).dropna(how='all').reset_index())

    # TODO ask Daan if this is not potentially a problem
    # I think it's not, because all models use the same imputed data,
    # so the comparison of models is still fair
    time = data.pop('TIME')
    data = IterativeImputer().fit_transform(data)
    # Recover the column structure and the TIME column
    data = pd.DataFrame(data, columns=[col for col in cols if col != 'TIME'])
    data['TIME'] = time

    # Now create train/test split
    y = data.pop(targetcol)
    X_train, X_test, y_train, y_test = train_test_split(
        data, y, test_size=test_size, shuffle=False)

    return X_train, X_test, y_train, y_test


def benchmark_model(train_test_data, scorer=mean_squared_error, validation_data=True,
                    return_histories=False, fit_kwargs={}, **modeldict):
    '''
    Benchamarks a dictionary of sam models on train/test data, and returns a dictionary with scores
    The models are assumed to be SAM models in 2 ways:

        - ``predict`` is called as ``predict(X_test, y_test)``
        - ``model.get_actual(y_test)`` is called

    Parameters
    ----------
    train_test_data: tuple
        tuple with elements X_train, X_test, y_train, y_test
    modeldict: dictionary
        dictionary of shape ``{modelname: model}`` where modelname is a string
    scorer: function, optional (default=mean_squared_error)
        Function with signature ``func(y_true, y_pred)``
        where ``y_true`` and ``y_pred`` are pandas series, and it returns a scalar

    Returns
    -------
    dict:
        Dctionary of form: ``{modelname_1: score, ..., modelname_n: score,
        persistence_benchmark: score, mean_benchmark: score}``
        where all scores are scalars.
    '''

    X_train, X_test, y_train, y_test = train_test_data

    if validation_data:
        fit_kwargs['validation_data'] = (X_test, y_test)
    final_scores = {}
    histories = {}

    for modelname in modeldict:

        model = modeldict[modelname]

        history = model.fit(X_train, y_train, **fit_kwargs)
        pred = model.predict(X_test, y_test)

        results = pd.DataFrame({
            'pred': pred,
            'actual': model.get_actual(y_test)
        }).dropna(axis=0)

        score = scorer(results['actual'], results['pred'])
        final_scores[modelname] = score
        histories[modelname] = history

    # Benchmark results:
    # We use the last model to get actual
    results = pd.DataFrame({
        'actual': model.get_actual(y_test),
        'persistence_benchmark': y_test,
        'mean_benchmark': y_test.mean()
    }).dropna(axis=0)

    final_scores['persistence_benchmark'] = scorer(
        results['actual'], results['persistence_benchmark'])
    final_scores['mean_benchmark'] = scorer(results['actual'], results['mean_benchmark'])

    if return_histories:
        return final_scores, histories
    else:
        return final_scores


def plot_score_dicts(**score_dicts):
    '''
    Very simple plotting function for showing the results

    Parameters
    ----------
    score_dicts: kwargs
       Containing score dictionaries (output from `benchmark_model`). The key of the dictionary
       is the name/descriptor of the dataset.

    Examples
    --------
    >>> plot_score_dicts(
    >>>     chicago={'model_a': 0.5, 'persistence_benchmark': 0.6, 'mean_benchmark': 0.4},
    >>>     china={'model_a': 0.1, 'mean_benchmark': 0.3, 'persistence_benchmark': 0.4}
    >>>     )
    '''
    return pd.DataFrame(score_dicts).transpose().plot(kind='bar')


def benchmark_wrapper(models, datasets, column_filters, targetcols):
    '''
    Wrapper around entire benchmark pipeline.
    Takes a dictionary of models, dictionary of datasets in SAM format,
    and preprocesses, fits and evaluates all models and benchmarks, and plots them

    Parameters
    ----------
    models: dict
        Dictionary of SAM models
    datasets: dict
        Dictionary of datasets in SAM format
    column_filters: dict
        Dictionary of functions that accept a colum in ID_TYPE format
    targetcols: dict
        Dictionary of strings, the targetcolumns in ID_TYPE format

    Examples
    --------
    >>> datasets = {
    >>>     'chicago': pd.read_feather('data/ChicagoWater.feather'),
    >>>     'beijing': pd.read_feather('data/CitiesPM.feather'),
    >>>     'detectronic': (pd.read_feather('data/detec_data.feather')
    >>>                     .rename({'timestamp': 'TIME', 'type': 'TYPE',
    >>>                              'location': 'ID', 'value': 'VALUE'}, axis=1)
    >>>                     .drop('index', axis=1)
    >>>                     .astype({'TYPE': str}))
    >>> }
    >>> column_filters = {
    >>>     'chicago': lambda x: x.startswith('63rd Street'),
    >>>     'beijing': lambda x: x.startswith('Beijing),
    >>>     'detectronic': lambda x: x.startswith('7167')
    >>> }
    >>> targetcols = {
    >>>     'chicago': '63rd Street Beach_Turbidity',
    >>>     'beijing: 'Beijing_US Post_PM'
    >>>     'detectronic': '7167_6'
    >>> }
    >>> models = {
    >>>     'mymodel': SAMQuantileMLP(predict_ahead=[3], use_y_as_feature=True, timecol='TIME',
    >>>                               dropout=0.5, verbose=True)  # some non-default params
    >>> }
    >>> benchmark_wrapper(models, datasets, column_filters, targetcols)
    '''
    data_names = datasets.keys()
    traintest_dict = \
        dict([(name, preprocess_data_for_benchmarking(datasets[name], column_filters[name],
                                                      targetcols[name]))
              for name in data_names])
    scores = {}
    for name in data_names:
        scores[name] = benchmark_model(traintest_dict[name], **models)
    plot_score_dicts(**scores)