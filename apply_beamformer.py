#!/usr/bin/env python
# coding=utf-8
# wujian@17.11.9

import os
import pickle
import glob
import json
import argparse

import torch as th
import numpy as np
from torch.autograd import Variable

from model import MaskComputer, MaskEstimator 
from fgnt.beamforming import mvdr_wrapper_on_masks, gev_wrapper_on_masks
from fgnt.signal_processing import audioread, audiowrite, stft, istft


num_bins = 513

# compatiable with 2/6ch 
def load_multichannel_data(prefix):
    audio_mat = [audioread(f) for f in glob.glob('{}.CH[1-6].wav'.format(prefix))]
    return np.array(audio_mat).astype(np.float32)


# {dt|et}05_{bus|caf|ped|str}_{real|simu}
def apply_beamfomer(args):
    estimator = MaskEstimator(num_bins) 
    mask_computer = MaskComputer(estimator, args.model)
    
    flist_name = os.path.basename(args.flist)
    sub_dir = flist_name.split('.')[0]
    dumps_dir = os.path.join(args.dumps_dir, sub_dir)

    func_bf = mvdr_wrapper_on_masks if not args.gev else \
            gev_wrapper_on_masks

    if not os.path.exists(dumps_dir):
        os.makedirs(dumps_dir)

    with open(args.flist, 'r') as f:
        flist = f.readlines()

    for f in flist:
        f = f.strip()
        tokens  = f.split('/')
        noisy_samples = load_multichannel_data(f)
        noisy_specs   = stft(noisy_samples, time_dim=1).transpose((1, 0, 2))
        mask_n, mask_x = mask_computer.compute_masks(np.abs(noisy_specs).astype(np.float32))
        mask_n = np.median(mask_n, axis=1)
        mask_x = np.median(mask_x, axis=1)
        clean_specs   = func_bf(noisy_specs, mask_n, mask_x) 
        clean_samples = istft(clean_specs)
        print('dumps to {}/{}.wav'.format(dumps_dir, tokens[-1]))
        audiowrite(clean_samples, '{}/{}.wav'.format(dumps_dir, tokens[-1]), 16000, True, True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Command to apply MVDR/GEV beamformer")
    parser.add_argument("model", type=str, 
                        help="path of model states generated by train_estimator.py")
    parser.add_argument("flist", type=str, 
                        help="a list of wave to processed")
    parser.add_argument("--dumps-dir", type=str, default="enhan", dest="dumps_dir",
                        help="output directory of enhanced data")
    parser.add_argument("--gev", action='store_true', default=False, dest="gev",
                        help="apply GEV beamforming instead of MVDR")
    args = parser.parse_args()
    apply_beamfomer(args)