#!/bin/bash

nohup  python3 -u foretify_checker.py > log_jsonl.txt 2>&1 &

nohup  python3 -u foretify_checker_with_error.py > log_jsonl.txt 2>&1 &
