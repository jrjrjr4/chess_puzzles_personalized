"""
Filter the raw Lichess puzzle export down to the app's curated pool.

Reconstruction of the original (lost) curation: keep well-liked puzzles
that test at least one of the app's 10 tracked themes and aren't smeared
across too many themes, then take a per-theme quota stratified across
rating levels so every difficulty has coverage.

Usage:
    python scripts/filter_lichess_puzzles.py [path-to-lichess_db_puzzle.csv]

Writes data/filtered_puzzles.csv (same 10 columns as the Lichess export)
and prints a per-theme / per-rating-bucket summary. Upload afterwards with
upload_puzzles_to_supabase.py.
"""
import csv
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))
from puzzle_manager import TRACKED_THEMES  # noqa: E402

RAW_CSV_DEFAULT = r'C:\Users\jason\Downloads\lichess_db_puzzle.csv\lichess_db_puzzle.csv'
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'filtered_puzzles.csv')

POPULARITY_MIN = 95      # Lichess popularity is -100..100; 95+ = widely liked
MAX_THEMES = 4           # puzzles smeared across many themes teach nothing crisp
PER_THEME_TARGET = 6000  # quota per tracked theme (scarce themes take all they have)
BUCKET_SIZE = 400        # rating stratification granularity

COLUMNS = ['PuzzleId', 'FEN', 'Moves', 'Rating', 'RatingDeviation',
           'Popularity', 'NbPlays', 'Themes', 'GameUrl', 'OpeningTags']


def collect_candidates(raw_path):
    """One pass over the raw dump: bucket qualifying rows per tracked theme."""
    # theme -> bucket -> list of (popularity, nb_plays, row)
    per_theme = defaultdict(lambda: defaultdict(list))
    scanned = kept = 0

    with open(raw_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            scanned += 1
            themes = row['Themes'].split()
            tracked = [t for t in themes if t in TRACKED_THEMES]
            if not tracked or len(themes) > MAX_THEMES:
                continue
            try:
                popularity = int(row['Popularity'])
                nb_plays = int(row['NbPlays'])
                rating = int(row['Rating'])
            except ValueError:
                continue
            if popularity < POPULARITY_MIN:
                continue
            kept += 1
            bucket = rating // BUCKET_SIZE * BUCKET_SIZE
            for theme in tracked:
                per_theme[theme][bucket].append((popularity, nb_plays, row))

    print(f'Scanned {scanned:,} rows; {kept:,} pass the quality filters.')
    return per_theme


def select_stratified(per_theme):
    """Take up to PER_THEME_TARGET per theme, spread across rating buckets,
    best-liked first within each bucket. Dedup across themes by PuzzleId."""
    chosen = {}  # PuzzleId -> row
    summary = defaultdict(dict)

    for theme in TRACKED_THEMES:
        buckets = per_theme.get(theme, {})
        if not buckets:
            continue
        for bucket in buckets:
            buckets[bucket].sort(key=lambda t: (t[0], t[1]), reverse=True)

        available = {b: list(rows) for b, rows in buckets.items()}
        remaining = PER_THEME_TARGET
        taken_for_theme = defaultdict(int)

        # Round-robin over buckets: even spread first, spill into deep
        # buckets once shallow ones run dry.
        while remaining > 0 and any(available.values()):
            share = max(1, remaining // max(1, len([b for b in available if available[b]])))
            progressed = False
            for bucket in sorted(available):
                take = min(share, len(available[bucket]), remaining)
                for _ in range(take):
                    popularity, nb_plays, row = available[bucket].pop(0)
                    remaining -= 1
                    taken_for_theme[bucket] += 1
                    progressed = True
                    chosen.setdefault(row['PuzzleId'], row)
                if remaining <= 0:
                    break
            if not progressed:
                break

        summary[theme] = dict(taken_for_theme)

    return chosen, summary


def main():
    raw_path = sys.argv[1] if len(sys.argv) > 1 else RAW_CSV_DEFAULT
    if not os.path.exists(raw_path):
        print(f'Raw Lichess dump not found: {raw_path}')
        print('Download from https://database.lichess.org/#puzzles and pass the CSV path.')
        sys.exit(1)

    per_theme = collect_candidates(raw_path)
    chosen, summary = select_stratified(per_theme)

    out_path = os.path.abspath(OUTPUT_CSV)
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction='ignore')
        writer.writeheader()
        for row in chosen.values():
            writer.writerow(row)

    print(f'\nWrote {len(chosen):,} unique puzzles to {out_path}\n')
    buckets_seen = sorted({b for counts in summary.values() for b in counts})
    header = 'theme'.ljust(20) + ''.join(str(b).rjust(8) for b in buckets_seen) + '   total'
    print(header)
    print('-' * len(header))
    for theme in TRACKED_THEMES:
        counts = summary.get(theme, {})
        total = sum(counts.values())
        line = theme.ljust(20) + ''.join(str(counts.get(b, 0)).rjust(8) for b in buckets_seen)
        print(line + str(total).rjust(8))


if __name__ == '__main__':
    main()
