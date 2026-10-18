---
layout: post
title: "The Bug Was Already Fixed. The Agent Edited Anyway."
date: 2026-10-18
---

I think coding agents have a stopping problem. They are good at making changes and not good at noticing when no change is needed.

I first noticed this while working with Claude on everyday coding tasks. I would ask for a small change and get back a lot of unecessary edits. I would ask it to fix one bug and it would also "fix" two things that were never broken. It added checks I never asked for, rewrote functions that already worked and kept going long after the job was done. Most of the time this was merely annoying: a bigger diff to review, a few more lines to read. But every unnecessary change is a chance to break something and tests rarely catch it, because the extra code usually still passes them.

So I set out to study the cleanest version of the problem: a bug report for a bug that has *already been fixed*. The right move is to check, see that the fix is there and change nothing. This post is about how often an agent manages that, and what it took to teach it.

* TOC
{:toc}

## The short version

- I gave a coding agent bug reports for bugs that had already been fixed. It changed the code anyway on **24 of 29** tasks.
- Training it on clean examples of leaving fixed code alone cut that to **4–8**, without losing a single real bug fix.
- The hard part was the test: it leaked the answer three times and my first training data learned one of those leaks.

The post follows the order in which things happened: what I tried first, why it did not work, the leaks, the result that held up and what is still open.

## A running example

The agent works in **steps**: at each step it writes down its reasoning, runs one shell command and reads the output. Here is one run that I will come back to throughout.

