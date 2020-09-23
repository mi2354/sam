import pandas as pd
import numpy as np
from sam.data_sources import read_knmi
from sklearn.exceptions import NotFittedError
from sklearn.base import BaseEstimator, TransformerMixin


class SPEITransformer(BaseEstimator, TransformerMixin):
    """ Standardized Precipitation (and Evaporation) Index

    Computation of standardized metric that measures relative drought
    or precipitation shortage.

    SP(E)I is a metric computed per day. Therefore daily weather data
    is required as input. This class assumes that the data contains
    precipitation columns 'RH' and optionally evaporation column 'EV24'.
    These namings are KNMI standards.

    The method computes a rolling average over the precipitation (and
    evaporation). Based on historic data (at least 30 years) the mean
    and standard deviation of the rolling average are computed across years.
    The daily rolling average is then transformed to a Z-score, by dividing
    by the corresponding mean and standard deviation.

    Smoothing can be applied to make the model more robust, and able to
    compute the SP(E)I for leap year days. If ``smoothing=False``, the
    transform method can return NA's

    The resulting score describes how dry the weather is. A very low score
    (smaller than -2) indicates extremely dry weather. A high score (above 2)
    indicates very wet weather.

    See:
    http://www.droogtemonitor.nl/index.php/over-de-droogte-monitor/theorie

    Parameters
    ----------
    metric: {"SPI", "SPEI"}, default="SPI"
        The type of KPI to compute
        "SPI" computes the Standardized Precipitation Index
        "SPEI" computed the Standardized Precipitation Evaporation Index
    window: str or int, default='30D'
        Window size to compute the rolling precipitation or precip-evap sum
    smoothing: boolean, default=True
        Whether to use smoothing on the estimated mean and std for each day of
        the year.
        When ``smoothing=True``, a centered rolling median of five steps is
        applied to the models estimated mean and standard deviations per day.
        The model definition will therefore be more robust.
        Smoothing causes less sensitivity, especially for the std.
        Use the ``plot`` method to visualize the estimated mean and std
    min_years: int, default=30
        Minimum number of years for configuration. When setting less than 30,
        make sure that the estimated model makes sense, using the ``plot``
        method

    Examples
    ----------
    >>> from sam.data_sources import read_knmi
    >>> from sam.feature_engineering import SPEITransformer
    >>> knmi_data = read_knmi(start_date='1960-01-01', end_date='2020-01-01',
    >>>     variables=['RH', 'EV24'], freq='daily').set_index('TIME').dropna()
    >>> knmi_data['RH'] = knmi_data['RH'].divide(10).clip(0)
    >>> knmi_data['EV24'] = knmi_data['EV24'].divide(10)
    >>> spi = SPEITransformer().configure(knmi_data)
    >>> spi.transform(knmi_data)
    """
    def __init__(self, metric='SPEI', window='30D', smoothing=True, min_years=30):
        self.window = window
        self.metric = metric
        self.smoothing = smoothing
        self.min_years = min_years
        self.metric_name = metric + '_' + window
        self.axis_name = 'Precip-Evap' if metric == 'SPEI' else 'Precip'
        self.configured = False

    def check_configured(self):
        if not self.configured:
            raise NotFittedError("This instance of SPEITransformer has not "
                                 "been configured yet. Use 'configure' with "
                                 "appropriate arguments before using this "
                                 "transformer")

    def check_X(self, X):
        if 'RH' not in X.columns:
            raise ValueError("Dataframe X should contain columns 'RH'")
        if ('EV24' not in X.columns) and (self.metric == 'SPEI'):
            raise ValueError("Metric SPEI requires X to have 'EV24' column")

    def compute_target(self, X):
        if self.metric == 'SPI':
            target = X['RH']
        elif self.metric == 'SPEI':
            target = X['RH'] - X['EV24']
        else:
            raise ValueError("Invalid metric type, choose either 'SPI' or 'SPEI'")

        target = target.rolling(self.window).mean()

        return target

    def configure(self, X, y=None):
        """ Fit normal distribution on rolling precipitation (and evaporation)
        Apply this to historic data of precipitation (at least ``min_years`` years)
        Parameters
        ----------
        X: pandas dataframe
            A data frame containing columns 'RH' (and optionally 'EV24')
            and should have a datetimeindex
        """
        self.check_X(X)
        target = self.compute_target(X)

        results = pd.DataFrame({
            self.metric_name: target,
            'month': target.index.month,
            'day': target.index.day
        }, index=target.index)

        self.model = results \
            .groupby(['month', 'day'])[self.metric_name] \
            .agg(['count', 'mean', 'std']) \
            .reset_index() \
            .sort_values(by=['month', 'day'])

        n_years = self.model['count'].max()
        # Make sure that for at least one day there are ``min_years`` samples
        if n_years < self.min_years:
            raise ValueError(f'Provided weather data contains less than'
                             f'{self.min_years} years. '
                             f'Please provide more data for configuration')

        # Each day should at least have data for 50%
        # of all years in the data, otherwise estimated mean and std
        # are set to nan. This removes leap year days
        self.model.loc[
            (self.model['count'] < (n_years / 2)),
            ['mean', 'std']
        ] = np.nan
        if self.smoothing:
            # To remove spikes in the mean and std
            # and create a smooth model over the year
            # smoothing is applied. This approach of 5-step median
            # is just a first approach, and does the essential trick
            # Default SP(E)I from literature does not use smoothing
            self.model['mean'] = self.model['mean'] \
                .rolling(5, center=True, min_periods=1).median(skipna=True)
            self.model['std'] = self.model['std'] \
                .rolling(5, center=True, min_periods=1).median(skipna=True)

        self.configured = True

        return self

    def fit(self, X):
        """ Fit function
        Does nothing, but is required for a transformer.
        This function wil not change the SP(E)I model. The SP(E)I
        should be configured with the ``configure`` method.
        In this way, the ``SPEITransfomer`` can be used within a
        sklearn pipeline, without requiring > 30 years of data.
        """
        return self

    def transform(self, X, y=None):
        """ Transforming new weather data to SP(E)I metric
        Returns a dataframe with single columns
        """
        self.check_configured()
        self.check_X(X)
        target = self.compute_target(X)

        results = pd.DataFrame({
            self.metric_name: target,
            'month': target.index.month,
            'day': target.index.day
        }, index=target.index)

        results = results.merge(
            self.model,
            left_on=['month', 'day'],
            right_on=['month', 'day'],
            how='left'
        )
        results.index = target.index
        results[self.metric_name] = (results[self.metric_name] - \
            results['mean']) / results['std']

        return results[[self.metric_name]]

    def plot(self):
        """ Plot model
        Visualisation of the configured model. This function shows the
        estimated mean and standard deviation per day of the year.
        """
        self.check_configured()
        import matplotlib.pyplot as plt
        fig, axs = plt.subplots(2, figsize=(10, 10))
        axs[0].plot(self.model['mean'])
        axs[0].set_ylabel('Mean of ' + self.axis_name)
        axs[0].set_xlabel('Day of the year')
        axs[1].plot(self.model['std'])
        axs[1].set_ylabel('Standard deviation of ' + self.axis_name)
        axs[1].set_xlabel('Day of the year')
