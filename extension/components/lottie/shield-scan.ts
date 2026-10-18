// A small hand-made Lottie animation (no third-party file, so no licence to track):
// a shield with a scan line sweeping down it and a ring turning around it.
const JADE = [0.66, 0.31, 0.36, 1]; // rose (#a8505b)
const ease = { i: { x: [0.4], y: [1] }, o: { x: [0.6], y: [0] } };

const stroke = (width: number) => ({
  ty: 'st',
  c: { a: 0, k: JADE },
  o: { a: 0, k: 100 },
  w: { a: 0, k: width },
  lc: 2,
  lj: 2,
});

const still = (v: unknown) => ({ a: 0, k: v });

export const shieldScan = {
  v: '5.7.0',
  fr: 30,
  ip: 0,
  op: 60,
  w: 100,
  h: 100,
  nm: 'shield-scan',
  ddd: 0,
  assets: [],
  layers: [
    {
      // Ring that keeps turning
      ddd: 0, ind: 1, ty: 4, nm: 'ring', sr: 1, ip: 0, op: 60, st: 0, bm: 0,
      ks: {
        o: still(100),
        r: { a: 1, k: [{ t: 0, s: [0], e: [360], i: { x: [0.5], y: [0.5] }, o: { x: [0.5], y: [0.5] } }, { t: 60, s: [360] }] },
        p: still([50, 50, 0]),
        a: still([0, 0, 0]),
        s: still([100, 100, 100]),
      },
      shapes: [
        {
          ty: 'gr',
          it: [
            { ty: 'el', p: still([0, 0]), s: still([88, 88]) },
            { ty: 'tm', s: still(0), e: still(28), o: still(0), m: 1 },
            stroke(4),
            { ty: 'tr', p: still([0, 0]), a: still([0, 0]), s: still([100, 100]), r: still(0), o: still(100) },
          ],
          nm: 'ring',
        },
      ],
    },
    {
      // Scan line sweeping down and back up
      ddd: 0, ind: 2, ty: 4, nm: 'scan', sr: 1, ip: 0, op: 60, st: 0, bm: 0,
      ks: {
        o: still(100),
        r: still(0),
        p: {
          a: 1,
          k: [
            { t: 0, s: [50, 34, 0], e: [50, 66, 0], ...ease },
            { t: 30, s: [50, 66, 0], e: [50, 34, 0], ...ease },
            { t: 60, s: [50, 34, 0] },
          ],
        },
        a: still([0, 0, 0]),
        s: still([100, 100, 100]),
      },
      shapes: [
        {
          ty: 'gr',
          it: [
            { ty: 'sh', ks: still({ c: false, v: [[-15, 0], [15, 0]], i: [[0, 0], [0, 0]], o: [[0, 0], [0, 0]] }) },
            stroke(3),
            { ty: 'tr', p: still([0, 0]), a: still([0, 0]), s: still([100, 100]), r: still(0), o: still(100) },
          ],
          nm: 'line',
        },
      ],
    },
    {
      // The shield outline
      ddd: 0, ind: 3, ty: 4, nm: 'shield', sr: 1, ip: 0, op: 60, st: 0, bm: 0,
      ks: {
        o: still(100),
        r: still(0),
        p: still([50, 50, 0]),
        a: still([0, 0, 0]),
        s: still([100, 100, 100]),
      },
      shapes: [
        {
          ty: 'gr',
          it: [
            {
              ty: 'sh',
              ks: still({
                c: true,
                v: [[0, -26], [22, -18], [22, 4], [0, 28], [-22, 4], [-22, -18]],
                i: [[0, 0], [0, 0], [0, 0], [11, -5], [0, 9], [0, 0]],
                o: [[0, 0], [0, 0], [0, 9], [-11, -5], [0, 0], [0, 0]],
              }),
            },
            stroke(4),
            { ty: 'tr', p: still([0, 0]), a: still([0, 0]), s: still([100, 100]), r: still(0), o: still(100) },
          ],
          nm: 'outline',
        },
      ],
    },
  ],
};
