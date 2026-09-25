// Plays REAL multiplayer E91 games against a running backend, sending exactly
// the messages the browsers send (a teacher and two students: create the game,
// JOIN, START, A_MEASURE / B_MEASURE), then checks the physics over all of
// them: identical keys without Eve, the four Bell terms and S, both sides
// ~50 % ones — half the games with Alice clicking first, half with Bob.
//
// Why pool many games: a real game is capped at 30 photons, far too few to
// judge S. 400 games give ~650 rounds per Bell term, σ(S) ≈ 0.04.
//
// Run from anywhere, with the backend and Redis up (README "Running Locally"),
// Node 22+ (built-in WebSocket):
//     node tools/e91_fake_browsers.mjs <games> <eve: 0|1>
//     node tools/e91_fake_browsers.mjs 400 0
//     node tools/e91_fake_browsers.mjs 400 1 lie   # browsers misreport Eve: the server must not care
//
// Every game it creates is DELETED afterwards. It refuses any server other than
// localhost unless E91_TOOL_HOST is set — it writes to the database it targets.
const HOST = process.env.E91_TOOL_HOST ?? '127.0.0.1:8000';
if (!process.env.E91_TOOL_HOST && !/^(127\.0\.0\.1|localhost)(:\d+)?$/.test(HOST)) {
    throw new Error('refusing a non-local host');
}
const API = `http://${HOST}`;
const WS = `ws://${HOST}/ws`;
const PHOTONS = 30;
const ANGLE = {'1': 0, '2': 45, '3': 90, '4': 135};

const open = (url) => new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    const inbox = [];
    const waiters = [];
    ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        const p = data.payload ?? data;
        const i = waiters.findIndex(w => w.match(p));
        if (i >= 0) waiters.splice(i, 1)[0].resolve(p); else inbox.push(p);
    };
    ws.wait = (match, ms = 5000) => new Promise((res, rej) => {
        const i = inbox.findIndex(match);
        if (i >= 0) return res(inbox.splice(i, 1)[0]);
        const t = setTimeout(() => rej(new Error('timeout waiting on ' + url)), ms);
        waiters.push({match, resolve: (p) => { clearTimeout(t); res(p); }});
    });
    ws.sendEvent = (event, message) => ws.send(JSON.stringify({event, message}));
    ws.onopen = () => resolve(ws);
    ws.onerror = () => reject(new Error('cannot open ' + url));
});

const bases = (ids) => Array.from({length: PHOTONS}, () => ids[Math.floor(Math.random() * ids.length)]);

async function playOne(withEve, aliceFirst, tag) {
    const res = await fetch(`${API}/games/e91/`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({photon_number: PHOTONS, eve: withEve, eve_percentage: 1.0}),
    });
    const game = await res.json();
    if (!game.code) throw new Error('create failed: ' + JSON.stringify(game));
    try {
        const teacher = await open(`${WS}/games/e91/${game.code}/?player_name=teacher&admin=1`);
        const names = [`a${tag}`, `b${tag}`];
        const students = [];
        for (const name of names) {
            const s = await open(`${WS}/games/e91/${game.code}/?player_name=${name}`);
            s.sendEvent('JOIN', {game_code: game.code, player_name: name});
            students.push(s);
        }
        await new Promise(r => setTimeout(r, 150));  // let both registrations land
        teacher.sendEvent('START', {game_code: game.code, game_id: game.id});
        const roles = (await students[0].wait(p => p.event === 'ROLES')).message;

        const seat = {};
        for (const [id, info] of Object.entries(roles)) {
            if (typeof info === 'object' && info.role) seat[info.role] = {id, ...info};
        }
        const nameOf = {A: seat.B.partner, B: seat.A.partner};
        const room = seat.A.room;
        const play = {A: await open(`${WS}/games/e91/${game.code}/rooms/${room}/`),
                      B: await open(`${WS}/games/e91/${game.code}/rooms/${room}/`)};

        const chosen = {A: bases(['1', '2', '3']), B: bases(['2', '3', '4'])};
        const bits = {};
        for (const role of aliceFirst ? ['A', 'B'] : ['B', 'A']) {
            play[role].sendEvent(`${role}_MEASURE`, {
                bases: chosen[role], eve_present: browsersLie ? !seat.A.eve_present : seat.A.eve_present,
                player_name: nameOf[role],
            });
            bits[role] = (await play[role].wait(p => p.event === `${role}_MEASURE`)).message.bits;
        }
        for (const s of [teacher, ...students, play.A, play.B]) s.close();
        return {chosen, bits, evePresent: seat.A.eve_present};
    } finally {
        await fetch(`${API}/games/e91/${game.id}/`, {method: 'DELETE'});  // leave the DB clean
    }
}

const games = Number(process.argv[2] ?? 20);
const withEve = process.argv[3] === '1';
// Optional 3rd argument "lie": the browsers send the OPPOSITE eve_present to the one
// the server told them. The server must ignore it and trust its own round.
const browsersLie = process.argv[4] === 'lie';
const rows = {true: [], false: []};   // aliceFirst → rounds
let keyBits = 0, keyErrors = 0, gamesWithIdenticalKeys = 0, ones = {A: 0, B: 0}, total = 0;

for (let g = 0; g < games; g++) {
    const aliceFirst = g % 2 === 0;
    const r = await playOne(withEve, aliceFirst, `${Date.now() % 100000}${g}`);
    let errs = 0;
    for (let i = 0; i < PHOTONS; i++) {
        const a = r.chosen.A[i], b = r.chosen.B[i], x = r.bits.A[i], y = r.bits.B[i];
        rows[aliceFirst].push([ANGLE[a], ANGLE[b], x, y]);
        if (a === b) { keyBits++; if (x !== y) { keyErrors++; errs++; } }
        ones.A += x === '1'; ones.B += y === '1'; total++;
    }
    if (errs === 0) gamesWithIdenticalKeys++;
}

const S = (rounds) => {
    const E = (a, b) => {
        const rs = rounds.filter(([x, y]) => x === a && y === b);
        return rs.length ? rs.reduce((s, [, , p, q]) => s + (p === q ? 1 : -1), 0) / rs.length : 0;
    };
    return Math.abs(E(0, 45) - E(0, 135) + E(90, 45) + E(90, 135));
};
const terms = (rounds) => Object.fromEntries([[0,45],[0,135],[90,45],[90,135]].map(([a,b]) => { const rs = rounds.filter(([x,y]) => x===a && y===b); return [`E(${a},${b})`, `${(rs.reduce((s,[,,p,q]) => s + (p===q?1:-1), 0)/rs.length).toFixed(3)} (n=${rs.length})`]; }));
console.log(JSON.stringify({ terms_aliceFirst: terms(rows.true), terms_bobFirst: terms(rows.false),
    games, eve: withEve, photonsPerGame: PHOTONS,
    S_aliceFirst: S(rows.true).toFixed(3), S_bobFirst: S(rows.false).toFixed(3),
    keyBits, keyErrors, keyErrorRate: (keyErrors / keyBits).toFixed(3),
    gamesWithIdenticalKeys: `${gamesWithIdenticalKeys}/${games}`,
    aliceOnes: (ones.A / total).toFixed(3), bobOnes: (ones.B / total).toFixed(3),
}, null, 1));
process.exit(0);
