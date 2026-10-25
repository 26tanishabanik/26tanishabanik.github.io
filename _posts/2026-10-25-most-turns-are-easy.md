---
layout: post
title: "Most Turns Are Easy. The Model Has to Know Which."
subtitle: "A small, open decision model for phone calls in Indian languages. It answers the routine questions in a call on its own and passes the rest to a larger model."
date: 2026-10-25
---

When a caller says "haan ji" after "Shall I start the return?", there is not much to work out. It means yes. A surprising share of a customer-care call is like this. On 6,502 test replies, a model with 2.5 billion parameters was confident enough to decide 84 of every 100 on its own, and it was right on 99.5% of those.

If a voice agent sends every turn to an LLM, each of those easy turns costs a few hundred milliseconds and a paid call. The turns that really are hard get exactly the same treatment: a caller who answers a demo offer with "Haan, par abhi dukaan par bahut bheed hai, shaam ko saat baje karao" (yes, but the shop is packed right now, make it seven this evening), or one who says in the same breath which colour they ordered and which colour arrived.

One way to cut that cost is to put a small model in front, let it take the turns it is sure about and pass the rest on. Cascades and routers of this kind have been studied for general LLM queries, for example in [FrugalGPT](https://arxiv.org/abs/2305.05176) and [RouteLLM](https://arxiv.org/abs/2406.18665). In a phone call the small model has a narrower job: pick one of a few given answers and say how sure it is, which is what decision models such as Jev, Laya and Vega do. It also has to do that in the way people in India actually speak on the phone: Hindi typed in English letters, Tamil with English in the middle of a sentence, a "hello, can you hear me?" in place of an answer.

This post is about the open decision model I built on Sarvam-1 for Indian-language calls, how I tested it and what it does inside a real voice agent today.

* TOC
{:toc}

## The short version

- **I built an open decision model on Sarvam-1 (2.5 billion parameters) for phone calls in 10 Indian languages and English.** On 6,502 test replies it never saw in training, two-thirds of them from call flows it never saw either, it reads 96.3% correctly. When it is confident enough to act alone, which happens for 84 of every 100 replies, it is right 99.5% of the time.
- **It carries over to everyday decision tasks it was not trained for.** On a public set of such tasks translated into 11 Indian languages, it scored 85.5%, the highest of the open models I tested.
- **In front of Sarvam's own conversational LLM, it raises accuracy and removes most of the LLM calls.** On 2,700 test turns the LLM alone got 92.8% right. With this model in front and the hand-off rules chosen on separate calibration calls, accuracy rose to 94.3% and the LLM was needed on only a quarter of turns. One pass of the model takes about 32 milliseconds on a single L4 GPU.

The post follows the order in which things happened: seeing where existing models stand, building the model, testing it, putting it in a voice agent and what I learned along the way.

## How the decision model is used

At each turn the decision model reads the recent conversation, a question such as "Did the caller confirm the delivery address?" and a short list of options (yes, no, the caller asked something else, and so on), and returns one option with a confidence. Above a cutoff the agent acts on it; below it, the turn goes to the LLM, which handles unusual cases better but costs about 0.4 seconds per call in my tests, against a few tens of milliseconds for the small model on a GPU. Released decision models expose the same idea as a calibrated probability, an abstain flag or a probability of acting.

That only works if a confidence of 0.99 actually means "right 99 times in 100". Much of this project was about earning that.

## Where existing models stand

Before building anything, I measured how released decision models, hosted and open, handle Indian languages. I used two public benchmarks, [Belebele](https://arxiv.org/abs/2308.16884) for reading comprehension and [IndicXNLI](https://arxiv.org/abs/2204.08776) for whether one sentence follows from another, and JevBench, a public set of 120 everyday decision tasks (checking an answer against a written policy, rating how complete an answer is, sorting things into levels) that I translated into 11 Indian languages. Results varied a lot from model to model and from language to language, which made it worth asking how far an open model built for Indian-language calls could go.[^bench]

The model this post is about was later run on the same translated tasks without training on any of them, and scored 85.5%.

## Building it on Sarvam-1

The base model is [Sarvam-1](https://huggingface.co/sarvamai/sarvam-1), a 2.5-billion-parameter language model trained heavily on Indian languages. It reads Indian scripts efficiently: on Indian-language text from the FLORES benchmark it needs about 2.1 tokens per word, where Qwen3.5-2B, a general model of similar size, needs about 4.1. A phone bot rereads the conversation at every turn, so this roughly halves the text the model has to process for each decision.

On top of it sits a small decision head. The model reads the conversation, the question and all the possible answers together, scores each answer and separately flags when none of them fits. Only a small fraction of the weights is trained, using the standard technique [LoRA](https://arxiv.org/abs/2106.09685), so most of what Sarvam-1 already knows stays in place.

The call data comes from 12 customer-care call flows, such as blocking a card, returning an order, booking a clinic appointment and repaying a loan. Caller replies for each step were generated directly in each language and labelled again by a second model that did not see the intended answer, and I kept only the replies where both agreed. Every Indian-language reply exists in native script, romanized and code-mixed form. The final training set has about 86,000 examples across 10 Indian languages and English: about 79,000 generated call turns and about 6,500 examples from public Indian-language datasets for intent, inference and abusive language.

Besides the right answer, the model is trained on pairs of near-identical replies where one changed detail flips the answer, on staying consistent when the same sentence is written in another script, on keeping its confidence honest and on the answers of earlier versions of itself.

![Where the decision model sits in a voice agent]({{ site.baseurl }}/assets/img/decision-pipeline.png)

## How I tested it

Four call flows (insurance claims, travel bookings, support for a children's learning app and vehicle servicing) never appear in training, and neither do several families of business rules. I know Hindi, Bengali and Assamese, so I also kept Assamese out of training entirely. That gives a test on a language the model has never seen in a call, and one whose mistakes I can check myself.[^assamese]

Alongside accuracy I tracked **confident mistakes**: wrong answers given with at least 0.95 confidence. In a system that acts on high confidence, these are the errors that are most easily overlooked, so every version was checked to keep them low.

The results below come from three kinds of test: held-out call test sets, built like the training calls but from the flows, rule families and language that training never saw; the translated public benchmark above, from outside this project; and my own live calls to a voice agent built on the model.

## How well it decides

The most common decision in a call is whether the caller's reply answers the bot's question, and which answer it gives. On 6,502 test replies the model gets **96.3%** right, and 95.4% on the 4,289 of them that come from the four unseen flows.

![About 575 test replies per Indian language and 179 in English. The axis starts at 80% so the differences between languages are visible.]({{ site.baseurl }}/assets/img/decision-languages.png)

How a reply is written matters as much as its language. Native-script and code-mixed replies are both read correctly 97.9% of the time, while Hindi typed in English letters ("haan ji, bhej dijiye") is harder at 93.3%, since romanized text has no fixed spelling. Assamese still reaches 89.2%, probably helped by its closeness to Bengali, which uses almost the same script.

The other decisions a voice agent needs:

| Decision (held-out tests) | Examples | Accuracy |
|---|---:|---:|
| Short replies that only make sense with the bot's question (a bare "അതെ", yes, or "नाही पायजे", do not want) | 1,343 | **99.7%** |
| Is the caller talking about something else entirely? | 1,534 | **99.0%** |
| Is this a complaint? (call flow never seen in training) | 235 | **97.4%** |
| Should a person take over? | 1,907 | 94.3% |
| "Yes, but…" replies (a yes with a condition attached) | 700 | 94.3% |
| How urgent is the problem? (fresh set, new settings) | 1,080 | 89.3% |
| Does the caller meet a business rule never seen in training? | 1,011 | 82.4% |

The first three are close to solved. The last two need reasoning about situations the model has not seen.

## Knowing when it is sure

A voice agent also needs to know when to trust an answer. For each kind of question I looked for the lowest confidence at which the model is right at least 99 times in 100, checked statistically on a separate set of calls and then on every test set.[^cutoff] For caller replies that cutoff is 0.987.

![6,502 test replies, sorted from most to least confident. On the 4,289 replies from unseen flows alone, the same cutoff decides 82% of replies at 99.3% accuracy.]({{ site.baseurl }}/assets/img/decision-coverage.png)

Five kinds of question earned a proven cutoff: caller replies, short replies read in context, complaints, off-topic turns and mood. The model decides about 90% of complaint turns alone, but only about 30% of mood turns. Urgency and business rules have no 99% cutoff yet, so under that strict rule they always go to the LLM or a person.

## Next to Sarvam's LLM

I compared a voice agent that sends every turn to `sarvam-105b-conversations`, the version of Sarvam's 105B model tuned for real-time dialogue and voice agents, with one that puts this model first, on 2,700 test turns covering every kind of question.

![2,700 test turns covering every kind of question. The third row was chosen on separate calibration calls and applied once; the fourth was tuned on half of the test turns and scored on the other half.]({{ site.baseurl }}/assets/img/decision-llm.png)

The second row uses only the strict 99% cutoffs. The third picks, for each kind of question, whichever arrangement was most accurate on separate calibration calls: the model alone, the LLM alone, or the model with the LLM taking the turns below a confidence threshold. That lets the model take more turns, including urgency and business rules, where the threshold is set for accuracy instead of for 99%. The LLM received the same conversation, question and options as this model, with no examples, at temperature 0.[^llm] On the replies it decides alone, the model is right 99.4% of the time, against 98.1% for the LLM on the same turns. Across all replies the LLM is slightly ahead (97.2% to 96.2%), which is why the uncertain ones go to it. The LLM is also stronger on the translated everyday decision tasks (95.8% to 87.0%) and on unseen business rules (94.0% to 87.0%). On the turns in this comparison, the small model is stronger at spotting when a caller needs a person (94.7% to 87.7%), at judging urgency (89.0% to 85.5%) and at reading mood (80.7% to 78.0%), and it is far faster. Combining the two beats either one.

![Median time for one pass of this model over the options, against the LLM's median response time over the API in my tests. The accuracy figures in this post average two passes with the options in different orders, which took 1.8 times as long as one pass on my laptop.]({{ site.baseurl }}/assets/img/decision-latency.png)

## In a live call

I also built a generic customer-care voice agent around the model and called it myself: a shopping-app returns desk, a bank card line and a loan repayment line, with the agent working out which one the caller needs. Sarvam's speech-to-text detects the language, this model makes the quick decisions, the use case's written policy decides what is allowed, Sarvam's LLM writes the reply and Sarvam's text-to-speech reads it out. Here is one turn, with the decisions as the agent logged them.

> मैंने एक काजल ऑर्डर किया था पर वो नीले रंग का था पर ये तो काला है। मैंने ये ऑर्डर नहीं किया था।
>
> *Maine ek kajal order kiya tha par vo neele rang ka tha, par ye to kaala hai. Maine ye order nahi kiya tha.*
> (I ordered a kajal and it was blue, but this one is black. This is not what I ordered.)

| Question | Answer | Confidence | Decided by |
|---|---|---:|---|
| Should a person take over? | no | 0.96 | this model |
| Caller's mood | calm | 0.94 | this model |
| What does the caller want? | model's best guess: return | 0.55 | LLM, which chose exchange |
| Which item, and what went wrong? | kajal, wrong item | n/a | LLM |

The model was sure about mood and hand-off and acted on both. It was unsure whether the caller wanted a return or an exchange, which the sentence really does leave open, so the agent passed that question on, and the bot offered to swap the black kajal for the blue one.

## What I learned

### Track confidence as closely as accuracy
{:.no_toc}

Two versions with the same accuracy can behave very differently in a voice agent, depending on how often each is wrong while sure. Confident mistakes caught problems the accuracy numbers did not show at all.

### Learn from earlier models, not from their certainty
{:.no_toc}

Each version also learns from the answers of earlier versions, through [distillation](https://arxiv.org/abs/1503.02531), with the earlier models as teachers. Which teachers to use turned out to matter a lot, because a teacher that is very sure of itself can pass that certainty on, including on the cases it gets wrong. Two training runs on the same data, with different teachers and starting points, show the effect: one learned from more confident earlier versions (average top confidence 0.88 on these questions) and one from calmer ones (0.78).

![Wrong answers given with at least 0.95 confidence, on 1,011 questions about business rules that never appear in training. The calmer teachers gave fewer confident mistakes and slightly higher accuracy.]({{ site.baseurl }}/assets/img/decision-teachers.png)

### Confidence needs enough examples to be tuned
{:.no_toc}

Confidence is rescaled after training, separately for each kind of question, on examples the model has not trained on, and the rescaling is only as good as the number of examples behind it. A kind of question now gets its own adjustment only when it has at least 150 such examples; otherwise it shares one with similar questions. With that rule, on a fresh set of 1,080 urgency questions the model was right 89.3% of the time and made no confident mistakes.

### Set the hand-off rules on the calls you will actually serve
{:.no_toc}

Tuning which questions go to the LLM on calls from the training flows still raised overall accuracy (to 94.3%), but made unseen business rules worse (94.0% to 87.5%). Tuned on calls like the ones being served, it reached about 95% with the LLM on about 22% of turns, and no kind of question got meaningfully worse. A small labelled sample of a team's own calls is worth keeping for exactly this step.

### Live calls show what test sets cannot
{:.no_toc}

Calling the agent myself turned up four situations the test sets did not cover. Callers often say more than the bot asked: in the kajal call, the colour ordered and the colour received came in one sentence, while the model had been trained only to answer the question the bot actually asked. Callers also say things that are neither answers nor off-topic, such as "hello, can you hear me?" or "one minute", and each needs a different response. Routing a caller's first sentence to the right service works best when "something else" is an option the model has properly learned, not a vague fallback. And long descriptions of the options need to be read in full. These four findings became the training data for the next round.

## The next round

The next version was trained on those four patterns, and it improved on all of them.

![Accuracy on the held-out call test sets. Routing covers all test services (on services seen in training it went from 78.7% to 92.5%; on services never seen, from 77.6% to 82.0%). The current model was never trained to tell kinds of non-answer apart, so its 50.5% is a starting point rather than a like-for-like score. Details offered unasked are measured in domains never seen in training. Caller replies stayed at 96.3%.]({{ site.baseurl }}/assets/img/decision-nextround.png)

The jump on non-answers is the largest single gain in the project: the model now tells apart a line check ("can you hear me?"), a request to repeat, a request to wait, a side question and an unclear reply 97.3% of the time.

Before it replaces the current model, its confidence on routing and on whether a caller has given every detail needs to come down, and the hand-off decision, which moved from 94.3% to 93.1%, needs to recover.

## Where it stands

**Working well today**

- Reads 96 of every 100 caller replies correctly, across 10 Indian languages and English, in native script, romanized and code-mixed text.
- Knows when it is sure: it decides most replies on its own at better than 99% accuracy, and passes the rest to the LLM.
- Makes Sarvam's conversational LLM more accurate while taking over most of its calls.
- A few tens of milliseconds per pass of the model on a single GPU.
- The highest score among the open models I tested on translated everyday decision tasks.

**Still growing**

- Open-ended decisions that depend on reading a written policy, where large LLMs are still ahead.
- Decisions that need more reasoning, such as urgency, which are confirmed before acting.
- Romanized text and languages it has never seen.
- Learning from real customer calls at scale, beyond my own test calls.

There are two directions I am most interested in. The first is teaching the model how calls tend to unfold, so it can expect where a conversation is heading instead of judging each turn on its own. The second is sound: right now the model only reads the transcript, so tone of voice, background noise and a second person speaking are lost before it decides.

## Final thoughts

I started out asking how well decision models handle Indian languages, and whether a 2.5-billion-parameter open model built on Sarvam-1 could do this job well for phone calls. The more useful result for me was a different one. Most turns in a call are easy, and a small model can handle them faster and more accurately than a large one, as long as it is honest about the turns that are not easy. Teaching the model to tell those apart mattered more than making it a little more accurate.

[^bench]: For Belebele and IndicXNLI, 200 items per language, comparing each model's Indian-language average with its English score after removing items whose machine translation was broken. For JevBench, the same 1,295 native-script items for every model, keeping a translation only if the right answer did not change; the questions and options stay in English, and each released model was called zero-shot through its own package or API.
[^assamese]: Assamese call turns never appear in training. A short Assamese word list is part of the short-replies-in-context task, and Sarvam-1 itself was not trained on Assamese.
[^cutoff]: "At least 99%" means the 95% lower confidence bound (Clopper–Pearson) on a separate calibration set is at or above 99%. About 300 correct answers in a row are needed before that bound can reach 99%, which is why cutoffs are set per kind of question and not per step of a call.
[^llm]: Every answer the LLM gave was valid. With hand-off rules chosen on calibration calls, 98 turns were gained and 59 lost against the LLM alone (p = 0.002). The "tuned on calls like the test calls" row was chosen on half of the test turns and scored on the other half, then swapped; over three random splits it gave 94.7% to 95.0% accuracy with the LLM on 21% to 23% of turns.
