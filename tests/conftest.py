import pytest
import pandas as pd
import os, glob, inspect

@pytest.fixture(scope="module")
def ncbi_lines():
    """
    A list of generic ncbi lines.
    """

    return ["sp|Q9Y6Y9|LY96_HUMAN Lymphocyte antigen 96 OS=Homo sapiens OX=9606 GN=LY96 PE=1 SV=2"]

@pytest.fixture(scope="module")
def ncbi_lines_parsed():
    """
    A list of parse results for those ncbi_lines.
    """

    parsed_lines =  [{"structure":False,
                      "low_quality":False,
                      "predicted":False,
                      "precursor":False,
                      "isoform":False,
                      "hypothetical":False,
                      "partial":False}]

    return parsed_lines

@pytest.fixture(scope="module")
def dataframe_good_files():
    """
    A list of files that should be properly parsable by topiary.
    """

    dir = os.path.dirname(os.path.realpath(__file__))
    files = glob.glob(os.path.join(dir,"data","supported-df-formats","*"))

    return files

@pytest.fixture(scope="module")
def reverse_blast_hit_dfs():
    """
    Load saved hit_dfs output.
    """

    def _load(prefix):

        dir = os.path.dirname(os.path.realpath(__file__))
        files = glob.glob(os.path.join(dir,
                                       "data",
                                       "reverse_blast",
                                       f"{prefix}_hit_dfs",
                                       "*.csv"))
        files.sort()
        for i in range(len(files)):
            files[i] = pd.read_csv(files[i])

        return files

    return {"ncbi":_load("ncbi"),"local":_load("local")}


@pytest.fixture(scope="module")
def test_dataframes():
    """
    A dictionary holding dataframes of varying sorts of badness to test parser.
    """

    dir = os.path.dirname(os.path.realpath(__file__))
    search_string = os.path.join(dir,"data","*.csv")

    df_dict = {}
    for g in glob.glob(search_string):
        key = ".".join(os.path.split(g)[1].split(".")[:-1])
        df_dict[key] = pd.read_csv(g)

    return df_dict


def get_public_param_defaults(public_function,private_function):
    """
    Get the defaults for a public function in the API that then passes
    a subset of its arguments directly into a private function. This allows
    us to test the defaults on the public api without having to hardcode
    them into the tests.
    """

    public_param = inspect.signature(public_function).parameters
    private_param = inspect.signature(private_function).parameters

    kwargs = {}
    for p in private_param:
        try:
            default = public_param[p].default
        except KeyError:
            # If here, private function has a private argument
            continue

        if default is not inspect._empty:
            kwargs[p] = public_param[p].default

    return kwargs
