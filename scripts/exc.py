class DataError(Exception):
    """
    Generic error raised whenever the data does not meet the model requirements.
    For instance :
    - Not the right sheet names,
    - Not the right column names,
    - No matching between gamspy objects (such as sets, parameters, maps)
    """
    pass


class IncoherentDataError(Exception):
    """
    Generic error raised whenever datasets lack of consistency, such as :
    - less total beds number than babies not going out,
    - ...
    """
    pass
