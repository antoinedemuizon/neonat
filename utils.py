import pandas as pd


def mapping_creation(df):
    """
    Return a pd.Series adapted to gamspy map object.
    """
    multi_index = pd.MultiIndex.from_frame(df.dropna()).drop_duplicates()
    gamspy_mapping_df = pd.Series(index=multi_index)
    return gamspy_mapping_df