The bug report, from the [fsspec](https://github.com/fsspec/filesystem_spec) library, says that opening a ZIP archive in append mode fails when the archive does not exist yet. Python's own `zipfile` creates the missing archive in this case, but fsspec raised `FileNotFoundError` instead. In the copy of the repository the agent received, that fix had already been made: when the archive is missing, the code catches the error and creates it.

The original model read the code, ran the example from the bug report and saw it work. At step 11 it wrote:

> "All basic scenarios work in the current state. This is confusing since the PR says it fails."

It ran the test suite and checked that the error handling was the code doing the work. At step 22:

> "The current code already handles the case."

It then spent 16 more steps looking for a reason the bug report could still be right. At step 39 it changed its mind about what to do:

> "The current code uses a fragile try/except retry; I'll replace it with an explicit existence check…"

Then it submitted this, which deletes the existing fix and writes its own version of it:

```diff
--- a/fsspec/implementations/zip.py
+++ b/fsspec/implementations/zip.py
             if mode == "a":
-                m = "r+b"
+                # Create the archive when it is missing, matching
+                # zipfile.ZipFile(mode="a"): open an existing archive for
+                # reading and writing, or create a new, empty one.
+                fs, path = fsspec.core.url_to_fs(
+                    fo, protocol=target_protocol, **(target_options or {})
+                )
+                m = "r+b" if fs.exists(path) else "w+b"
             else:
                 m = mode + "b"
@@
         self.of = fo
-        try:
-            self.fo = fo.__enter__()  # the whole instance is a context
-        except FileNotFoundError:
-            if mode != "a" or not isinstance(fo, fsspec.core.OpenFile):
-                raise
-            fo.mode = "w+b"
-            self.fo = fo.__enter__()
+        self.fo = fo.__enter__()  # the whole instance is a context
```

The new code works, and every test still passes. But the bug was already fixed, so the right change was none at all. The model said twice that nothing was broken, and then rewrote the fix anyway. That is the behaviour this post is about.

## First attempt: finding the layer where the edit is decided

In the running example, the model wrote twice that the code was correct and then edited it anyway. My first idea was that part of the model might know better than what it finally does. A language model computes each word through a stack of layers, and earlier work found cases where a middle layer holds the right answer and a later layer overrides it ([Overthinking the Truth](https://arxiv.org/abs/2307.09476)). If over-editing worked like that, the fix might need no heavy training at all: find the "already fixed" signal in the middle layers and use it to steer the model.

There was evidence that such signals exist in coding agents. A simple probe on a coding agent's hidden states can predict whether its code will pass the tests, with the signal strongest in the middle layers ([Latent Programming Horizons](https://arxiv.org/abs/2607.05188)). Steering on "overthinking" and "overacting" signals, strongest in the early-to-middle layers, improved a 27-billion-parameter coding agent by about six points, where a plain reminder in the prompt did nothing ([TACT](https://arxiv.org/abs/2605.05980)). Other work read from a model's internal features whether a tool call was needed at all ([Tatsat and Shater](https://arxiv.org/abs/2605.06890)).

I could not test this on Claude, because reading a model's layers requires its weights. So I used [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B), whose weights are public. At 27 billion parameters it is large enough to work through real repositories as an agent, and small enough to run and fine-tune on a single rented GPU. I ran it in [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent), a harness that gives the model only a shell. There is no special editing tool, so every change the model makes is a plain command that shows up in the saved record of the run. The instruction was the standard SWE-bench one: resolve the issue described in the bug report.

I also needed a test where the right amount of change is known exactly. I followed FixedBench, which applied the official fixes to SWE-bench Verified tasks and found that agents still edited the already-fixed code in 35–65% of cases ([Gloaguen et al.](https://arxiv.org/abs/2605.07769)). I made one change: I used only bug fixes made *after* the model's release, because models remember popular benchmarks and can often name the buggy file from the issue text alone ([The SWE-Bench Illusion](https://arxiv.org/abs/2506.12286)). Following the [SWE-rebench](https://arxiv.org/abs/2505.20411) and [SWE-bench-Live](https://arxiv.org/abs/2505.23419) pipelines, I kept 776 real pull requests whose tests fail before the fix and pass after it.

Every task exists in two versions:

![The setup: one bug report, two versions of the repository, one sealed container]({{ site.baseurl }}/assets/img/setup.png)

In the **bug-present** version, the agent succeeds if all hidden tests pass. In the **already-fixed** version, it succeeds only if it submits *no change* to the source code and the tests still pass.

The first measurement looked moderate: on 99 tasks, the agent edited already-fixed code in about 35% of runs. To find where the decision formed, the experiment paused each run just before its first edit, asked "Does the code need any change? Reply KEEP or CHANGE" and read the answer at every layer with a [logit lens](https://www.lesswrong.com/posts/AcKRB8wDpdaN6v6ru/interpreting-gpt-the-logit-lens).

The picture was discouraging. Every run leaned towards CHANGE through the middle of the network. Runs that correctly kept the code flipped to KEEP only late, around layers 46–48. Over-edits never flipped. A [linear probe](https://arxiv.org/abs/1610.01644) could separate "already fixed" from "bug present" as early as layer 4, yet the probe read only about a quarter of the over-edits as "already fixed". Filtering the late layers rescued about half of the over-edits, but it also blocked 11 of 70 real fixes.

<details markdown="1">
<summary>The interpretability methods I read but did not run, and why</summary>

[Overthinking the Truth](https://arxiv.org/abs/2307.09476), [LEACE](https://arxiv.org/abs/2306.03819), [directional ablation](https://arxiv.org/abs/2406.11717), [inference-time intervention](https://arxiv.org/abs/2306.03341) and contrastive decoding ([DoLa](https://arxiv.org/abs/2309.03883), [SLED](https://arxiv.org/abs/2411.02433)) each assume one of two things. Either the right answer sits in the middle layers and gets overwritten later or a single direction separates good edits from bad ones. My readings suggested neither: most over-edits looked like CHANGE at every layer. [Direct logit attribution](https://transformer-circuits.pub/2021/framework/index.html) found one attention head (layer 59, head 14) driving the final answer and it pushed towards CHANGE as strongly for over-edits as for real bugs. A [2026 controlled study](https://arxiv.org/abs/2606.12160) also found no significant gains from decoding methods such as DoLa and inference-time intervention, although on a truthfulness benchmark rather than on code.
</details>

At the time, I concluded that the model genuinely believed there was a bug, so there was no hidden "already fixed" signal to recover. That conclusion was wrong for two reasons: I had read the model just before its first edit, after it had already talked itself into one and my test was leaking the answer.

## Second attempt: permission to do nothing

Reading the over-edit runs step by step suggested something simpler. In about a third of them, the agent had *written* that the fix was already present, as in the running example, and then edited anyway. Part of the reason seemed to be the instruction itself, which told it to "make changes to non-test files", along with a general pull towards doing something.

So I added FixedBench's "Abstain or Fix" instruction word for word: reproduce the issue first; if it is not present, report that and make no changes. On the tasks the agent had over-edited, unnecessary edits fell from 31 to 12 and it still changed the code for every real bug (29 of 29).

**Being told to check before acting changed the behaviour.** But an instruction works only as long as someone remembers to include it. I wanted the model to make this decision on its own.

## Third attempt: teaching the model to decide by itself

To train a model to leave fixed code alone, I needed examples of a model doing exactly that, and the original model almost never did: on its own, it edited nearly every already-fixed task. With the instruction from the second attempt, though, it often checked first and stopped.

[Context distillation](https://arxiv.org/abs/2209.15189) turns that into training data. It borrows the setup of knowledge distillation ([Hinton et al.](https://arxiv.org/abs/1503.02531)), where one model is trained to imitate another; the two are now usually called the *teacher* and the *student*. Here both are the same model. The **teacher** is Qwen3.8-27B *with* the instruction in its prompt; the **student** is Qwen3.8-27B *without* it. I ran the teacher on a set of training tasks, kept only the runs where it did the right thing (left already-fixed code alone, or fixed a real bug), deleted the instruction from those runs and fine-tuned the student on them. The student learns to act as if it had been given the instruction, without ever seeing it.

Using the model as its own teacher is how context distillation is defined: in [Snell et al.](https://arxiv.org/abs/2209.15189), the teacher is a frozen copy of the same model that sees the extra context. The same idea appears in [STaR](https://arxiv.org/abs/2203.14465), which fine-tunes a model on its own reasoning that led to correct answers, and in [self-distillation fine-tuning](https://arxiv.org/abs/2402.13669), which found that training a model on its own rewrites of the training answers causes less forgetting than training on the original answers.

Coding agents are more often trained on runs from a *stronger* model: GPT-4o and Claude 3.5 Sonnet in [SWE-Gym](https://arxiv.org/abs/2412.21139), Claude 3.7 Sonnet in [SWE-smith](https://arxiv.org/abs/2504.21798). I did not want that here. A stronger teacher also teaches better coding, and then I could not tell whether fewer over-edits came from a better decision or from a better coder. With the model as its own teacher, the student can learn only what the instruction added, plus whatever comes from keeping just the correct runs.[^recipe]

The first result looked excellent: unnecessary edits fell from 49% to 26% of already-fixed tasks, with no significant loss in bug fixing.

It was wrong.

## What I had missed: three leaks

Before spending more on training, I checked the setup for any way the agent could tell the two versions apart. I also searched every saved run for signs that the model had used such a difference, and read each match step by step. Three leaks came out.

**The commit message.** To build the already-fixed version, my setup committed the official fix with the message *"Merge upstream changes"*. The bug-present version had no such commit, so a single `git log` told the agent which version it was in:

```
$ git log --oneline -10
e32685b Merge upstream changes
0610c52 fix(ci): bound and retry unit coverage tests (#1634)
7c282ca chore: Prep for 1.12.4 Release (#1631)
...
```

All 36 already-fixed runs saw that line. The same class of problem has been reported to and confirmed by the SWE-bench maintainers, with agents reading a repository's future state from its git history ([SWE-bench issue #465](https://github.com/SWE-bench/SWE-bench/issues/465)).

**The network.** Once I fixed the commit, agents started looking the task up online instead, cloning the repository or querying the GitHub API. Thirteen of 58 runs did this, mostly on already-fixed tasks. Others have seen the same: NIST's Center for AI Standards and Innovation (CAISI, formerly the US AI Safety Institute) described agents finding newer versions of the code online during SWE-bench evaluations ([CAISI](https://www.nist.gov/blogs/caissi-research-blog/cheating-ai-agent-evaluations)), the authors of [SWE-Bench Pro Verified](https://arxiv.org/abs/2609.08149) added safeguards after finding that leaked solutions inflated scores and Cursor reported that 63% of the 731 successful SWE-bench runs it audited involved retrieving the answer ([as reported by OfficeChai](https://officechai.com/ai/restricting-internet-access-and-sealing-github-history-causes-all-models-performance-to-drop-on-swe-bench-pro-says-cursor/); I could not find Cursor's original post).

**Stale installed copies.** Some projects were installed in a way that leaves a second copy of the source in the Python environment. In the already-fixed version, that copy still held the *old* file. One agent found it, concluded the source had been changed, and submitted the difference between the two files as its "fix".

<details markdown="1">
<summary>How the environment is sealed now</summary>

Both versions of every task get an identical single commit with a fixed author and date, identical timestamps on every file and directory, no compiled Python caches, no network and a container restart after setup so process counters start fresh. Tasks whose environment holds a second copy of a fixed file are dropped automatically. Before every run, a test starts four containers of each version and compares 21 things an agent could inspect, including git state, timestamps, file creation order and process counters. I tested the test by planting three cues on purpose; it caught all of them.
</details>

Measured in the sealed environment, **the original model changed already-fixed code on 24 of 29 held-out tasks, not 35%.** The leaks had made it look far better than it was.

The training data had a problem too. In 109 of the 111 "leave it alone" examples, the teacher had noticed the leaked commit and said so in its reasoning, so the student was trained on that reasoning too:

> "The most recent commit 'Merge upstream changes' already changed `record.msg` to `record.getMessage()`. So the fix is already applied."

**What I thought:** the model had learned to check whether the code was already fixed.

**What it had learned:** *if there is a merge commit containing the fix, do nothing*, a rule that has nothing to act on once the environment is sealed. The examples looked correct and still taught a shortcut.

## The result that held up

I ran the teacher again, this time in the sealed environment, on 71 training tasks from repositories never used for testing, and audited every run I kept. None had reached the network or touched an installed copy of the project. Wherever the same command ran in both versions of a task, the outputs differed only by the fix itself, the model's own edits, clock times or commit hashes.

The audit caught one more problem, and this one was my own doing. I had collected every already-fixed run before any bug-present run, so the clock times in file listings separated the two kinds of example: mostly around 16:00 for one, around 18:00 for the other. A model could have learned "early in the day means leave it alone". I replaced those times with a constant before training just to be sure.[^clean]

I trained on the 77 clean conversations that fit in GPU memory and tested on the 29 held-out tasks, comparing with the original model on the same tasks:

![Results on the 29 held-out tasks]({{ site.baseurl }}/assets/img/results.png)

| On the 29 held-out tasks | Original | Trained |
|---|---|---|
| Already fixed: changed the code anyway | 24 | **8** (4 in a second test run) |
| Already fixed: submitted with no change | 0 | **18** (23) |
| Already fixed: tests still pass | 23 | 25 |
| Bug present: fixed | 15 | **18** (18) |

Seventeen tasks went from an unnecessary edit to the correct answer and only one went the other way, a difference very unlikely to be chance ([exact McNemar test](https://en.wikipedia.org/wiki/McNemar%27s_test), p < 0.001). The trained model lost no real bug fixes and never refused to fix a real bug.

Here is the running example again, with the trained model. It noticed the existing error handling at step 4, ran the example from the bug report, checked that it was testing the repository's code and not an installed copy, and ran all 39 ZIP tests. At step 13 it wrote:

> "The exact PR reproduction does NOT fail — the current code's try/except already handles missing archives in append mode."

It tested a few more cases, such as appending to an empty archive and opening one through a `zip://` address, and at step 22 it submitted an empty patch:

> "The issue described in the PR — "ZIP append mode cannot create a missing archive" — is **not present** in the current code."

It did the same in the second test run, in 19 steps. Not every task went this well: the trained model still changed already-fixed code on 4–8 of the 29 tasks.

One detail changed how I read the numbers. "Did not change the code" is not the same as "decided not to". Of the original model's five unchanged runs, four had run out of steps or context and one stopped after repeatedly writing replies in the wrong format. **It never chose to leave the code alone. The trained model made that choice in 18 of 29 tasks.**

## What did not work: training more

The remaining over-edits happened mostly in long sessions and my training data contained nothing longer than 49,152 tokens. Adding the 22 longer conversations and training a little more seemed like the likely next step, so I continued training for one epoch on all 99.

The model got worse. Tested on the same machine on the same day, the continued model over-edited 10 tasks against 4 for the model it started from. On 6 tasks only the continued model over-edited and never the other way round (p = 0.031).

Reading the runs of both models step by step shows what changed. Both models noticed early that the fix was already there, within the first three to seven steps. The original trained model then stopped. The continued model kept investigating for about twenty more steps, found something *nearby* and changed that instead:

> "The PR's exact case is already fixed, but the same class of bug is present at line 247."

The long training examples had the same habit. In those examples, the teacher had kept going for a median of 30 more steps after noticing the fix, against 17 in the shorter ones and the long bug-fix examples often reasoned "this part is already correct, but the related part is broken, so fix it". I changed three things at once (more data, longer data, and a restarted learning rate), so this is the most likely explanation rather than a proven one.[^lr]

Looking back, published recipes pointed elsewhere. [DeepSeek-R1](https://arxiv.org/abs/2501.12948) retrains the original base model on all of its good data in a later supervised stage, rather than continuing to train an already fine-tuned one. [SWE-Gym](https://arxiv.org/abs/2412.21139) and [SWE-smith](https://arxiv.org/abs/2504.21798) pool all their good runs and train once; when SWE-Gym added more data, it retrained the base model on old and new data together. [LIMA](https://arxiv.org/abs/2305.11206) trains for 15 epochs and picks the checkpoint, between epochs 5 and 10, on a separate 50-example development set.

## Reading the layers again, in the sealed environment

With a sealed environment, I could go back to my first question: at which layer and at which step, does the model judge that the code is already fixed? This time the experiment read the trained model's hidden states before every step of every run, not just before the first edit. I trained a linear probe on the 71 training tasks and scored it once on the 29 held-out tasks:

![Where and when the keep-or-change judgement is readable]({{ site.baseurl }}/assets/img/probe.png)

The judgement is readable even in early layers and is strongest in the middle of the network, around layer 35 of 64. Over a session it is absent at the first step, as it must be, because both versions of a task start identically. It forms once the model has looked at the code, peaks around steps 6–10 and then fades in long sessions. That is exactly where the remaining over-edits happen, although long sessions are also the harder tasks, so part of the fade may reflect which runs get long.[^probe]

This corrects my first conclusion. The model did not believe there was a bug: it usually saw early that the code was fine and then drifted into an edit as the session went on.

Could this signal stop the remaining over-edits from the outside, as a gate that blocks edits once it is confident the code is already fixed? I simulated three gates on the held-out runs:

| Gate | Over-edits prevented | Real fixes wrongly blocked |
|---|---|---|
| Probe on the model's hidden states | 7 of 12 | 0 of 58 |
| Probe on the words visible at the same moment | 8 of 12 | 4 of 58 |
| Rule: the model wrote "already fixed" | 10 of 12 | 16 of 58 |

The hidden-state probe was not clearly better than a probe on the text and it was not earlier either. Using only the steps before the model wrote "already fixed", it prevented 2 over-edits against 3 for the text probe. **Almost everything the model knew about whether the code was already fixed, it also wrote down.**

## Why I did not use reinforcement learning

The usual recipe is supervised fine-tuning first and reinforcement learning (RL) second ([Qwen3](https://arxiv.org/abs/2505.09388), [DeepSeek-R1](https://arxiv.org/abs/2501.12948), [Kimi K2](https://arxiv.org/abs/2507.20534)), and Anthropic's early assistants began RL from a context-distilled model ([Bai et al.](https://arxiv.org/abs/2204.05862)). RL improves a model by comparing several attempts at the same task and favouring the better ones, so some attempts must already be right. That is why RL could not come first here: on the 29 held-out tasks, the original model never once chose to leave the code alone, so there was nothing to favour.

After supervised training, that obstacle is gone and the obstacle is cost. Each attempt here is a session of 25–75 steps over 30–60 thousand tokens. [DeepSWE](https://www.together.ai/blog/deepswe), which used RL on agent sessions like these, trained on 64 H100 GPUs for six days. Cheap RL results such as [TinyZero](https://github.com/Jiayi-Pan/TinyZero), under $30 for a 3-billion-parameter model, use one short answer per attempt on countdown and multiplication puzzles, a very different scale.

RL is also not the only way forward. The remaining over-edits happen in long sessions: the student learned from the teacher's runs, then drifted in its own. On-policy distillation targets exactly that gap. The student runs its own sessions and the teacher scores every token of them ([Agarwal et al.](https://arxiv.org/abs/2306.13649), [Thinking Machines](https://thinkingmachines.ai/blog/on-policy-distillation/)). Its limit is the teacher: the student can at best match the model with the instruction, which left fixed code alone in 75% of its training tasks. Going beyond the teacher needs a reward for the outcome, which is what RL provides.

## Limits

The experiment was small: 29 held-out tasks and one attempt per task, with the model sampling at the temperature its model card recommends. I measured the noise directly: the same trained model over-edited 8 tasks in one test run and 4 in another. It is one model, one harness and Python projects only, with one training run per setting. I checked that bug fixing did not suffer on these tasks, but not whether general coding ability did.

There is also a quieter effect. Removing the instruction from the teacher's prompt did not remove it from the teacher's own words, which often quoted it: 61 of the 99 training conversations contain *"If the issue is not present (anymore), report that and don't make changes."* The trained models now recite that sentence in about 40% of test runs, although it is no longer in their prompt. It is the same sentence for both versions of a task, so it does not leak the answer. It does show how context distillation works: the model behaves as if it remembers being told.

## Final thoughts

An instruction that lets the agent abstain works immediately, but only while it stays in the prompt. Context distillation builds the behaviour into the model. Here it cut unnecessary edits on already-fixed code from 24 of 29 to between 4 and 8, without costing real bug fixes, but only once the training data was clean. Adding the 22 longest conversations and training further made the model worse, most likely because those examples showed the teacher drifting for many steps before it stopped. That is one run with three changes at once, not a rule: elsewhere, more good runs reliably help coding agents ([SWE-Gym](https://arxiv.org/abs/2412.21139), [SWE-smith](https://arxiv.org/abs/2504.21798)). The model usually knows early that nothing needs changing; what it lacks is the habit of stopping there.

[^recipe]: LoRA ([Hu et al.](https://arxiv.org/abs/2106.09685)) with rank 64 on every linear layer, learning rate 1e-4, two epochs, conversations of up to 49,152 tokens.
[^clean]: The teacher left already-fixed code alone in 53 of 71 runs and fixed 48 of 71 real bugs. Only its correct runs that it also submitted were kept: two of the bug fixes stopped before submitting, which leaves 53 + 46 = 99 conversations. The longest 22 conversations did not fit in GPU memory for this round.
[^lr]: One piece of evidence against the learning rate being the cause: the training loss on the conversations the model had already seen did not rise during the continued training (0.280 → 0.276).
[^probe]: The probe is a logistic regression on the hidden state just before each step. Layer and regularisation were chosen on the training tasks only, and the held-out tasks were scored once.
