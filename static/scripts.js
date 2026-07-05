// static/scripts.js

$(document).ready(function () {
    console.log("Scripts loaded.");

    initThemeToggle();
    initSoundToggle();

    var $puzzleData = $('#puzzle-data');
    if ($puzzleData.length > 0) {
        if (typeof Chessground === 'function' && typeof Chess === 'function') {
            initPuzzle($puzzleData);
        } else {
            console.error("Chessground or Chess.js is not loaded!");
            $('#status-message').text("Error loading chess board. Please refresh.").css('color', 'red');
        }
    }
});

function initThemeToggle() {
    var $btn = $('#theme-toggle');
    if (!$btn.length) return;

    function isDark() {
        return document.documentElement.getAttribute('data-theme') === 'dark';
    }

    function renderIcon() {
        $btn.find('i').attr('class', isDark() ? 'fas fa-sun' : 'fas fa-moon');
    }

    $btn.on('click', function () {
        var dark = isDark();
        if (dark) {
            document.documentElement.removeAttribute('data-theme');
        } else {
            document.documentElement.setAttribute('data-theme', 'dark');
        }
        try {
            localStorage.setItem('theme', dark ? 'light' : 'dark');
        } catch (e) {}
        renderIcon();
    });

    renderIcon();
}

// --- Sound effects: short synthesized tones, no audio files ---
var audioCtx = null;

function soundEnabled() {
    try {
        return localStorage.getItem('sound') !== 'off';
    } catch (e) {
        return true;
    }
}

function getAudioCtx() {
    var Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    if (!audioCtx) audioCtx = new Ctx();
    // Browsers keep the context suspended until a user gesture; every play
    // call here happens in response to a click/drag, so resume works
    if (audioCtx.state === 'suspended') audioCtx.resume();
    return audioCtx;
}

function playNotes(notes) {
    if (!soundEnabled()) return;
    var ctx = getAudioCtx();
    if (!ctx) return;
    var now = ctx.currentTime;
    notes.forEach(function (n) {
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.type = n.type || 'sine';
        osc.frequency.value = n.freq;
        var t0 = now + (n.at || 0);
        gain.gain.setValueAtTime(0.0001, t0);
        gain.gain.exponentialRampToValueAtTime(n.gain || 0.1, t0 + 0.012);
        gain.gain.exponentialRampToValueAtTime(0.0001, t0 + n.dur);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t0);
        osc.stop(t0 + n.dur + 0.05);
    });
}

// Soft marimba-ish blip for a correct move
function playCorrectSound() {
    playNotes([
        { freq: 660, dur: 0.12, gain: 0.10 },
        { freq: 1320, dur: 0.08, gain: 0.03 }
    ]);
}

// Gentle rising chime when the puzzle is solved
function playSolveSound() {
    playNotes([
        { freq: 523.25, at: 0.00, dur: 0.18, gain: 0.09 },
        { freq: 659.25, at: 0.09, dur: 0.18, gain: 0.09 },
        { freq: 783.99, at: 0.18, dur: 0.30, gain: 0.10 }
    ]);
}

// Quiet low thud for a wrong move
function playWrongSound() {
    playNotes([{ freq: 196, dur: 0.18, gain: 0.06, type: 'triangle' }]);
}

