"""
Reconcile a gene tree with a species tree using generax without bootstraps.
"""

import topiary
from topiary._private.interface import prep_calc
from topiary._private.interface import write_run_information

from topiary._private import check
from ._generax import setup_generax
from ._generax import run_generax
from ._generax import GENERAX_BINARY

import ete3
import numpy as np

import os, glob, shutil


def reconcile_no_bootstrap(previous_dir,
                           df,
                           model,
                           tree_file,
                           species_tree_file,
                           allow_horizontal_transfer,
                           output,
                           overwrite,
                           num_threads,
                           generax_binary):
    """
    Reconcile the gene tree to the species tree using generax. This should be
    called by generax.reconcile.reconcile

    Parameters
    ----------
    previous_dir : str, optional
        directory containing previous calculation. function will grab the the
        csv, model, and tree from the previous run. If this is not specified,
        `df`, `model`, and `tree_file` arguments must be specified.
    df : pandas.DataFrame or str, optional
        topiary data frame or csv written out from topiary df. Will override
        dataframe from `previous_dir` if specified.
    model : str, optional
        model (i.e. "LG+G8"). Will override model from `previous_dir`
        if specified.
    tree_file : str, optional
        tree_file in newick format. Will override tree from `previous_dir` if
        specified.
    species_tree_file : str, optional
        species tree in newick format.
    allow_horizontal_transfer : bool, default=True
        whether to allow horizontal transfer during reconcilation. If True, use
        the "UndatedDTL" model. If False, use the "UndatedDL" model.
    output: str, optional
        output directory. If not specified, create an output directory with
        form "generax_reconcilation_randomletters"
    overwrite : bool
        whether or not to overwrite existing output directory
    num_threads : int
        number of threads to use. if -1 use all available.
    generax_binary : str
        what generax binary to use

    Returns
    -------
    plot : toyplot.canvas or None
        if running in jupyter notebook, return toyplot.canvas; otherwise, return
        None.
    """

    # Prepare for the calculation, loading in previous calculation and
    # combining with arguments as passed in.
    result = prep_calc(previous_dir=previous_dir,
                       df=df,
                       model=model,
                       tree_file=tree_file,
                       output=output,
                       overwrite=overwrite,
                       output_base="generax_reconcilation")

    df = result["df"]
    csv_file = result["csv_file"]
    model = result["model"]
    tree_file = result["tree_file"]
    alignment_file = result["alignment_file"]
    starting_dir = result["starting_dir"]
    output = result["output"]
    existing_trees = result["existing_trees"]
    start_time = result["start_time"]

    required = [df,model,tree_file]
    for r in required:
        if r is None:
            err = "\nA dataframe, model, and tree are required for this "
            err += "calculation.\n\n"
            raise ValueError(err)

    # Set up generax directory
    setup_generax(df,
                  tree_file,
                  model,
                  "working",
                  species_tree_file=species_tree_file)

    # Actually run generax
    cmd = run_generax(run_directory="working",
                      allow_horizontal_transfer=allow_horizontal_transfer,
                      num_threads=num_threads,
                      generax_binary=generax_binary)

    # Make output directory to hold final outputs
    os.mkdir("output")

    # Copy trees from previous calculation in. This will preserve any that our
    # new calculation did not wipe out.
    for t in existing_trees:
        tree_filename = os.path.split(t)[-1]
        shutil.copy(t,os.path.join("output",tree_filename))

    # Copy in tree.newick
    shutil.copy(os.path.join("working","result","results","reconcile","geneTree.newick"),
                os.path.join("output","tree.newick"))

    # Copy reconcilation information
    shutil.copytree(os.path.join("working","result","reconciliations"),
                    os.path.join("output","reconcilations"))
    shutil.copy(os.path.join("output","reconcilations","reconcile_events.newick"),
                os.path.join("output","tree_events.newick"))

    # Write run information
    write_run_information(outdir="output",
                          df=df,
                          calc_type="reconciliation",
                          model=model,
                          cmd=cmd,
                          start_time=start_time)

    print(f"\nWrote results to {os.path.abspath('output')}\n")

    # Leave working directory
    os.chdir(starting_dir)

    # Write out a summary tree.
    return topiary.draw.tree(run_dir=output,
                             output_file=os.path.join(output,
                                                      "output",
                                                      "summary-tree.pdf"))
