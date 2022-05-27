
__author__ = "Michael J. Harms"
__date__ = "2021-04-08"
__description__ = \
"""
utility functions for the topiary package
"""

from topiary import _private, _arg_processors

import pandas as pd
import numpy as np

import re, sys, os, string, random, pickle, io, urllib, http, copy

def create_nicknames(df,
                     paralog_patterns,
                     source_column="name",
                     output_column="nickname",
                     separator="/",
                     unassigned_name="unassigned",
                     overwrite_output=False,
                     ignorecase=True):
    """
    Create a nickname column that has a friendly nickname for each sequence,
    generated by looking for patterns defined in the 'paralog_patterns'
    dictionary in 'source_column' column from the dataframe.

    Parameters
    ----------
        df: topiary dataframe
        paralog_patterns: dictionary for creating standardized nicknames from
                          input names. Key specifies what should be output, values
                          the a list of patterns that map back to that key.  For
                          example:

                          {"S100A9":["S100-A9","S100 A9","S-100 A9","MRP14"],
                           "S100A8":["S100-A8","S100 A8","S-100 A9","MRP8"]}

                          would assign "S100A9" to any sequence matching patterns
                          only from its list; "S100A8" to any sequence matching
                          patterns only from its list; and S100A9/S100A8 to any
                          sequence matching patterns from both lists.
        source_column: source column in dataframe to use to generate a nickname
                       (accessed via df.loc[:,source_column])
        output_column: column in which to store newly constructed nicknames
                       (accessed via df.loc[:,output_column])
        separator: "/" character to place between nicknames if more than one
                   pattern matches.
        unassigned_name: nickname to give sequences that do not match any of
                         the patterns.
        overwrite_output: boolean (default False). overwrite an existing output
                          column
        ignorecase: boolean (default True). Whether or not to ignore the case
                    of matches when assigning the nickname.

    Returns
    -------
        Copy of dataframe with new nickname column
    """

    # Parse 'df' argument
    if type(df) is not pd.DataFrame:
        err = "\ndf should be a pandas dataframe\n\n"
        raise ValueError(err)

    # Check to make sure the specified source column exists
    try:
        df.loc[:,source_column]
    except KeyError:
        err = f"\ndataframe does not have source_column '{source_column}'\n\n"
        raise ValueError(err)

    # Make sure the output column is not reserved by topiary
    if output_column in _private.reserved_columns:
        err = f"\n'{output_column}' is a reserved column name. Please choose\n"
        err += "another column name.\n\n"
        raise ValueError(err)

    # Make sure the output_column does not exist or that we're allowed to
    # overwrite
    try:
        df.loc[:,output_column]
        if not overwrite_output:
            err = f"\ndataframe already has output_column '{output_column}'.\n"
            err += "To overwrite set overwrite_output = True\n\n"
            raise ValueError(err)
    except KeyError:
        pass

    # check unassigned_name argument
    if type(unassigned_name) is not str:
        err = "\nunassigned_name should be a string.\n\n"
        raise ValueError(err)

    # check separator argument
    if type(separator) is not str:
        err = "\nseparator should be a string.\n\n"
        raise ValueError(err)

    patterns = _arg_processors.process_paralog_patterns(paralog_patterns,
                                                        ignorecase=ignorecase)

    # Get entries from source column
    source = [entry for entry in df.loc[:,source_column]]
    out = []
    for i, s in enumerate(source):

        out.append([])

        # Go over every patterns
        for p in patterns:

            # If we find the pattern in the entry, break; we only need
            # to note we found it once
            if p[0].search(source[i]):
                out[-1].append(p[1])
                break

        # Join list of hits
        out[-1] = f"{separator}".join(out[-1])

        # No hit, give unassigned_name
        if out[-1] == "":
            out[-1] = unassigned_name

    # Return an edited copy of the dataframe
    df = df.copy()
    df.loc[:,output_column] = out

    # Validate topiary dataframe to make sure not mangled; will also update
    # column order so nickname is early and thus in a user-friendly place

    return _arg_processors.process_topiary_dataframe(df)
