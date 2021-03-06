from sparktk.lazyloader import implicit

def create(data, schema=None, validate_schema=False, tc=implicit):
    """
    Creates a frame from the given data and schema.  If no schema data types are provided, the schema is inferred
    based on the data in the first 100 rows.

    If schema validation is enabled, all data is is checked to ensure that it matches the schema.  If the data does
    not match the schema's data type, it attempts to cast the data to the proper data type.  When the data is unable
    to be casted to the schema's data type, the item will be missing (None) in the frame.

    :param data: Data source
    :param schema: Optionally specify a schema (list of tuples of string column names and data type), column names
                   (list of strings, and the column data types will be inferred) or None (column data types will be
                   inferred and column names will be numbered like C0, C1, C2, etc).
    :param validate_schema: When True, all data is is checked to ensure that it matches the schema.  If the data does
                            not match the schema's data type, it attempts to cast the data to the proper data type.
                            When the data is unable to be casted to the schema's data type, a ValueError is raised.
                            Defaults to False.
    :param tc: TkContext
    :return: Frame loaded with the specified data


    Examples
    --------

    Create a frame with the specified data.

        >>> data = [["Bob", 30, 8], ["Jim", 45, 9.5], ["Sue", 25, 7], ["George", 15, 6], ["Jennifer", 18, 8.5]]
        >>> frame = tc.frame.create(data)

    Since no schema is provided, the schema will be inferred.  Note that the data set had a mix of strings and
    integers in the third column.  The schema will use the most general data type from the data that it sees, so in
    this example, the column is treated as a float.

        >>> frame.schema
        [('C0', str), ('C1', int), ('C2', float)]

        >>> frame.inspect()
        [#]  C0        C1  C2
        ======================
        [0]  Bob       30    8
        [1]  Jim       45  9.5
        [2]  Sue       25    7
        [3]  George    15    6
        [4]  Jennifer  18  8.5

    We could also enable schema validation, which checks the data against the schema.  If the data does not match the
    schema's data type, it attempts to cast the data to the proper data type.

        >>> frame = tc.frame.create(data, validate_schema=True)

    In this example with schema validation enabled, the integers in column C2 get casted to floats:

        >>> frame.inspect()
        [#]  C0        C1  C2
        ======================
        [0]  Bob       30  8.0
        [1]  Jim       45  9.5
        [2]  Sue       25  7.0
        [3]  George    15  6.0
        [4]  Jennifer  18  8.5

    We could also provide a list of column names when creating the frame.  When a list of column names is provided,
    the data types for the schema are still inferred, but the columns in the schema are labeled with the specified names.

        >>> frame = tc.frame.create(data, schema=["name", "age", "shoe_size"], validate_schema=True)

        >>> frame.schema
        [('name', str), ('age', int), ('shoe_size', float)]

        >>> frame.inspect()
        [#]  name      age  shoe_size
        =============================
        [0]  Bob        30        8.0
        [1]  Jim        45        9.5
        [2]  Sue        25        7.0
        [3]  George     15        6.0
        [4]  Jennifer   18        8.5

    Note that if a value cannot be parsed as the specified data type in the schema, it will show up as missing (None),
    if validate_schema is enabled.  For example, consider the following frame where columns are defined as integers,
    but the data specified has a string in the second row.

        >>> data = [[1, 2, 3], [4, "five", 6]]
        >>> schema = [("a", int), ("b", int), ("c", int)]

        >>> frame = tc.frame.create(data, schema, validate_schema = True)

        >>> frame.inspect()
        [#]  a  b     c
        ===============
        [0]  1     2  3
        [1]  4  None  6

    Note that the spot where the string was located, has it's value missing (None) since it couldn't be parsed to an
    integer.  If validate_schema was disabled, no attempt is made to parse the data to the data type specified by the
    schema, and further frame operations may fail due to the data type discrepancy.

    """
    if tc is implicit:
        implicit.error('tc')    
    from sparktk.frame.frame import Frame
    return Frame(tc, data, schema, validate_schema)
