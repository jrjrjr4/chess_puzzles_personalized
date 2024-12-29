from flask import Flask, render_template
from puzzle_manager import load_puzzles

app = Flask(__name__)

# Preload puzzles into memory (for a small CSV it's fine to do this once)
puzzles = load_puzzles()

@app.route('/')
def index():
    # For a simple homepage, just show a message
    return render_template('index.html')

if __name__ == '__main__':
    # Start the Flask development server
    app.run(debug=True)
