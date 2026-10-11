import assert from 'node:assert/strict'
import { execFileSync, spawn, spawnSync } from 'node:child_process'
import {
  chmodSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, realpathSync, rmSync, symlinkSync, utimesSync, writeFileSync,
} from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { after, before, test } from 'node:test'
import { fileURLToPath } from 'node:url'

// Every verdict scripts/prune-worktrees.sh can reach, against a throwaway
// repository and a stub `gh` that reports which branches merged.
const script = fileURLToPath(new URL('../prune-worktrees.sh', import.meta.url))
// Resolved, as git records worktree paths (macOS tmpdir() sits behind /var -> /private/var).
const dir = realpathSync(mkdtempSync(join(tmpdir(), 'prune-worktrees-')))
const root = join(dir, 'root')
const wt = (name) => join(dir, `wt-${name}`)
const runtimeWt = join(root, '.claude', 'worktrees', 'runtime')
const rt = (name) => join(root, '.claude', 'worktrees', name)
const env = {
  ...process.env,
  HOME: dir,
  PATH: `${join(dir, 'bin')}:${process.env.PATH}`,
  STUB_GH_PRS: join(dir, 'merged-prs.txt'),
  GIT_CONFIG_GLOBAL: '/dev/null',
  GIT_CONFIG_NOSYSTEM: '1',
  GIT_AUTHOR_NAME: 'test', GIT_AUTHOR_EMAIL: 'test@example.invalid',
  GIT_COMMITTER_NAME: 'test', GIT_COMMITTER_EMAIL: 'test@example.invalid',
}
const git = (...args) => execFileSync('git', ['-C', root, ...args], { env, encoding: 'utf8' }).trim()
let serial = 0
const commit = (branch) => {
  git('checkout', '-q', branch)
  writeFileSync(join(root, `file-${++serial}`), `${serial}\n`)
  git('add', '.')
  git('commit', '-q', '-m', `commit ${serial}`)
  return git('rev-parse', 'HEAD')
}
// A PR from `branch`, merged with a merge commit; returns the PR's head.
const mergedPr = (branch, commits = 1) => {
  git('checkout', '-q', '-b', branch, 'main')
  let head
  for (let i = 0; i < commits; i++) head = commit(branch)
  git('checkout', '-q', 'main')
  git('merge', '-q', '--no-ff', '-m', `Merge ${branch}`, branch)
  return head
}
const prune = (...flags) => spawnSync('bash', [script, ...flags], { cwd: root, env, encoding: 'utf8' })
const linesFor = (output, subject) => output.split('\n').filter((line) => line.includes(`${subject} `) || line.endsWith(subject))
const verdictOf = (output, subject) => {
  const lines = linesFor(output, subject)
  assert.equal(lines.length, 1, `expected one verdict for ${subject}:\n${output}`)
  return lines[0].replace(/\s+/g, ' ')
}
const worktrees = () => git('worktree', 'list', '--porcelain')
// Backdate a worktree's git state past the one-day idle window.
const idle = (tree) => {
  const admin = execFileSync('git', ['-C', tree, 'rev-parse', '--absolute-git-dir'], { env, encoding: 'utf8' }).trim()
  const then = new Date(Date.now() - 2 * 24 * 3600 * 1000)
  for (const file of ['HEAD', 'index', 'logs/HEAD']) {
    if (existsSync(join(admin, file))) utimesSync(join(admin, file), then, then)
  }
}
const branchExists = (name) => spawnSync('git', ['-C', root, 'rev-parse', '-q', '--verify', `refs/heads/${name}`], { env }).status === 0
let sleeper

