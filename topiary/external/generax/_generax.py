
# raxml binary to use it not specified by user
GENERAX_BINARY = "generax"

import topiary

import numpy as np

import subprocess, os, sys, time, random, string, shutil, copy
import multiprocessing as mp

def _create_generax_input(df,gene_tree):
    """
    Take a dataframe and generate the data structures necessary for a GeneRax
    run.

    df: topiary data frame.
    gene_tree: gene tree with uid taxon names.

    returns consistently named gene_tree, species_tree, and link_dict
    """

    # Arbitrarily resolve any polytomies in genet tree
    gene_tree.resolve_polytomy()

    # Map uid to ott in the dataframe
    uid_to_ott = {}
    for i in range(len(df)):
        uid = df.uid.iloc[i]
        ott = df.ott.iloc[i]
        uid_to_ott[uid] = ott

    uid_in_gene_tree = []
    link_dict = {}
    for l in gene_tree.get_leaves():

        uid = l.name
        ott = uid_to_ott[uid]

        # For generating mapping file, record which uid are associated with what ott
        try:
            link_dict[ott].append(uid)
        except KeyError:
            link_dict[ott] = [uid]

        # Record that we saw this uid
        uid_in_gene_tree.append(uid)

    # Make df only have uid seen (will automatically trim down to only ott
    # of interest)
    mask = np.array([u in uid_in_gene_tree for u in df.uid],dtype=np.bool)
    df = df.loc[mask]

    # Get species tree for the dataframe
    species_tree = topiary.get_species_tree(df)

    # Resolve polytomies and make sure all branch lenghts/supports have values
    species_tree.resolve_polytomy()
    for n in species_tree.traverse():
        if n.dist != 1:
            n.dist = 1
        if n.support != 1:
            n.support = 1

    return gene_tree, species_tree, link_dict

def _write_generax_input(df,gene_tree,species_tree,link_dict,model,out_dir):
    """
    Write out files for running generax. The contents of this directory can be
    run on the command line by:

    df: topiary data frame
    gene_tree: gene tree returned from _create_generax_input
    species_tree: species tree returned from _create_generax_input
    link_dict: link_dict returned from _create_generax_input
    model: phylogenetic model to use (should match ml tree)
    out_dir: output directory to write files
    """

    # Construct the control file for generax
    control_out = []
    control_out.append("[FAMILIES]")
    control_out.append("- reconcile")
    control_out.append("starting_gene_tree = gene_tree.newick")
    control_out.append("alignment = alignment.phy")
    control_out.append("mapping = mapping.link")
    control_out.append(f"subst_model = {model}")

    # Write out control file
    f = open(os.path.join(out_dir,"control.txt"),"w")
    f.write("\n".join(control_out))
    f.close()

    # Write out .phy file
    topiary.write_phy(df,os.path.join(out_dir,"alignment.phy"),
                      seq_column="alignment")

    # Write out gene tree
    gene_tree.write(outfile=os.path.join(out_dir,"gene_tree.newick"),
                    format=5)

    # Write out species tree
    species_tree.write(outfile=os.path.join(out_dir,"species_tree.newick"))

    # Write out link file
    f = open(os.path.join(out_dir,"mapping.link"),"w")
    for k in link_dict:
        f.write(f"{k}:")
        f.write(";".join(link_dict[k]))
        f.write("\n")
    f.close()

def setup_generax(df,
                  gene_tree,
                  model,
                  out_dir,
                  dir_with_bootstraps=None):

    if os.path.isdir(out_dir):
        err = f"out_dir '{out_dir}' already exists."
        raise FileExistsError(err)

    os.mkdir(out_dir)
    template_dir = os.path.join(out_dir,"ml")
    os.mkdir(template_dir)

    # Create generax data structures
    gene_tree, species_tree, link_dict = _create_generax_input(df,gene_tree)

    # Write out generax input
    _write_generax_input(df,gene_tree,species_tree,link_dict,model,template_dir)



def gen_seed():
    """
    Generate a random string of 10 integers and return as a string.
    """

    return "".join([f"{random.choice(range(10)):d}" for _ in range(10)])


def _subproc_wrapper(cmd,stdout,queue):
    """
    Wrap the subprocess.run call to allow multithreading.

    args: args to pass to subprocess.run
    kwargs: kwargs to pass to subprocess.run
    queue: multiprocessing queue to catch return value
    """

    ret = subprocess.run(cmd,stdout=stdout)
    queue.put(ret)

