#!/bin/bash

source /home/bleakill/sumo-hooks/env/bin/activate
nohup /usr/bin/python3 /home/bleakill/sumo-hooks/sumo-hooks.py > /home/bleakill/sumo-hooks/output.log 2>&1 &