before(() => {
  mkdirSync(join(dir, 'bin'))
  writeFileSync(join(dir, 'bin', 'gh'), [
    '#!/bin/sh',
    'if [ -n "$STUB_GH_FAIL" ]; then echo "stub gh: network down" >&2; exit 1; fi',
    '[ "$1 $2 $3 $4" = "pr list --state merged" ] || { echo "stub gh: unexpected $*" >&2; exit 64; }',
    'cat "$STUB_GH_PRS"',
  ].join('\n'))
  chmodSync(join(dir, 'bin', 'gh'), 0o755)
  execFileSync('git', ['init', '-q', '--bare', '-b', 'main', join(dir, 'origin.git')], { env })
  execFileSync('git', ['init', '-q', '-b', 'main', root], { env })
  writeFileSync(join(root, '.gitignore'), [
    '.claude/', 'scratch/', '.shared', 'node_modules/', '.venv/', '__pycache__/', '.pytest_cache/', '*.tsbuildinfo', 'dist/',
    '.env', 'coverage/', '.wrangler/', '.agents/hooks/logs/', '',
  ].join('\n'))
  git('add', '.')
  git('commit', '-q', '-m', 'initial')
  git('remote', 'add', 'origin', join(dir, 'origin.git'))

  const prs = []
  const record = (branch, head) => prs.push(`${branch} ${head}`)
  for (const branch of ['merged', 'dirty', 'ignored', 'active', 'locked', 'runtime', 'plain', 'gone']) {
    record(`feat/${branch}`, mergedPr(`feat/${branch}`))
  }
  // Local tip behind its PR's head, on a PR-side commit: still merged.
  const behind = mergedPr('feat/behind', 2)
  record('feat/behind', behind)
  git('branch', '-f', 'feat/behind', `${behind}~1`)
  // One local commit past the PR's head: unmerged work.
  record('feat/ahead', mergedPr('feat/ahead'))
  commit('feat/ahead')
  git('checkout', '-q', 'main')
  // A name reused for a fresh branch from the main-line commit the old PR
  // branched from. That commit is an ancestor of the old PR's head.
  const base = git('rev-parse', 'main')
  record('feat/reused', mergedPr('feat/reused'))
  git('branch', '-f', 'feat/reused', base)
  // A name reused at main's tip, and a branch no PR ever merged.
  git('branch', 'feat/fresh', 'main')
  record('feat/fresh', base)
  git('branch', 'feat/unmerged', 'main')
  commit('feat/unmerged')
  git('checkout', '-q', 'main')
  git('push', '-q', 'origin', 'main')
  writeFileSync(env.STUB_GH_PRS, `${prs.join('\n')}\n`)

  for (const name of ['merged', 'behind', 'ahead', 'dirty', 'ignored', 'active', 'locked', 'reused', 'gone']) {
    git('worktree', 'add', '-q', wt(name), `feat/${name}`)
  }
  git('worktree', 'add', '-q', runtimeWt, 'feat/runtime')
  git('worktree', 'add', '-q', '--detach', wt('detached'), 'main')
  git('worktree', 'lock', wt('locked'))
  writeFileSync(join(wt('dirty'), 'scratch.txt'), 'unsaved\n')
  // Dependency installs, tool caches, and build output regenerate, at any depth.
  const regenerable = (tree) => {
    for (const file of ['node_modules/pkg/index.js', 'web/node_modules/pkg/index.js', '.venv/bin/python',
      'api/__pycache__/app.pyc', '.pytest_cache/v', 'app.tsbuildinfo', 'web/dist/index.js']) {
      mkdirSync(join(tree, file, '..'), { recursive: true })
      writeFileSync(join(tree, file), 'generated\n')
    }
  }
  regenerable(wt('behind'))
  // One unrecognized ignored path keeps the worktree, whatever else is there.
  regenerable(wt('ignored'))
  mkdirSync(join(wt('ignored'), 'scratch'))
  writeFileSync(join(wt('ignored'), 'scratch', 'valuable'), 'keep me\n')
  // Ignored symlinks are safe to unlink; their targets stay in the main checkout.
  symlinkSync(join(root, '.gitignore'), join(wt('merged'), '.shared'))
  rmSync(wt('gone'), { recursive: true })
  // Runtime scratch checkouts with no commits of their own. Session setup copies
  // ignored config from the main checkout.
  writeFileSync(join(root, '.env'), 'KEY=main\n')
  git('branch', 'claude/fresh-session', 'main')
  git('worktree', 'add', '-q', rt('fresh'), 'claude/fresh-session')
  for (const name of ['stale', 'copy', 'edited']) git('worktree', 'add', '-q', '--detach', rt(name), 'main')
  writeFileSync(join(rt('copy'), '.env'), 'KEY=main\n')
  for (const file of ['.agents/hooks/logs/session.log', 'coverage/index.html', 'web/.wrangler/state']) {
    mkdirSync(join(rt('copy'), file, '..'), { recursive: true })
    writeFileSync(join(rt('copy'), file), 'generated\n')
  }
  writeFileSync(join(rt('edited'), '.env'), 'KEY=edited\n')
  for (const name of ['stale', 'copy', 'edited']) idle(rt(name))
  sleeper = spawn('sleep', ['120'], { cwd: wt('active'), stdio: 'ignore' })
})

after(() => {
  sleeper?.kill()
  rmSync(dir, { recursive: true, force: true })
})

