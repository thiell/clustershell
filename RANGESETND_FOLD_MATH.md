# RangeSetND folding — mathematical reference

Reference for the nD folding functions in `lib/ClusterShell/RangeSet.py` as
rewritten in PR #656 (commit dfcb118, targeted at 1.11):
`_fold_univariate`, `_fold_multivariate_expand`, `_fold_multivariate_merge`,
`_sort`. The pre-#656 algorithm is described where the comparison is
instructive. Measurements and validation summary: see PR #656.

## 1. Model and notation

Fix a dimension D >= 1. An *element value* is a padded index string ("5",
"05", "0005", …). Distinct strings are distinct values even when numerically
equal — "5" != "05" — which is how mixed-length zero padding works since 1.9
(node `n05` differs from node `n5`). Write Sigma for the set of all such
strings.

- An *axis set* X is a finite nonempty subset of Sigma (a `RangeSet`:
  a `set` subclass whose members are these strings).
- A *vector* (or *box*) is B = X_1 x X_2 x ... x X_D, the Cartesian product
  of D axis sets. Its *size* is |B| = prod_d |X_d|.
- A `RangeSetND` holds a list V = [B_1, ..., B_n] (the `_veclist`, each entry
  a list of D RangeSets). The *represented set* is the union of points

      S(V) = B_1 ∪ B_2 ∪ ... ∪ B_n  ⊆  Sigma^D.

Input veclists are arbitrary: boxes may overlap, duplicate, or nest. Most of
the API (`__len__`, `__str__`, iteration, `__getitem__`, …) is only correct
on a *disjoint* decomposition — e.g. `len()` computes sum_i |B_i|, which
equals |S(V)| only if the B_i are pairwise disjoint. Hence folding, deferred
via the `_dirty` flag and the `precond_fold` decorator so that k mutations
cost one fold (amortization).

**Contract of `_fold()`.** Produce V' from V with:

