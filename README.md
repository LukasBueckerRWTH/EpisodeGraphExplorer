# Episode Graph Explorer
Standalone Python Application allowing for exploration of Episodes

## Table of Contents
- [EpisodeGraphExplorer](#Episode-Graph-Explorer)
    - [Install](#install)
    - [Required data](#required-data)
    - [Usage](#usage)
    - [Test data](#test-data)

## Installation
Either:
1. Download the Windows Executeable under [Releases](https://github.com/LukasBueckerRWTH/EpisodeGraphExplorer/releases)
2. Clone the repository and install all packages from requirements.txt

## Required data
Requires:
1. An xes event log
2. A list of episodes. Example episode extraction done using [ProM](https://promtools.org/) and the [PADSUtils](https://github.com/promworkbench/PADSUtils/) package (Minimum version 6.16.7)

## Usage
Either:
1. Run the downloaded executeable
2. Run the python file for the EpisodeGraphExplorer:
```sh
python EpisodeGraphExplorer.py
```

## Test data
We provide three event logs ([Process Discovery Challenge 2025](https://doi.org/10.4121/7212a73a-1eac-4a08-8c01-973dca020822),[Sepsis Cases - Event Log](https://doi.org/10.4121/uuid:915d2bfb-7e84-49ad-a286-dc35f063a460) and a custom event log) with some episode files.