test('the dry run judges every candidate and preserves worktrees and branches', () => {
  const before = worktrees()
  const { status, stdout, stderr } = prune()
  assert.equal(status, 0, stderr)
  const expected = [
    [wt('merged'), 'prune', 'merged PR (feat/merged)'],
    [wt('behind'), 'prune', 'merged PR (feat/behind)'],
    [wt('ahead'), 'keep', 'unmerged commits (feat/ahead)'],
    [wt('dirty'), 'keep', 'uncommitted changes (feat/dirty)'],
    [wt('ignored'), 'prune', 'merged PR (feat/ignored)'],
    [wt('active'), 'keep', 'a process is working in it (feat/active)'],
    [wt('locked'), 'keep', 'locked'],
    [wt('reused'), 'keep', 'no commits beyond main, --include-empty (feat/reused)'],
    [wt('gone'), 'prune', 'directory is gone'],
    [wt('detached'), 'keep', 'detached HEAD'],
    [runtimeWt, 'keep', 'runtime-owned (--include-runtime)'],
    ...['stale', 'copy', 'edited', 'fresh'].map((name) => [rt(name), 'keep', 'runtime-owned (--include-runtime)']),
    ['branch feat/plain', 'prune', 'merged PR'],
  ]
  for (const [subject, verdict, reason] of expected) {
    assert.equal(verdictOf(stdout, subject), `${verdict} ${subject} ${reason}`)
  }
  for (const quiet of ['feat/fresh', 'feat/unmerged', 'main']) {
    assert.deepEqual(linesFor(stdout, `branch ${quiet}`), [], `${quiet} is kept without a verdict line`)
  }
  assert.ok(stdout.endsWith(`Dry run: no worktrees or local branches changed. To remove the lines marked prune, run:\n  ${script} --apply\n`), stdout)
  assert.equal(worktrees(), before)
})

test('the opt-in flags widen only what they name', () => {
  const { status, stdout, stderr } = prune('--include-runtime', '--include-empty')
  assert.equal(status, 0, stderr)
  assert.equal(verdictOf(stdout, runtimeWt), `prune ${runtimeWt} merged PR (feat/runtime)`)
  assert.equal(verdictOf(stdout, wt('reused')), `prune ${wt('reused')} no commits beyond main (feat/reused)`)
  assert.equal(verdictOf(stdout, 'branch feat/fresh'), 'prune branch feat/fresh no commits beyond main')
  assert.equal(verdictOf(stdout, wt('ahead')), `keep ${wt('ahead')} unmerged commits (feat/ahead)`)
  // Runtime checkouts with no commits of their own go once idle a day, detached
  // or not; unchanged copies of the main checkout's ignored files lose nothing.
  for (const name of ['stale', 'copy']) {
    assert.equal(verdictOf(stdout, rt(name)), `prune ${rt(name)} runtime, idle a day, no commits beyond main (detached)`)
  }
  assert.equal(verdictOf(stdout, rt('fresh')), `keep ${rt('fresh')} runtime, git activity within a day (claude/fresh-session)`)
  assert.equal(verdictOf(stdout, rt('edited')), `keep ${rt('edited')} unique local config needs inspection (detached)`)
  assert.equal(verdictOf(stdout, wt('detached')), `keep ${wt('detached')} detached HEAD`, 'a person detached it on purpose')
  assert.ok(stdout.endsWith(`\n  ${script} --include-runtime --include-empty --apply\n`), 'the hint keeps the flags')
  // `make prune-worktrees` supplies its own spelling of the same rerun.
  const viaMake = spawnSync('bash', [script], { cwd: root, encoding: 'utf8',
    env: { ...env, PRUNE_WORKTREES_RERUN: 'make prune-worktrees RUNTIME=1 APPLY=1' } })
  assert.ok(viaMake.stdout.endsWith('\n  make prune-worktrees RUNTIME=1 APPLY=1\n'), viaMake.stdout + viaMake.stderr)
  assert.deepEqual(linesFor(stdout, 'branch feat/unmerged'), [])
  assert.deepEqual(linesFor(stdout, root), [], 'the main checkout is never a candidate')
  // Even when the main checkout is on another branch, main itself is never pruned.
  git('checkout', '-q', 'feat/unmerged')
  try {
    const moved = prune('--include-empty')
    assert.equal(moved.status, 0, moved.stderr)
    assert.deepEqual(linesFor(moved.stdout, 'branch main'), [])
  } finally {
    git('checkout', '-q', 'main')
  }
})

test('without the merged-PR list it refuses to judge or remove anything', () => {
  const before = worktrees()
  const empty = join(dir, 'no-prs.txt')
  writeFileSync(empty, '')
  // An lsof that sees nothing would make every worktree look idle.
  mkdirSync(join(dir, 'blind'))
  writeFileSync(join(dir, 'blind', 'lsof'), '#!/bin/sh\nexit 1\n')
  chmodSync(join(dir, 'blind', 'lsof'), 0o755)
  for (const [override, message] of [
    [{ STUB_GH_FAIL: '1' }, /network down/],
    [{ STUB_GH_PRS: empty }, /refusing to judge/],
    [{ PATH: `${join(dir, 'blind')}:${env.PATH}` }, /lsof failed; refusing to judge/],
  ]) {
    const { status, stdout, stderr } = spawnSync('bash', [script, '--apply', '--include-empty'],
      { cwd: root, env: { ...env, ...override }, encoding: 'utf8' })
    assert.notEqual(status, 0)
    assert.match(stderr, message)
    assert.doesNotMatch(stdout, /removed/)
    assert.equal(worktrees(), before)
  }
})

