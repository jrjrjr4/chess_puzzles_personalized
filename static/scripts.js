// static/scripts.js

$(document).ready(function () {
    var $puzzleData = $('#puzzle-data');
    if ($puzzleData.length > 0) {
        if (typeof Chessboard === 'function' && typeof Chess === 'function') {
            initPuzzle($puzzleData);
        } else {
            $('#status-message').text('Error loading chess board. Please refresh.').css('color', 'red');
        }
    }
});

function initPuzzle($data) {
    var fen = $data.data('fen');
    var movesStr = $data.data('moves');

    if (!movesStr || typeof movesStr !== 'string') {
        $('#status-message').text('Error: Invalid puzzle data').css('color', 'red');
        return;
    }

    var movesList = movesStr.trim().split(' ').filter(function (move) {
        return move.length > 0;
    });

    if (movesList.length === 0) {
        $('#status-message').text('Error: No moves in puzzle').css('color', 'red');
        return;
    }

    var game = new Chess(fen);
    if (!game) {
        $('#status-message').text('Error: Invalid FEN position').css('color', 'red');
        return;
    }

    var playerColor = game.turn() === 'w' ? 'black' : 'white';
    var currentMoveIndex = 0;
    var puzzleComplete = false;
    var attemptRecorded = false;
    var selectedSquare = null;
    var legalTargets = [];

    var board = Chessboard('myBoard', {
        position: fen,
        orientation: playerColor,
        draggable: true,
        pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
        onDragStart: onDragStart,
        onDrop: onDrop,
        onSnapEnd: onSnapEnd
    });

    $('#status-message').text("Watch the opponent's move...");

    setTimeout(function () {
        makeOpponentMove();
    }, 800);

    $('#myBoard').on('click', '.square-55d63', onBoardSquareClick);

    $('#show-solution-btn').on('click', function () {
        if (currentMoveIndex >= movesList.length || puzzleComplete) return;

        clearHighlights();
        var moveStr = movesList[currentMoveIndex];
        var moveObj = buildMoveObject(moveStr);

        game.move(moveObj);
        board.position(game.fen());
        markLastMove(moveObj.from, moveObj.to);
        currentMoveIndex++;

        if (currentMoveIndex < movesList.length) {
            setTimeout(makeOpponentMove, 500);
        } else {
            $('#status-message').text('Solution shown')
                .removeClass('status-error status-success');
            puzzleComplete = true;
        }
    });

    $(window).resize(function () {
        board.resize();
        if (selectedSquare) {
            selectSquare(selectedSquare);
        }
    });

    function onDragStart(source, piece) {
        clearHighlights();

        if (puzzleComplete || game.game_over() || !isPlayersTurn()) return false;
        if (playerColor === 'white' && piece.search(/^b/) !== -1) return false;
        if (playerColor === 'black' && piece.search(/^w/) !== -1) return false;
    }

    function onDrop(source, target) {
        return handlePlayerMove(source, target, true);
    }

    function onSnapEnd() {
        board.position(game.fen());
    }

    function onBoardSquareClick() {
        var square = getSquareFromElement(this);
        if (!square) return;

        if (selectedSquare && legalTargets.indexOf(square) !== -1) {
            handlePlayerMove(selectedSquare, square, false);
            return;
        }

        if (selectedSquare === square) {
            clearHighlights();
            return;
        }

        if (isOwnPiece(square)) {
            selectSquare(square);
            return;
        }

        clearHighlights();
    }

    function handlePlayerMove(source, target, snapBackOnWrong) {
        clearHighlights();

        var move = game.move({
            from: source,
            to: target,
            promotion: 'q'
        });

        if (move === null) return 'snapback';

        var expectedMove = movesList[currentMoveIndex];
        var userMoveString = source + target;

        if (move.flags.includes('p')) {
            userMoveString += move.promotion;
        }

        var isCorrect = (userMoveString === expectedMove) ||
            (userMoveString === expectedMove.substring(0, 4)) ||
            (source + target === expectedMove.substring(0, 4));

        if (isCorrect) {
            currentMoveIndex++;
            board.position(game.fen());
            markLastMove(source, target);

            if (currentMoveIndex >= movesList.length) {
                $('#status-message').text('Puzzle solved')
                    .removeClass('status-error').addClass('status-success');
                puzzleComplete = true;
                if (!attemptRecorded) {
                    recordAttempt(true);
                    attemptRecorded = true;
                }
            } else {
                $('#status-message').text('Correct. Keep going...')
                    .removeClass('status-error').addClass('status-success');
                setTimeout(makeOpponentMove, 500);
            }
            return;
        }

        $('#status-message').text('Incorrect move. Try again.')
            .removeClass('status-success').addClass('status-error');
        game.undo();
        board.position(game.fen());

        if (!attemptRecorded) {
            recordAttempt(false);
            attemptRecorded = true;
        }

        return snapBackOnWrong ? 'snapback' : undefined;
    }

    function makeOpponentMove() {
        if (currentMoveIndex >= movesList.length) return;

        var moveStr = movesList[currentMoveIndex];
        if (!moveStr || moveStr.length < 4) return;

        var moveObj = buildMoveObject(moveStr);
        var result = game.move(moveObj);
        if (!result) return;

        clearHighlights();
        board.position(game.fen());
        markLastMove(moveObj.from, moveObj.to);
        currentMoveIndex++;

        if (currentMoveIndex >= movesList.length) {
            $('#status-message').text('Puzzle solved')
                .removeClass('status-error').addClass('status-success');
            puzzleComplete = true;
        } else {
            $('#status-message').text('Your turn. Select a piece or drag it.')
                .removeClass('status-success status-error');
        }
    }

    function buildMoveObject(moveStr) {
        var moveObj = {
            from: moveStr.substring(0, 2),
            to: moveStr.substring(2, 4)
        };

        if (moveStr.length > 4) {
            moveObj.promotion = moveStr.substring(4, 5);
        }

        return moveObj;
    }

    function selectSquare(square) {
        if (puzzleComplete || game.game_over() || !isPlayersTurn() || !isOwnPiece(square)) {
            clearHighlights();
            return;
        }

        var moves = game.moves({ square: square, verbose: true });
        if (!moves.length) {
            clearHighlights();
            return;
        }

        selectedSquare = square;
        legalTargets = moves.map(function (move) {
            return move.to;
        });

        clearHighlights(false);
        highlightSquare(square, 'square-selected');
        moves.forEach(function (move) {
            highlightSquare(move.to, move.captured ? 'square-capture' : 'square-legal');
        });
    }

    function isPlayersTurn() {
        return (playerColor === 'white' && game.turn() === 'w') ||
            (playerColor === 'black' && game.turn() === 'b');
    }

    function isOwnPiece(square) {
        var piece = game.get(square);
        if (!piece) return false;
        return (playerColor === 'white' && piece.color === 'w') ||
            (playerColor === 'black' && piece.color === 'b');
    }

    function getSquareFromElement(el) {
        var classes = el.className.split(/\s+/);
        for (var i = 0; i < classes.length; i++) {
            if (/^square-[a-h][1-8]$/.test(classes[i])) {
                return classes[i].replace('square-', '');
            }
        }
        return null;
    }

    function highlightSquare(square, className) {
        $('#myBoard .square-' + square).addClass(className);
    }

    function markLastMove(from, to) {
        window.requestAnimationFrame(function () {
            $('#myBoard .square-55d63').removeClass('square-last-move');
            highlightSquare(from, 'square-last-move');
            highlightSquare(to, 'square-last-move');
        });
    }

    function clearHighlights(keepSelectionState) {
        $('#myBoard .square-55d63').removeClass('square-selected square-legal square-capture');
        if (keepSelectionState !== false) {
            selectedSquare = null;
            legalTargets = [];
        }
    }

    function recordAttempt(success) {
        var puzzleId = $data.data('id');
        if (!puzzleId) return;

        fetch('/api/puzzle/attempt', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                puzzle_id: String(puzzleId),
                success: success
            })
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(function (data) {
                if (data.rating_changes && data.rating_changes.length > 0) {
                    updateRatingsDisplay(data.rating_changes, data.overall_rating);
                }
            })
            .catch(function (error) {
                console.error('Error recording attempt:', error);
            });
    }

    function updateRatingsDisplay(changes, overallRating) {
        var $overallEl = $('#overall-rating-value');
        if ($overallEl.length) {
            $overallEl.text(overallRating);
        }

        changes.forEach(function (change) {
            var categoryId = 'rating-' + change.category.replace(/ /g, '-');
            var $ratingEl = $('#' + categoryId);
            var $itemEl = $ratingEl.closest('.rating-item');

            if (!$ratingEl.length) return;

            $ratingEl.text(change.new_rating);
            if (change.change > 0) {
                $ratingEl.removeClass('rating-down').addClass('rating-up');
            } else if (change.change < 0) {
                $ratingEl.removeClass('rating-up').addClass('rating-down');
            }

            $itemEl.addClass('updated');
            setTimeout(function () {
                $itemEl.removeClass('updated');
            }, 500);
        });
    }
}
