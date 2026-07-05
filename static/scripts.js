// static/scripts.js

$(document).ready(function () {
    console.log("Scripts loaded.");

    var $puzzleData = $('#puzzle-data');
    if ($puzzleData.length > 0) {
        if (typeof Chessboard === 'function' && typeof Chess === 'function') {
            initPuzzle($puzzleData);
        } else {
            console.error("Chessboard.js or Chess.js is not loaded!");
            $('#status-message').text("Error loading chess board. Please refresh.").css('color', 'red');
        }
    }
});

function initPuzzle($data) {
    var fen = $data.data('fen');
    var movesStr = $data.data('moves');
    
    // Handle case where moves might be empty or malformed
    if (!movesStr || typeof movesStr !== 'string') {
        $('#status-message').text("Error: Invalid puzzle data").css('color', 'red');
        return;
    }
    
    var movesList = movesStr.trim().split(' ').filter(function(m) { return m.length > 0; });

    console.log("Initializing puzzle with FEN:", fen);
    console.log("Solution moves:", movesList);

    if (movesList.length === 0) {
        $('#status-message').text("Error: No moves in puzzle").css('color', 'red');
        return;
    }

    var game = new Chess(fen);
    
    if (!game) {
        $('#status-message').text("Error: Invalid FEN position").css('color', 'red');
        return;
    }
    
    // Determine player color (opposite of who moves first in the FEN)
    // The first move is the opponent's move, so player is the opposite color
    var playerColor = game.turn() === 'w' ? 'black' : 'white';
    console.log("Player color:", playerColor);

    var board = Chessboard('myBoard', {
        position: fen,
        orientation: playerColor,
        draggable: true,
        pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
        onDragStart: onDragStart,
        onDrop: onDrop,
        onSnapEnd: onSnapEnd
    });

    var currentMoveIndex = 0;
    var puzzleComplete = false;
    var attemptRecorded = false;
    
    $('#status-message').text("Watch the opponent's move...");
    
    // Play opponent's first move after a short delay
    setTimeout(function() {
        makeOpponentMove();
    }, 800);

    function onDragStart(source, piece, position, orientation) {
        // Don't allow moves if puzzle is complete or game is over
        if (puzzleComplete) return false;
        if (game.game_over()) return false;

        // Only allow moving player's pieces
        if (playerColor === 'white' && piece.search(/^b/) !== -1) return false;
        if (playerColor === 'black' && piece.search(/^w/) !== -1) return false;
        
        // Only allow moves on player's turn
        if ((playerColor === 'white' && game.turn() !== 'w') ||
            (playerColor === 'black' && game.turn() !== 'b')) {
            return false;
        }
    }

    function onDrop(source, target) {
        // Try the move (always try queen promotion first for simplicity)
        var move = game.move({
            from: source,
            to: target,
            promotion: 'q'
        });

        // If illegal, snap back
        if (move === null) return 'snapback';

        // Build the move string to compare with expected
        var expectedMove = movesList[currentMoveIndex];
        var userMoveString = source + target;
        
        // Add promotion suffix if this was a promotion
        if (move.flags.includes('p')) {
            userMoveString += move.promotion;
        }

        // Check if move matches expected (handle with/without promotion suffix)
        var isCorrect = (userMoveString === expectedMove) || 
                        (userMoveString === expectedMove.substring(0, 4)) ||
                        (source + target === expectedMove.substring(0, 4));

        if (isCorrect) {
            currentMoveIndex++;
            
            if (currentMoveIndex >= movesList.length) {
                // Puzzle solved!
                $('#status-message').text("🎉 Puzzle Solved!")
                    .removeClass('status-error').addClass('status-success');
                puzzleComplete = true;
                if (!attemptRecorded) {
                    recordAttempt(true);
                    attemptRecorded = true;
                }
            } else {
                // More moves to go
                $('#status-message').text("Correct! Keep going...")
                    .removeClass('status-error').addClass('status-success');
                setTimeout(makeOpponentMove, 500);
            }
        } else {
            // Wrong move
            $('#status-message').text("Incorrect move. Try again.")
                .removeClass('status-success').addClass('status-error');
            game.undo();
            if (!attemptRecorded) {
                recordAttempt(false);
                attemptRecorded = true;
            }
            return 'snapback';
        }
    }

    function recordAttempt(success) {
        var puzzleId = $data.data('id');
        
        if (!puzzleId) {
            console.error("No puzzle ID found");
            return;
        }

        fetch('/api/puzzle/attempt', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                puzzle_id: String(puzzleId),
                success: success
            }),
        })
        .then(function(response) {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(function(data) {
            console.log("Attempt recorded:", data);
            if (data.rating_changes && data.rating_changes.length > 0) {
                updateRatingsDisplay(data.rating_changes, data.overall_rating, success);
            }
        })
        .catch(function(error) {
            console.error("Error recording attempt:", error);
        });
    }

    function updateRatingsDisplay(changes, overallRating, success) {
        // Update overall rating
        var $overallEl = $('#overall-rating-value');
        if ($overallEl.length) {
            $overallEl.text(overallRating);
        }
        
        // Update each changed category
        changes.forEach(function(change) {
            // Find the rating element by category name (replace spaces with dashes)
            var categoryId = 'rating-' + change.category.replace(/ /g, '-');
            var $ratingEl = $('#' + categoryId);
            var $itemEl = $ratingEl.closest('.rating-item');
            
            if ($ratingEl.length) {
                // Update the value
                $ratingEl.text(change.new_rating);
                
                // Add color class based on change direction
                if (change.change > 0) {
                    $ratingEl.removeClass('rating-down').addClass('rating-up');
                } else if (change.change < 0) {
                    $ratingEl.removeClass('rating-up').addClass('rating-down');
                }
                
                // Add pulse animation
                $itemEl.addClass('updated');
                setTimeout(function() {
                    $itemEl.removeClass('updated');
                }, 500);
            }
        });
    }

    function onSnapEnd() {
        board.position(game.fen());
    }

    function makeOpponentMove() {
        if (currentMoveIndex >= movesList.length) {
            return;
        }
        
        var moveStr = movesList[currentMoveIndex];
        
        if (!moveStr || moveStr.length < 4) {
            console.error("Invalid move string:", moveStr);
            return;
        }
        
        var from = moveStr.substring(0, 2);
        var to = moveStr.substring(2, 4);
        var promotion = moveStr.length > 4 ? moveStr.substring(4, 5) : undefined;

        var moveObj = { from: from, to: to };
        if (promotion) {
            moveObj.promotion = promotion;
        }
        
        var result = game.move(moveObj);
        
        if (!result) {
            console.error("Failed to make opponent move:", moveStr);
            return;
        }
        
        board.position(game.fen());
        currentMoveIndex++;

        if (currentMoveIndex >= movesList.length) {
            $('#status-message').text("🎉 Puzzle Solved!")
                .removeClass('status-error').addClass('status-success');
            puzzleComplete = true;
        } else {
            $('#status-message').text("Your turn...")
                .removeClass('status-success status-error');
        }
    }

    // Show Solution button
    $('#show-solution-btn').on('click', function () {
        if (currentMoveIndex < movesList.length && !puzzleComplete) {
            var moveStr = movesList[currentMoveIndex];
            var from = moveStr.substring(0, 2);
            var to = moveStr.substring(2, 4);
            var promotion = moveStr.length > 4 ? moveStr.substring(4, 5) : undefined;

            var moveObj = { from: from, to: to };
            if (promotion) {
                moveObj.promotion = promotion;
            }
            
            game.move(moveObj);
            board.position(game.fen());
            currentMoveIndex++;

            if (currentMoveIndex < movesList.length) {
                // Play opponent's response
                setTimeout(makeOpponentMove, 500);
            } else {
                $('#status-message').text("Solution shown")
                    .removeClass('status-error status-success');
                puzzleComplete = true;
            }
        }
    });

    // Handle window resize
    $(window).resize(function () {
        board.resize();
    });
}