test('--apply removes exactly what the dry run marked prune', () => {
  const { status, stdout, stderr } = prune('--apply')
  assert.equal(status, 0, stderr)
  for (const name of ['merged', 'behind', 'ignored']) {
    assert.ok(!existsSync(wt(name)), `${name} worktree still on disk`)
    assert.ok(!worktrees().includes(wt(name)), `${name} still registered`)
    assert.ok(!branchExists(`feat/${name}`), `feat/${name} not deleted`)
  }
  assert.ok(!worktrees().includes(wt('gone')), 'the vanished worktree was not pruned')
  assert.ok(!branchExists('feat/plain'), 'feat/plain not deleted')
  for (const name of ['ahead', 'dirty', 'active', 'locked', 'reused', 'detached']) {
    assert.ok(existsSync(wt(name)) && worktrees().includes(wt(name)), `${name} was removed`)
  }
  assert.ok(existsSync(join(wt('dirty'), 'scratch.txt')))
  const archiveDir = join(dir, 'Project', '_worktree-archive', 'root')
  const archives = readdirSync(archiveDir).filter((name) => name.startsWith('wt-ignored-'))
  assert.equal(archives.length, 1)
  assert.match(execFileSync('tar', ['-xOzf', join(archiveDir, archives[0]), 'scratch/valuable'], { encoding: 'utf8' }), /keep me/)
  assert.ok(existsSync(join(root, '.gitignore')), 'the symlink target was removed')
  for (const name of ['ahead', 'dirty', 'active', 'locked', 'reused', 'runtime', 'fresh', 'unmerged']) {
    assert.ok(branchExists(`feat/${name}`), `feat/${name} was deleted`)
  }
  assert.match(stdout, /removed .*wt-merged and feat\/merged/)
})

// Runs after the dry runs above scanned these worktrees: scanning must not have
// refreshed their index into looking recently used.
test('--include-runtime --apply removes idle runtime checkouts and keeps the rest', () => {
  const { status, stdout, stderr } = prune('--apply', '--include-runtime')
  assert.equal(status, 0, stderr)
  for (const tree of [rt('stale'), rt('copy'), runtimeWt]) {
    assert.ok(!existsSync(tree) && !worktrees().includes(tree), `${tree} still present`)
  }
  assert.ok(stdout.split('\n').includes(`removed ${rt('stale')}`), `a detached removal names no branch:\n${stdout}`)
  assert.ok(!branchExists('feat/runtime'), 'the merged runtime branch survived')
  for (const tree of [rt('fresh'), rt('edited'), wt('detached')]) {
    assert.ok(existsSync(tree) && worktrees().includes(tree), `${tree} was removed`)
  }
  assert.equal(readFileSync(join(rt('edited'), '.env'), 'utf8'), 'KEY=edited\n')
  assert.equal(readFileSync(join(root, '.env'), 'utf8'), 'KEY=main\n', 'the main checkout copy was touched')
  assert.ok(branchExists('claude/fresh-session'))
})

test('an archive failure keeps the worktree and reports failure', () => {
  const head = mergedPr('feat/archive-failure')
  git('push', '-q', 'origin', 'main')
  writeFileSync(env.STUB_GH_PRS, `${readFileSync(env.STUB_GH_PRS, 'utf8')}feat/archive-failure ${head}\n`)
  git('worktree', 'add', '-q', wt('archive-failure'), 'feat/archive-failure')
  mkdirSync(join(wt('archive-failure'), 'scratch'))
  writeFileSync(join(wt('archive-failure'), 'scratch', 'valuable'), 'preserve me\n')

  const archiveDir = join(dir, 'Project', '_worktree-archive', 'root')
  chmodSync(archiveDir, 0o755)
  try {
    const result = prune('--apply')
    assert.notEqual(result.status, 0)
    assert.match(result.stdout, /skipped .*wt-archive-failure: could not archive ignored payload/)
    assert.ok(existsSync(join(wt('archive-failure'), 'scratch', 'valuable')))
  } finally {
    chmodSync(archiveDir, 0o700)
  }

  const retry = prune('--apply')
  assert.equal(retry.status, 0, retry.stderr)
  assert.ok(!existsSync(wt('archive-failure')))
})