function initSoundToggle() {
    var $btn = $('#sound-toggle');
    if (!$btn.length) return;

    function renderIcon() {
        $btn.find('i').attr('class', soundEnabled() ? 'fas fa-volume-up' : 'fas fa-volume-mute');
    }

    $btn.on('click', function () {
        try {
            localStorage.setItem('sound', soundEnabled() ? 'off' : 'on');
        } catch (e) {}
        renderIcon();
        if (soundEnabled()) playCorrectSound(); // audible preview
    });

    renderIcon();
}

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
    var playerColorLetter = playerColor === 'white' ? 'w' : 'b';
    console.log("Player color:", playerColor);

    var currentMoveIndex = 0;
    var puzzleComplete = false;
    var attemptRecorded = false;
    var lastMove = null; // [from, to] of the last accepted move

    function isPlayersTurn() {
        return !puzzleComplete && !game.game_over() && game.turn() === playerColorLetter;
    }

    function cgColor() {
        return game.turn() === 'w' ? 'white' : 'black';
    }

    function computeDests() {
        var dests = new Map();
        game.SQUARES.forEach(function (s) {
            var ms = game.moves({ square: s, verbose: true });
            if (ms.length) {
                dests.set(s, ms.map(function (m) { return m.to; }));
            }
        });
        return dests;
    }

    var cg = Chessground(document.getElementById('board'), {
        fen: fen,
        orientation: playerColor,
        turnColor: cgColor(),
        coordinates: true,
        animation: { enabled: true, duration: 200 },
        highlight: { lastMove: true, check: true },
        premovable: { enabled: false },
        draggable: { enabled: true, showGhost: true },
        selectable: { enabled: true },
        movable: {
            free: false,
            color: playerColor,
            dests: new Map(), // locked until the opponent's first move plays
            showDests: true,
            events: { after: onUserMove }
        }
    });

    // chess.js is the source of truth; this pushes it to the board.
    // cg.set() animates fen diffs, so it also handles opponent replies and
    // wrong-move rollbacks.
    function syncBoard() {
        cg.set({
            fen: game.fen(),
            turnColor: cgColor(),
            check: game.in_check(),
            lastMove: lastMove || undefined,
            movable: {
                color: playerColor,
                dests: isPlayersTurn() ? computeDests() : new Map()
            }
        });
    }

    $('#status-message').text("Watch the opponent's move...");

    // Play opponent's first move after a short delay
    setTimeout(function() {
        makeOpponentMove();
    }, 800);

    // Shared move validator: applies the move to chess.js, compares against
    // the solution, updates status and records the attempt.
    // Returns 'illegal', 'wrong' or 'correct'.
    function handlePlayerMove(source, target) {
        // Try the move (always try queen promotion first for simplicity)
        var move = game.move({
            from: source,
            to: target,
            promotion: 'q'
        });

        if (move === null) return 'illegal';

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
                playSolveSound();
                if (!attemptRecorded) {
                    recordAttempt(true);
                    attemptRecorded = true;
                }
            } else {
                // More moves to go
                $('#status-message').text("Correct! Keep going...")
                    .removeClass('status-error').addClass('status-success');
                playCorrectSound();
                setTimeout(makeOpponentMove, 500);
            }
            return 'correct';
        }

        // Wrong move
        $('#status-message').text("Incorrect move. Try again.")
            .removeClass('status-success').addClass('status-error');
        playWrongSound();
        game.undo();
        if (!attemptRecorded) {
            recordAttempt(false);
            attemptRecorded = true;
        }
        return 'wrong';
    }

    // Called by chessground after the user makes a board-legal move
    // (click-to-move or drag — dests guarantee legality).
    // Briefly flash squares green via chessground's custom highlight classes
    function flashSquares(keys) {
        var custom = new Map();
        keys.forEach(function (k) { custom.set(k, 'flash-correct'); });
        cg.set({ highlight: { custom: custom } });
        setTimeout(function () {
            cg.set({ highlight: { custom: new Map() } });
        }, 650);
    }

    function onUserMove(orig, dest) {
        var result = handlePlayerMove(orig, dest);
        if (result === 'correct') {
            lastMove = [orig, dest];
            syncBoard(); // renders promotion, check ring; locks dests until reply
            flashSquares([orig, dest]);
            if (puzzleComplete) cg.stop();
        } else {
            // Wrong or illegal: chess.js was undone (or never changed), so this
            // animates the piece back and restores the previous highlights.
            syncBoard();
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

    // Ease a displayed number from its current value to `to`
    function animateNumber($el, to, ms) {
        var from = parseInt($el.text(), 10);
        if (isNaN(from) || from === to) {
            $el.text(to);
            return;
        }
        var start = performance.now();
        function frame(now) {
            var p = Math.min((now - start) / (ms || 500), 1);
            var eased = 1 - Math.pow(1 - p, 3);
            $el.text(Math.round(from + (to - from) * eased));
            if (p < 1) requestAnimationFrame(frame);
        }
        requestAnimationFrame(frame);
    }

    // Float a "+12" / "-8" chip up out of the container
    function spawnDelta($container, change, isSpillover) {
        if (!change) return;
        var $chip = $('<span class="delta-chip">')
            .addClass(change > 0 ? 'delta-up' : 'delta-down')
            .text((change > 0 ? '+' : '') + change);
        if (isSpillover) $chip.addClass('delta-spill');
        $container.append($chip);
        setTimeout(function () { $chip.remove(); }, 1200);
    }

    function updateRatingsDisplay(changes, overallRating, success) {
        // Update overall rating
        var $overallEl = $('#overall-rating-value');
        if ($overallEl.length) {
            var oldOverall = parseInt($overallEl.text(), 10);
            animateNumber($overallEl, overallRating);
            if (!isNaN(oldOverall)) {
                spawnDelta($overallEl.parent(), overallRating - oldOverall);
            }
        }

        // Update each changed category
        changes.forEach(function(change) {
            // Find the rating element by category name (replace spaces with dashes)
            var categoryId = 'rating-' + change.category.replace(/ /g, '-');
            var $ratingEl = $('#' + categoryId);
            var $itemEl = $ratingEl.closest('.rating-item');

            if ($ratingEl.length) {
                animateNumber($ratingEl, change.new_rating);
                spawnDelta($itemEl, change.change, change.spillover);

                // Spillover drift stays visually quiet: no color change, no pulse
                if (change.spillover) return;

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

        lastMove = [from, to];
        currentMoveIndex++;
        syncBoard();

        if (currentMoveIndex >= movesList.length) {
            $('#status-message').text("🎉 Puzzle Solved!")
                .removeClass('status-error').addClass('status-success');
            puzzleComplete = true;
            cg.stop();
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
            lastMove = [from, to];
            currentMoveIndex++;
            syncBoard();

            if (currentMoveIndex < movesList.length) {
                // Play opponent's response
                setTimeout(makeOpponentMove, 500);
            } else {
                $('#status-message').text("Solution shown")
                    .removeClass('status-error status-success');
                puzzleComplete = true;
                cg.stop();
            }
        }
    });

    // Handle window resize (keeps drag coordinates in sync)
    $(window).resize(function () {
        cg.redrawAll();
    });
}