- (P1) *exactness*: S(V') = S(V);
- (P2) *disjointness*: B_i ∩ B_j = ∅ for all i != j in V';
- (P3) *canonicity*: V' (including its order) is a pure function of the
  point set S(V) — independent of how the input was decomposed, of insertion
  order, and of hash seeds;
- (P4) *compactness*, best effort: |V'| small. Minimal |V'| is not attempted:
  computing a minimum-size partition of an arbitrary point set into
  combinatorial boxes is NP-hard in general (related Boolean-matrix problems,
  e.g. partition into minimum all-ones combinatorial rectangles), so both the
  old and new algorithms are greedy heuristics that stop at a *maximal*
  fixpoint (Section 5.4).

## 2. Pipeline

```
_fold():
    if len(veclist) > 1:
        _fold_univariate() or _fold_multivariate()

_fold_multivariate():
    _fold_multivariate_expand()   # phase 1: normalize to disjoint "rows"
    _fold_multivariate_merge()    # phase 2: greedy re-merging + final sort
```

`update()` additionally tries `_fold_univariate()` eagerly after each append
until the first time two axes are seen to vary (`_multivar_hint`), after
which appends are O(1) and folding waits for the next read access.

## 3. `_fold_univariate` — the one-varying-axis identity

Let all vectors agree on every axis except (at most) axis v:
B_i = C_1 x ... x X_{i,v} x ... x C_D with the C_d shared. Then

    ∪_i B_i = C_1 x ... x (∪_i X_{i,v}) x ... x C_D            (U1)

*Proof.* Cartesian product distributes over union in a single factor:
a point (c_1, …, x, …, c_D) lies in the left side iff x ∈ X_{i,v} for some i
iff it lies in the right side. ∎

So the fold is exact, produces a single box (trivially disjoint), and is
computed in-place by unioning axis v of vector 0 (`slist.count` detects which
axis varies in O(nD)). D = 1 is always this case. If two or more axes vary,
`_fold_univariate` returns False and the multivariate path runs.

## 4. `_fold_multivariate_expand` — normalization to rows

**Definition.** For a prefix p = (x_1, …, x_{D-1}) ∈ Sigma^{D-1}, the *fiber*
of S over p is fib(p) = { v ∈ Sigma : (p, v) ∈ S }. The *row decomposition*
of S is

    R(S) = { {x_1} x ... x {x_{D-1}} x fib(p)  :  fib(p) != ∅ }.

The implementation computes exactly R(S(V)): for each input box B_i it
iterates the prefix products `product(*rgvec[:-1])` and bulk-unions the last
axis into `rows[p]`, i.e.

    rows[p] = ∪ { X_{i,D} : p ∈ X_{i,1} x ... x X_{i,D-1} } = fib(p),

with overlaps and duplicates absorbed by set union. Vectors containing an
empty axis contribute nothing (`product` of an empty pool is empty; the
`if not last` guard handles an empty last axis) — consistent with such a box
being the empty set.

**Lemma L0 (product disjointness).** For boxes A = prod X_d and B = prod Y_d
with all axes nonempty: A ∩ B = prod_d (X_d ∩ Y_d), hence

    A ∩ B = ∅  ⟺  X_d ∩ Y_d = ∅ for some axis d.

*Proof.* Componentwise; a product is empty iff some factor is. ∎

**Lemma L1 (row properties).**
(a) *Exactness*: S(R(S)) = S — each point (p, v) belongs to exactly the row
    of its prefix.
(b) *Disjointness*: distinct rows have distinct prefixes, which differ at
    some axis d < D; there the singleton axes {x_d} != {x'_d} are disjoint,
    so the rows are disjoint by L0.
(c) *Last-axis saturation*: no two rows are mergeable along axis D-1
    (Section 5), because the dict keying makes prefixes unique. ∎

Note R(S) depends only on S — not on the input decomposition. This is the
root of canonicity (P3), and it is the same normalization master computes
(master expands to single *points*, i.e. one vector per element; rows are the
result of grouping those points by prefix, which master's first merge passes
rediscover pairwise at O(k^2) cost per row).

Implementation notes: elements are reused string objects (no re-rendering, so
padding is preserved verbatim); `set(last)`, `row.update(last)` and
`frozenset(rg)` hit CPython's C fast path for set arguments (direct hash-table
copy, no Python-level iteration); every RangeSet placed in a row is freshly
created here, with `_autostep` propagated — establishing the *ownership
invariant* used by the merge phase (Section 5.3).

## 5. `_fold_multivariate_merge` — greedy re-merging

### 5.1 The merge rule

**Definition.** Boxes A = prod X_d and B = prod Y_d are *mergeable along axis
d* iff X_e = Y_e for every e != d. For such a pair,

    A ∪ B = X_1 x ... x (X_d ∪ Y_d) x ... x X_D                (U2)

is again a box — identity (U1) applied to two terms. This is the *only*
union of two distinct boxes that is guaranteed to be a box, which is why
single-axis merging is the natural greedy step.

**Lemma L2 (disjoint pairs merge disjointly).** If A, B are disjoint,
nonempty, and mergeable along d, then X_d ∩ Y_d = ∅.
*Proof.* A ∩ B = (prod_{e != d} X_e) x (X_d ∩ Y_d) by L0's product identity;
the shared factors are nonempty, so disjointness forces the d-factor empty. ∎

Consequently, on a pairwise-disjoint veclist the merge is always a *disjoint
union* on the differing axis — `set.update(gvec[pos], rgvec[pos])` with no
overlap handling needed.

**Lemma L3 (master's containment branch is dead code).** Master's pair scan
has a branch for "axis d strictly contained, all other axes equal → keep the
larger". That configuration implies A ⊆ B or B ⊆ A with A, B nonempty, hence
A ∩ B != ∅ — impossible between vectors of a pairwise-disjoint veclist, which
is the only kind `_fold_multivariate_merge` ever receives (it runs only after
expand). Likewise the "identical vectors" case (nb_diff = 0) cannot occur.
The rewrite drops both branches and asserts the invariant instead of
re-testing it per pair. ∎

**Lemma L4 (invariant preservation).** Replacing disjoint A, B mergeable
along d by C = A ∪ B keeps the veclist pairwise disjoint and exact:
for any other vector E, C ∩ E = (A ∩ E) ∪ (B ∩ E) = ∅, and the union of all
vectors is unchanged. By induction the invariants hold through the whole
merge phase. ∎

### 5.2 Group merge, one axis at a time

Fix axis d. On a pairwise-disjoint veclist, "mergeable along d" is an
equivalence relation ≡_d (it is equality of the projection to the other
axes). One pass groups vectors by the key

    key_d(B) = (frozenset(X_1), ..., frozenset(X_{d-1}),
                frozenset(X_{d+1}), ..., frozenset(X_D))

and unions each class along axis d. frozenset equality is set equality, so
dict fibers are exactly the ≡_d classes (hash collisions affect speed only).

**Lemma L5 (pass = class union, order-free).** The pass output replaces each
class {A_1, …, A_k} by X_1 x … x (∪_i X_{i,d}) x … x X_D, independent of
enumeration order (∪ is associative/commutative, and the partition into
classes is order-independent). After the pass, axis d is *saturated*: no two
survivors share a key_d. ∎

The loop then round-robins: axes are processed in a fixed order
(D-2, …, 0 on the first round — axis D-1 is skipped there because rows are
already last-axis saturated by L1(c) — then D-1, …, 0 on every later round)
until a full round performs no merge.

**Lemma L5b (prefix-box disjointness; the last axis never re-merges).**
Write pref(B) = X_1 x ... x X_{D-1} for the *prefix box* of B. After expand,
prefix boxes are distinct singleton products, hence pairwise disjoint. A
merge along an axis d < D-1 requires all other axes equal — including axis
D-1 — so within the prefix it unions two boxes that are equal except at d
and disjoint at d (L2 restricted to the prefix): the merged prefix box is
their union (U2), disjoint from every other prefix box (as in L4). By
induction, every veclist reachable by merges along axes d < D-1 has pairwise
disjoint — in particular pairwise *distinct* — prefix boxes. A merge along
axis D-1 would require two vectors with equal nonempty prefix boxes, which
therefore never exist: last-axis merges cannot fire after row expansion. ∎

(This is why expansion targets the last axis: fibers are last-axis-maximal
from the start, so merging only ever needs the other axes. The pos = D-1
passes in rounds >= 2 are consequently pure verification; the code keeps
them as cheap robustness — one hashing sweep — rather than encoding L5b.
An earlier revision of this document justified re-including axis D-1 with a
3-vector 3D example; that configuration is unreachable from expand output —
adversarial review caught it, and empirically the loop never exceeds two
rounds, one merging sweep plus one verifying sweep, across all probed
shapes.)

**Lemma L6 (termination).** Every merge decreases the vector count by one and
the count is bounded below by 1; a round with no merge exits the loop. So the
number of rounds is at most (#merges + 1) <= |R(S)|, and each round makes at
most D passes. This bound is very loose: in practice (and on every shape
probed adversarially) the loop ends after two rounds — one merging sweep,
one verifying sweep. ∎

**Lemma L7 (fixpoint equivalence with master).** The loop exits iff no pair
of vectors is mergeable along any axis — exactly the condition under which
master's final full O(n^2) pass would find nothing (its other merge branches
being dead by L3). Both algorithms therefore stop at decompositions that are
*maximal* with respect to single-axis merging; they may stop at *different*
maximal decompositions (Section 5.4). ∎

### 5.3 Ownership (why in-place `set.update` is safe)

Expand creates every RangeSet in the veclist fresh, and no axis object is
ever shared between two vectors. A merge keeps the class representative's
objects and mutates only its axis d; the consumed vectors' objects are
dropped entirely, so exclusivity is preserved inductively. In particular
user-supplied RangeSet objects (including those passed with
`copy_rangeset=False`) are never mutated — the same contract as master.

### 5.4 Fold quality: maximal != minimal

Maximal decompositions are not unique and not minimum-size, and the two
algorithms walk different greedy paths: the rewrite merges axis-major
(saturate one axis globally, then the next); master merged size-major
(size-sorted pairwise scans). Worked example (from the updated tests),
S = a[0-2]b[1-3]c4 ∪ a[0-1]b[2-3]c[4-5], |S| = 13:

    new (3 boxes):     {0,1}x{2,3}x{4,5}   (8)
                       {2}x{1,2,3}x{4}     (3)
                       {0,1}x{1}x{4}       (2)

    master (4 boxes):  {0,1}x{1,2}x{4}     (4)
                       {0,1}x{3}x{4,5}     (4)
                       {2}x{1,2,3}x{4}     (3)
                       {0,1}x{2}x{5}       (2)

Both are exact (8+3+2 = 4+4+3+2 = 13), pairwise disjoint, and maximal (every
pair differs in >= 2 axes — check each pair against the merge rule), yet they
have different sizes. Neither greedy dominates in general; empirically
(44k differential fuzz cases) the axis-major path gives a strictly smaller
decomposition about 4x more often than a larger one, and is never wrong
(P1/P2 always hold). This is the same class of output change that ec14536
introduced in 2022 when it replaced the pre-2022 splitting algorithm.

## 6. `_sort` — canonical order (P3)

The final ordering uses the key

    kappa(B) = (-|B|, ((-|X_1|, min X_1, max X_1), ...,
                       (-|X_D|, min X_D, max X_D)))

where min/max are taken in the element order sigma used by `_sorted()`
(length-then-lexicographic for non-negative strings, so numeric order within
equal padding; negatives ordered by value). Larger boxes come first, then
axis-wise size and bounds. The rewrite computes `_sorted()` once per axis
instead of twice (`rg[0]`/`rg[-1]` each re-sorted the set); values and hence
the ordering are identical to master's key.

**Lemma L8 (totality on disjoint decompositions).** If A != B are pairwise
disjoint boxes then kappa(A) != kappa(B).
*Proof.* Suppose kappa(A) = kappa(B). Then for every axis d, |X_d| = |Y_d|
and min X_d = min Y_d. By L0 some axis d* has X_{d*} ∩ Y_{d*} = ∅; but their
minima are equal, exhibiting a common element — contradiction. ∎

**Theorem (canonicity).** The folded veclist — content *and* order — is a
pure function of the point set S:
rows R(S) depend only on S (L1); each merge pass output is a pure function of
its input set of vectors (L5) with a fixed axis schedule; and the final sort
is by a key that is total on the (pairwise-disjoint) result (L8), so the
sorted order does not depend on list order, dict order, or string hash seeds.
Hence `str(RangeSetND)` is reproducible across runs, interpreters (including
Python 2.7's unordered dicts), and input decompositions. ∎
(Master satisfies the same theorem by an analogous argument; the two
functions of S are simply different where Section 5.4 applies.)

## 7. Complexity

Let P = |S| (unique points), n_0 = |R(S)| (rows), D the dimension, and
"content" = sum over vectors of sum of axis cardinalities.

| phase | master (post-ec14536) | rewrite |
|---|---|---|
| expand | O(P·D) RangeSet objects (~800B/pt in 2D), set of P tuples | O(P) C-level set inserts into n_0 rows; O(P) strings held |
| merge, structured data | per pass: O(P log P) sort + adjacent merges with O(k^2) row unions and O(n) `list.pop` shifts | per pass: O(n·D·kbar) frozenset hashing + O(content) disjoint unions |
| merge, scattered data | final full pass O(m^2·D) *with a RangeSet copy + intersection allocated per rejected pair* (the #485 profile: 71M copies) | same hashing passes; no per-pair work at all |
| sort | every pass; key re-sorts each axis twice | once, at the end; one `_sorted()` per axis |
| rounds | easy passes + 1 full pass, repeated while changing | <= #merges + 1 full rounds, 2 in practice (L6) |

The asymptotic killer in master is the O(m^2) pairwise pass whenever the data
does not collapse (m ~ P for scattered sets: 26s for 3k points, hours for
50k); the rewrite replaces it with O(P·D) hashing per round (0.02s and 0.45s
respectively). On expansion-heavy inputs the rewrite is also ~16x lighter in
memory because rows replace per-point vectors.

## 8. Padding and autostep

Elements are opaque strings end to end: expand moves existing string objects
(`product`, bulk set copies) and merge only unions sets of them, so "05" and
"5" remain distinct values and per-element padding survives folding exactly
(`pads()`, `iter_padding()` read it back off the strings). `_autostep` is
copied onto every RangeSet created by expand — it affects only string
rendering (`x-y/step` notation), never membership, so folding and autostep
commute.

## 9. Pointers

- Measurements, fuzz statistics and validation summary: PR #656.
- Validation performed (out of tree): differential fuzzing vs the previous
  implementation with element-set/len/pads/disjointness/idempotency oracles
  (44k+ cases, zero failures), canonicity fuzzing across build paths and
  hash seeds, identical fold digests on Python 2.7.5/3.9/3.13, adversarial
  perf-cliff search (no shape found where the new code is slower).
- History: #485 (Cray EX xnames, 6m38s) → ec14536 ("nD folding
  optimization", 2022: full expansion + easy passes, 2.8s) → PR #656
  (rows + hash-grouped merging, 0.06s).