def _follow_log_generator(f,p):
    """
    Generator function that follows some file object (f) until some
    multiprocessing Process (p) is not longer alive. This is useful for
    following a log file being spit out by an external program running on p.

    f: open file object
    p: multiprocessing.Process object
    """

    # start infinite loop
    while p.is_alive():
        # read last line of file
        line = f.readline()
        # sleep if file hasn't been updated
        if not line:
            time.sleep(0.1)
            continue

        yield line


def run_generax(run_directory,
                allow_horizontal_transfer=False,
                seed=None,
                generax_binary=GENERAX_BINARY,
                log_to_stdout=True,
                other_args=[]):

    """
    Run generax. Creates a working directory, copies in the relevant files, runs
    there, and then returns to the previous directory.

    algorithm: algorithm to run (--all, --ancestral, etc.)
    alignment_file: alignment file in .phy format (passed via --msa)
    tree_file: tree file in .newick format (passed via --tree)
    model: model in format recognized by --model
    dir_name: If specified, this will be the name of the working directory.
    seed: true/false, int, or str. If true, pass a randomly generated seed to
          raxml. If int or str, use that as the seed. (passed via --seed)
    threads: number of threads to use (passed via --threads)
    raxml_binary: raxml binary to use
    log_to_stdout: capture log and write to std out.
    other_args: list of arguments to pass to raxml
    """

    cmd = ["generax"]
    cmd.extend(["--families","control.txt"])
    cmd.extend(["--species-tree","species_tree.newick"])
    cmd.extend(["--prefix","result"])

    if allow_horizontal_transfer:
        model = cmd.extend(["--rec-model","UndatedDTL"])
    else:
        model = cmd.extend(["--rec-model","UndatedDL"])

    # seed argument is overloaded. Interpret based on type
    if seed is not None:
        if type(seed) is int:
            cmd.extend(["--seed",f"{seed:d}"])
        elif type(seed) is str:

            try:
                int(seed)
            except ValueError:
                err = f"seed {seed} could not be interpreted as an int\n"
                raise ValueError(err)

            cmd.extend(["--seed",seed])
        elif type(seed) is bool:
            if seed:
                cmd.extend(["--seed",gen_seed()])
        else:
            err = "seed must be True/False, int, or string representation of int\n"
            raise ValueError(err)

    # Grab other args
    cmd.extend(other_args)

    # Make sure that generax is in the path
    try:
        subprocess.run([generax_binary])
    except FileNotFoundError:
        err = f"\ngenerax binary '{generax_binary}' not found in path\n\n"
        raise ValueError(err)

    if not os.path.exists(run_directory):
        err = f"\nrun_directory '{run_directory}' not found.\n\n"
        raise FileNotFoundError(err)

    if not os.path.isdir(run_directory):
        err = f"\nrun_directory must be a directory not found.\n\n"
        raise ValueError(err)

    required_files = ["control.txt","alignment.phy",
                      "gene_tree.newick","species_tree.newick"]
    for f in required_files:
        filename = os.path.join(run_directory,f)
        if not os.path.exists(filename):
            err = f"\nrun_directory '{run_directory}' does not have all required\n"
            err += "files. It should have the following files:\n"
            for r in required_files:
                err += f"    {r}\n"
            err += "\n"
            raise FileNotFoundError(err)

    # Go into working directory
    cwd = os.getcwd()
    os.chdir(run_directory)

    # Print command
    full_cmd = " ".join(cmd)
    print(f"Running '{full_cmd}'",flush=True)

    # Launch generax as a multiprocessing process dumping its output to a
    # multiprocessing queue.
    queue = mp.Queue()
    main_process = mp.Process(target=_subproc_wrapper,
                              args=(cmd,subprocess.PIPE,queue))
    main_process.start()

    # If dumping log
    log_file = os.path.join("result","generax.log")
    if log_to_stdout:

        # While main process is running
        while main_process.is_alive():

            # If queue is empty, raxml job hasn't finished yet
            if not queue.empty():
                break

            # Try to open log every second
            try:
                f = open(log_file,"r")
                # Use follow generator function to catch lines as the come out
                for line in _follow_log_generator(f,main_process):
                    sys.stdout.write(line)
                    sys.stdout.flush()
                f.close()
            except FileNotFoundError:
                time.sleep(1)

    # Wait for main process to complete and get return
    main_process.join()
    ret = queue.get()

    # Check for error on return
    if ret.returncode != 0:
        err = f"ERROR: generax returned {ret.returncode}\n\n"
        err += "------------------------------------------------------------\n"
        err += " generax output \n"
        err += "------------------------------------------------------------\n"
        err += "\n\n"

        err += "".join([line for line in ret.stdout.decode()])

        raise RuntimeError(err)

    # Leave working directory
    os.chdir(cwd)
