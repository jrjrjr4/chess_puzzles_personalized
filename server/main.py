# server/main.py
from flask import Flask, render_template, request
from puzzle_manager import load_puzzles, get_random_puzzle

app = Flask(__name__)
puzzles = load_puzzles()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/puzzle/random/view')
def random_puzzle_view():
    """Route to display a random puzzle in HTML form."""
    theme = request.args.get('theme')  # optional query param
    puzzle = get_random_puzzle(puzzles, theme_filter=theme)
    return render_template('puzzle.html', puzzle=puzzle)

if __name__ == '__main__':
    app.run(debug=True)
