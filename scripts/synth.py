#!/usr/bin/env python3
import argparse
import numpy as np
import pandas as pd
import csv
import os
import time
import datetime
import sys
import logging
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class HFTStressTestGenerator:
    initial_price: float = 100.0
    base_spread: float = 0.01

    def _generate_pattern(self, t_array: np.ndarray, pattern_timeframes: List[float]) -> np.ndarray:
        signal = np.zeros_like(t_array)
        if not pattern_timeframes:
            return signal
        
        for tf in pattern_timeframes:
            signal += np.sin(2 * np.pi * t_array / tf)
        
        return signal * 0.001 

    def simulate(self,
               duration_secs: float = 600,
               randomness_intensity: float = 0.5,
               pattern_timeframes: Optional[List[float]] = None,
               mu: float = 0.5,
               alpha: float = 0.3,
               beta: float = 1.0,
               volatility: float = 0.0005) -> pd.DataFrame:
        timestamps = []
        t = 0
        while t < duration_secs:
            lambda_bar = mu + sum([alpha * np.exp(-beta * (t - ti)) for ti in timestamps if t > ti]) + alpha
            U = np.random.uniform(0, 1)
            t += -np.log(U) / lambda_bar
            if t >= duration_secs: break
            
            current_lambda = mu + sum([alpha * np.exp(-beta * (t - ti)) for ti in timestamps])
            if np.random.uniform(0, 1) < (current_lambda / lambda_bar):
                timestamps.append(t)
        
        t_array = np.array(timestamps)
        num_ticks = len(t_array)
        
        if pattern_timeframes is None:
            pattern_timeframes = [9, 54]
        
        signal_component = self._generate_pattern(t_array, pattern_timeframes)
        
        dt = np.diff(np.insert(t_array, 0, 0))
        z = np.random.normal(0, 1, num_ticks)
        
        stochastic_path = np.cumsum(volatility * np.sqrt(dt) * z)
        
        combined_returns = ((1 - randomness_intensity) * signal_component) + \
                           (randomness_intensity * stochastic_path)
        
        prices = self.initial_price * (1 + combined_returns)
        
        intensities = np.array([mu + sum([alpha * np.exp(-beta * (t - ti)) for ti in timestamps if t > ti]) for t in t_array])
        spreads = self.base_spread * (1 + (intensities / mu) * randomness_intensity)

        start_time = datetime.datetime.now()
        df = pd.DataFrame({
            'timestamp': [start_time + datetime.timedelta(seconds=ts) for ts in t_array],
            'seconds': t_array,
            'last': prices,
            'bid': prices - (spreads / 2),
            'ask': prices + (spreads / 2)
        })
        return df


def get_stats(df: pd.DataFrame, name: str) -> None:
    print(f"--- {name} ---")
    print(f"Tick Count: {len(df)}")
    print(f"Avg Spread: {(df['ask'] - df['bid']).mean():.5f}")
    print(f"Price StdDev: {df['last'].std():.5f}\n")


def parse_timeframes(timeframe_str: str) -> List[float]:
    if not timeframe_str:
        return []
    return [float(x.strip()) for x in timeframe_str.split(',') if x.strip()]


