import gzip
import io
import json
import logging
import re
import tempfile
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count
from os import path

import pyrouge
from tqdm import tqdm

depunct = re.compile(r"[^a-zA-Z0-9]")

def compute_rouge(x):
    system, reference = x
    rouge = pyrouge.Rouge155()

    # this doesn't disable the logging from perl
    rouge.log = logging.getLogger("pyrouge")
    rouge.log.setLevel(logging.ERROR)


    # fmt: off
    with tempfile.TemporaryDirectory("-system") as system_folder, \
         tempfile.TemporaryDirectory("-reference") as reference_folder:
    # fmt: on

        rouge.system_dir = system_folder
        rouge.model_dir = reference_folder

        rouge.system_filename_pattern = r"(\d+).txt"
        rouge.model_filename_pattern = "#ID#.txt"

        # remove non alphabetic and numeric characters
        system = depunct.sub(" ", system)
        reference = depunct.sub(" ", reference)

        with open(path.join(rouge.system_dir, "1.txt"), "w", encoding = "utf-8") as f:
            f.write(system)

        with open(path.join(rouge.model_dir, "1.txt"), "w", encoding = "utf-8") as f:
            f.write(reference)

        output = rouge.convert_and_evaluate()
        result = rouge.output_to_dict(output)

        # close and delete folder with its contents

    cols = []
    for metric in ["recall", "precision", "f_score"]:
        for n in ["1", "2", "l"]:
            col = "rouge_%s_%s" % (n, metric)
            cols.append(col)

    result = {c: result[c] for c in cols}
    return result

def gzip_jsonl_reader(system_filename: str, reference_filename: str, s_key: str, r_key: str):
    with gzip.open(system_filename) as system_fh, \
         gzip.open(reference_filename) as reference_fh:

        for system_line, reference in zip(system_fh, reference_fh):
            system, reference = json.loads(system_line), json.loads(reference)
            yield system[s_key], reference[r_key]

if __name__ == "__main__":
    import os
    DATAFOLDER = "/data"
    reference_file = os.environ["REFERENCE"]
    system_file = os.environ["SYSTEM"]
    score_file = os.environ["SCORE"]
    threshold = int(os.environ.get("THRESHOLD", 100))
    # gzipped = "GZIP" in os.environ

    cores = cpu_count()

    system_file = path.join(DATAFOLDER, reference_file)
    reference_file = path.join(DATAFOLDER, reference_file)
    score_file = path.join(DATAFOLDER, score_file)
    with ProcessPoolExecutor(cores) as executor:
        with open(score_file, "w") as score_file:
            chunk = []
            gzip_reader = gzip_jsonl_reader(system_file, reference_file, s_key="summary", r_key="summary")
            progress_bar = tqdm()
            for system, reference in gzip_reader:
                chunk.append((system, reference))
                
                if len(chunk) >= threshold:
                    scores = executor.map(compute_rouge, chunk)
                    for s in scores:
                        score_file.write(json.dumps(s) + "\n")
                    progress_bar.update(len(chunk))
                    chunk = []

            # else:
            #     with io.open(system_file, newline="\n") as system_fh, \
            #         io.open(reference_file, newline="\n") as reference_fh:
                    
            #         for system, reference in zip(system_fh, reference_fh):
            #             scores = compute_rouge(system, reference, stem=False)
            #             score_file.write(json.dumps(scores) + "\n")
