from pathlib import Path

import pandas as pd


PACKAGEDIR = Path(__file__).parent.absolute()


def load_rainbow_beach():
    """
    Loads the Rainbow Beach dataset (subset of the open Chicago Water dataset)

    Source:
    https://data.cityofchicago.org/Parks-Recreation/Beach-Water-Quality-Automated-Sensors/qmqz-2xku
    """
    file_path = PACKAGEDIR / "data/rainbow_beach.parquet"
    return pd.read_parquet(file_path)


def load_sewage_data():
    """
    Loads a sewage dataset, containing the discharge of multiple pumps and some weather data

    Source: Fake dataset by Royal HaskoningDHV
    """
    file_path = PACKAGEDIR / "data/sewage_data.parquet"
    return pd.read_parquet(file_path)
