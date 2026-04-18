from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import torch
from torch import nn as torch_nn

import tradebot.training as nn
from tradebot.root_modules.minirocket_classifier import fit_minirocket, transform_sequences