def main():
    parser = argparse.ArgumentParser(
        description="HFT Stress Test Generator - Generate synthetic tick data with SNR approach"
    )
    parser.add_argument(
        '-d', '--duration',
        type=float,
        default=600,
        help='Duration in seconds (default: 600)'
    )
    parser.add_argument(
        '-r', '--randomness',
        type=float,
        default=0.5,
        dest='randomness_intensity',
        help='Randomness intensity 0=pure pattern, 1=pure chaos (default: 0.5)'
    )
    parser.add_argument(
        '-t', '--timeframes',
        type=str,
        default='9,54',
        help='Comma-separated timeframe periods in seconds (default: 9,54)'
    )
    parser.add_argument(
        '-n', '--name',
        type=str,
        default='',
        help='Custom name for output file'
    )
    parser.add_argument(
        '-p', '--initial-price',
        type=float,
        default=100.0,
        help='Initial price (default: 100.0)'
    )
    parser.add_argument(
        '-s', '--spread',
        type=float,
        default=0.01,
        help='Base spread (default: 0.01)'
    )
    parser.add_argument(
        '--mu',
        type=float,
        default=0.5,
        help='Hawkes mu parameter - base tick rate (default: 0.5)'
    )
    parser.add_argument(
        '--alpha',
        type=float,
        default=0.3,
        help='Hawkes alpha parameter - cluster intensity (default: 0.3)'
    )
    parser.add_argument(
        '--beta',
        type=float,
        default=1.0,
        help='Hawkes beta parameter - decay (default: 1.0)'
    )
    parser.add_argument(
        '--volatility',
        type=float,
        default=0.0005,
        help='Volatility for Brownian motion (default: 0.0005)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '-w', '--overwrite',
        action='store_true',
        help='Overwrite if file exists'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='Random seed for reproducibility'
    )
    parser.add_argument(
        '--precision',
        type=int,
        default=6,
        help='Decimal precision for float values (default: 6)'
    )
    parser.add_argument(
        '--ticks',
        type=int,
        default=None,
        help='Alternative: specify exact tick count (overrides duration)'
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logging.info("Starting HFT stress test generation")
    
    if len(sys.argv) == 1:
        current = datetime.datetime.now()
        mmss = current.strftime("%M%S")
        args.name = f"d{mmss}"
        logging.info(f"No arguments provided, using defaults: duration={args.duration}s, "
                    f"randomness={args.randomness_intensity}, name={args.name}")
    
    if not args.name:
        current = datetime.datetime.now()
        args.name = current.strftime("%M%S")
        args.name = f"d{args.name}"
    
    args.name = ''.join(c if c.isalnum() or c in '-_' else '_' for c in args.name)
    if not args.name:
        args.name = 'unnamed'
    
    if args.randomness_intensity < 0 or args.randomness_intensity > 1:
        logging.error(f"Randomness must be 0-1, got {args.randomness_intensity}")
        print(f"ERROR: Randomness must be 0-1, got {args.randomness_intensity}")
        sys.exit(1)
    
    if args.duration <= 0 and args.ticks is None:
        logging.error(f"Duration must be > 0, got {args.duration}")
        print(f"ERROR: Duration must be > 0, got {args.duration}")
        sys.exit(1)
    
    filename = f'data/synth/{args.name}.csv'
    filename = filename.rstrip('.csv') + '.csv'
    if os.path.exists(filename) and not args.overwrite:
        logging.error(f"File already exists: {filename}")
        print(f"ERROR: File already exists: {filename}")
        sys.exit(1)
    
    if args.seed is not None:
        np.random.seed(args.seed)
        logging.info(f"Random seed set to {args.seed}")
    
    pattern_timeframes = parse_timeframes(args.timeframes)
    logging.info(f"Pattern timeframes: {pattern_timeframes}")
    
    gen = HFTStressTestGenerator(
        initial_price=args.initial_price,
        base_spread=args.spread
    )
    
    if args.ticks:
        logging.info(f"Estimating duration for {args.ticks} ticks with mu={args.mu}")
        expected_ticks = args.mu * args.duration
        if args.ticks > expected_ticks:
            args.duration = args.ticks / args.mu * 1.5
            logging.info(f"Adjusted duration to {args.duration}s to achieve target ticks")
    
    df = gen.simulate(
        duration_secs=args.duration,
        randomness_intensity=args.randomness_intensity,
        pattern_timeframes=pattern_timeframes,
        mu=args.mu,
        alpha=args.alpha,
        beta=args.beta,
        volatility=args.volatility
    )
    
    if args.ticks and len(df) != args.ticks:
        logging.warning(f"Requested {args.ticks} ticks but generated {len(df)}")
    
    logging.info(f"Generated {len(df)} ticks")
    get_stats(df, args.name)
    
    os.makedirs('data/synth', exist_ok=True)
    
    logging.info(f"Saving to {filename}")
    fmt = f'%.{args.precision}f'
    
    msc_times = (df['seconds'].values * 1000).astype(np.int64)
    start_msc = int(time.time() * 1000)
    msc_times = msc_times + start_msc
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time_msc', 'bid', 'ask'])
        for i in range(len(df)):
            writer.writerow([
                msc_times[i],
                fmt % df.iloc[i]['bid'],
                fmt % df.iloc[i]['ask']
            ])
    
    logging.info("Data generation and saving completed")
    print(f"Generated {len(df)} ticks and saved to {filename}")


if __name__ == '__main__':
    main()