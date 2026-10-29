# Contribution Snake preview

The SVGs are generated from the public contribution calendar for `zecloud`.
Only dates and GitHub's 0–4 intensity levels are stored; no token, private
repository names, or authenticated API response is needed.

From the repository root, refresh and check:

```sh
python scripts/update-snake.py
python -m unittest discover -s tests
git diff --stat
```

Commit refreshed assets through a reviewed branch/PR. The generator fails on
network errors, stale or incomplete responses, duplicate/nonconsecutive dates,
or invalid levels, rather than inventing contribution data. Render the existing
snapshot offline with `python scripts/update-snake.py --from-snapshot`.

The last 364 days are aligned to Sunday-first weeks. The blue snake follows
a deterministic, collision-free alternating vertical scan. It dims each visited
contribution, then the animation resets. The grid preserves actual dates and
intensities; the route is decorative, not a record of gameplay or commit counts.
The SVG title/description and each day's tooltip describe the snapshot.
Reduced-motion viewers get a static SVG via the profile's `picture` element;
the animated SVG also disables its CSS animations under reduced motion.
A static-view link is always available.

CI checks the snapshot and generator and ensures checked-in SVGs can be
reproduced offline. It has read-only permissions and does not commit, deploy,
or automatically merge anything.

The interactive game belongs to `zecloud/zecloud.github.io` at `/play/`.
Its README link must stay marked as pending until that page is verified deployed.
