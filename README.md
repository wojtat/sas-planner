# SAS Optimal Planner

Author: *Vojtěch Tilhon*, e-mail: *vojtech.tilhon@seznam.cz*

## About

This project was implemented for the PUI (Planning for Artificial Intelligence) course at FEE CTU.
No guarantees about the functionality of the code are given.

The `data/` directory contains 3 example SAS tasks which can be used.

The `planner.py` Python script takes an FDR task as a SAS file
and finds an optimal plan using the A* algorithm and the $h_{\max}$ or the LM-cut heuristic.
The found path is printed to the standard output.

The `hmax.py` file contains an implementation of the $h_{\max}$ heuristic.
Running the script prints out the value of the heuristic in the initial state of the provided FDR task.

The `lmcut.py` file contains the implementation of the LM-cut heuristic.
Running the script prints out the value of the heuristic in the initial state of the provided FDR task.

The `sas.py` file implements a SAS file parser and a utility function for transforming FDR tasks into
delete relaxed STRIPS tasks.
