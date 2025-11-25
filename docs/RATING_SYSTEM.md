# Rating System

This document explains how the chess puzzle rating system works in detail.

## Overview

The app tracks your skill level across **10 tactical categories** using an Elo-based rating system. Each category has its own rating that evolves independently as you solve puzzles.

## The 10 Tracked Categories

| Category | Key | What It Measures |
|----------|-----|------------------|
| **Pin** | `pin` | Ability to pin pieces against more valuable ones or the king |
| **Fork** | `fork` | Attacking multiple pieces simultaneously with one piece |
| **Mate** | `mate` | Recognizing and executing checkmate patterns |
| **Defense** | `defensiveMove` | Finding defensive resources and counter-tactics |
| **Endgame** | `endgame` | Technique in simplified positions |
| **Deflection** | `deflection` | Luring defenders away from key squares |
| **Quiet Move** | `quietMove` | Finding non-capturing winning moves |
| **Kingside Attack** | `kingsideAttack` | Attacking patterns against the castled king |
| **Discovered Attack** | `discoveredAttack` | Using discovered attacks and checks |
| **Capturing Defender** | `capturingDefender` | Removing key defensive pieces |

## How Ratings Work

### Starting Point

Every new user starts with **1600** rating in all categories. This is considered an "average club player" level.

### The Elo Formula

When you attempt a puzzle, your rating changes based on:

1. **Your current rating** in the relevant category
2. **The puzzle's rating** (difficulty)
3. **Whether you solved it** (success/failure)
4. **Your K-factor** (how much ratings can change)

The formula:

```
Expected Score = 1 / (1 + 10^((puzzle_rating - your_rating) / 400))
Rating Change = K × (Actual - Expected)
```

Where:
- `Actual` = 1 if you solved it, 0 if you failed
- `Expected` = probability you "should" solve it based on ratings

### Example Calculations

**Example 1: Equal Ratings**
- Your rating: 1600
- Puzzle rating: 1600
- Expected score: 0.5 (50% chance)
- K-factor: 100

If you **solve** it:
```
Change = 100 × (1 - 0.5) = +50 points
New rating: 1650
```

If you **fail** it:
```
Change = 100 × (0 - 0.5) = -50 points
New rating: 1550
```

**Example 2: Harder Puzzle (Upset Win)**
- Your rating: 1400
- Puzzle rating: 1600
- Expected score: 0.24 (24% chance)
- K-factor: 100

If you **solve** it:
```
Change = 100 × (1 - 0.24) = +76 points
New rating: 1476
```

**Example 3: Easier Puzzle (Upset Loss)**
- Your rating: 1800
- Puzzle rating: 1600
- Expected score: 0.76 (76% chance)
- K-factor: 100

If you **fail** it:
```
Change = 100 × (0 - 0.76) = -76 points
New rating: 1724
```

## The K-Factor System

The K-factor determines how much your rating can change per puzzle. It **decreases** as you solve more puzzles in a category, making your rating more stable over time.

### K-Factor Progression

| Attempts in Category | K-Factor | Description |
|---------------------|----------|-------------|
| 0 | 250 | First attempt - big swing to find your level |
| 1-2 | 200 | Very early - still calibrating |
| 3-5 | 150 | Learning phase |
| 6-10 | 100 | Developing |
| 11-20 | 60 | Intermediate |
| 21-35 | 40 | Experienced |
| 35+ | 25 | Established - stable rating |

### Why This Matters

- **New categories**: Your rating moves quickly to find your true level
- **Established categories**: Small changes prevent fluky results from skewing your rating
- **Each category is independent**: You might be established in "Fork" but new to "Endgame"

## Minimum Rating Changes

To ensure you always see meaningful progress, we enforce **minimum rating changes**:

| Attempts | Minimum Change |
|----------|----------------|
| 0-5 | ±50 points |
| 6-15 | ±30 points |
| 16+ | ±15 points |

This prevents situations where solving a much easier puzzle gives you only +2 points. You'll always gain or lose at least the minimum amount.

## Rating Bounds

Ratings are clamped between:
- **Minimum**: 400 (beginner)
- **Maximum**: 2800 (world-class)

## Overall Rating

Your **overall rating** is the average of all 10 category ratings:

```
Overall = (Pin + Fork + Mate + Defense + Endgame + Deflection + 
           QuietMove + KingsideAttack + DiscoveredAttack + CapturingDefender) / 10
```

Categories you haven't played yet use the default rating (1600).

## Adaptive Puzzle Selection

When you're logged in, the app intelligently selects puzzles to help you improve:

### 1. Category Weighting

Categories are weighted by how weak you are in them:

```python
weight = (2800 - your_rating) ^ 1.3
```

This exponential formula strongly favors your weakest categories:

| Your Rating | Weight (approx) |
|-------------|-----------------|
| 1000 | 8,500 |
| 1200 | 6,000 |
| 1400 | 4,000 |
| 1600 | 2,500 |
| 1800 | 1,500 |
| 2000 | 800 |

### 2. Category Selection

A category is chosen randomly, but weighted toward weaknesses. If your Fork rating is 1200 and your Pin rating is 1800, you're much more likely to get a Fork puzzle.

### 3. Rating Matching

Within the chosen category, puzzles are selected to match your skill:

- **Primary range**: Your rating -100 to +200
- **Expanded range**: Your rating -200 to +300 (if no puzzles in primary)
- **Fallback**: Any puzzle in the category

Puzzles closer to your rating are preferred, with a secondary weight for popularity.

## Viewing Your Progress

### Stats Page

The `/stats` page shows:
- Your overall rating
- Rating for each of the 10 categories
- Categories sorted by rating (weakest first)

### After Each Puzzle

When you solve or fail a puzzle, you'll see:
- Which categories were affected
- Old rating → New rating
- The change amount (+/- points)
- Your updated overall rating

## Resetting Ratings

If you want to start fresh:

1. Go to the Stats page
2. Click "Reset Ratings"
3. Confirm the action

This resets all 10 categories to 1600 and clears your attempt history for rating purposes.

## Tips for Improvement

1. **Focus on weaknesses**: The adaptive system will naturally guide you
2. **Don't fear failure**: Losing to hard puzzles teaches you more
3. **Be consistent**: Regular practice helps ratings stabilize
4. **Review mistakes**: Understand why you failed before moving on
5. **Trust the system**: Ratings take time to reflect your true level

## Technical Details

### Rating Updates Per Puzzle

A single puzzle can affect **multiple categories**. For example, a puzzle tagged with both "fork" and "mate" will update both ratings.

### Concurrent Category Progress

Since each category has its own K-factor and attempt count, you can be:
- Established (K=25) in Fork after 50+ attempts
- Learning (K=150) in Endgame with only 4 attempts

### Database Storage

Ratings are stored in the `user_category_ratings` table:

```sql
{
  user_id: "uuid",
  category: "fork",
  rating: 1650,
  attempts: 23,
  updated_at: "2024-01-15T10:30:00Z"
}
```

