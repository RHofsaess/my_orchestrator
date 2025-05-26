# Yet Not Another HEPscore Orchestrator
This project is a lightweight orchestrator for running HEPscore benchmarks.
It is wrapping around the hep-benchmark-suite toolset and extends it by the possibility of running multiple benchmarks with different configurations.
This is particularly useful for development purposes and less for the actual benchmarking later on.


### Dependencies


## Concept


## Configuration

## Setup and Dependencies
For setting up the tool, current requirements are:
- python > 3.6
- `PyYAML` (for writing the hepscore configs)

The setup itself has to be executed at first, simply by: `$ python3 main.py --install`.



## Notes
- The HEPscore suite also reports back an exit code of 0 if the run failed. The run logs are therefore explicitly evaluated
- After config changes, one should run --delete!
- 
## Tl;dr
1) clone: `$ git clone https://github.com/rhofsaess/my_orchestrator`
2) TODO