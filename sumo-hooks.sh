#!/bin/bash

source ./env/bin/activate
nohup python3 sumo-hooks.py > output.log 2>&1 &