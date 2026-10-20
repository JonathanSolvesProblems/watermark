# Repositories: what goes where, and why

Two public repos. The decision and the mechanics, so neither is improvised on submission day.

## 1. `watermark` (main track submission)

**Public, MIT, licence file at the root so GitHub shows it in the About box.**

The rules allow a private repo shared with six named Amazon DevRel accounts instead. I am
not taking that option, for three reasons:

- A private repo depends on six separate invitations being accepted, and GitHub expires
  them after 7 days. That is six silent ways for a judge to be unable to open the thing.
  SWORN was marked SUBMITTED, returned HTTP 200, and still never appeared in the gallery;
  the lesson was that anything between a judge and the artifact is a risk worth removing.
- Every entry of mine that has placed had a public repo.
- The honesty machinery only counts if someone can read it. `check_claims.py`,
  `docs/FRICTION_LOG.md` and `docs/CORRECTIONS.md` are arguments, not hygiene, and they
  are invisible behind an invitation.

Nothing in the repo needs to be secret. Credentials live in `server/.env`, which is
gitignored, and the claim questions are replaced with the insurer's wording without file
numbers, policy numbers, names or the address.

**If I ever do go private**, add the six accounts on submission day and not before, then
screenshot the Collaborators page: chris-trag, knmeiss, giolaq, anishamalde, mosesroth,
emersonsklar.

## 2. `ringwire` (Open Source mini challenge)

**Public, MIT, its own repo.** The mini challenge asks for a *new, additional* open-source
project shipped alongside the primary submission, so it cannot just be a folder inside the
main repo. `sdk/` is that project: `ringwire`, a typed Python client for the Ring
Partner API covering sensors, the two-step media downloads, WHEP sessions, chime playback,
webhook HMAC verification and the account-linking nonce. 22 tests, no network needed.

It now carries its own `LICENSE` and `.gitignore` so it stands alone.

### Splitting it out, with history

Run from the repo root once the GitHub repo exists and is empty:

```sh
git subtree split --prefix=sdk -b sdk-only
git push git@github.com:JonathanSolvesProblems/ringwire.git sdk-only:main
git branch -D sdk-only
```

`sdk/` stays in this repo as well, because the server imports it and the tests run against
it. That is fine and normal: the mini challenge asks for the project to exist and be open
source, not for it to be absent from everywhere else.

Re-run the split after any SDK change to push updates.

### The second half of the mini challenge

A contribution to a public repo during the window: a PR to `AmazonAppDev/ring-api-helloworld`
adding the sensor webhook event types (`flood_*`, `freeze_*`, `contact_sensor_*`, `tamper_*`)
to its normaliser, with tests. The rules say a PR does not need to be merged and a fork is
acceptable, so scope it small and obviously correct rather than architectural.

Required submission fields: contribution URL, repo URL, GitHub username
(`JonathanSolvesProblems`), and a short description of what it does and why it matters.

## Checklist for submission day

- [ ] `watermark` public, LICENSE visible in the About box
- [ ] `ringwire` public, LICENSE visible, tests green from a clean clone
- [ ] PR opened against `ring-api-helloworld`, URL recorded
- [ ] Both repos load in a logged-out browser
- [ ] `server/.env` absent from both (`git log --all --full-history -- server/.env` returns nothing)
