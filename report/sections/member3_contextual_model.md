# Member 3: Contextual Model — Transformer Fine-tuning, Calibration and Cross-event Evaluation


## 5.2 Contextual Model: Transformer Fine-tuning


We fine-tuned a contextual Transformer to classify each crisis message into the ten HumAID humanitarian categories. Because a triage tool must act on its own predictions, this component goes beyond accuracy: it also owns confidence calibration and a selective-prediction layer that routes low-confidence messages to human review.


### 5.2.1 Model choice and training


Two encoders were compared: DistilBERT, a compact general encoder, and Twitter-RoBERTa (`cardiffnlp/twitter-roberta-base`), pretrained on tweets and therefore matched to the social-media domain. Both were fine-tuned for five epochs (batch size 32, learning rate 2e-5, maximum length 128) on the official HumAID split, with macro-F1 as the primary metric because the label distribution is heavily skewed. Twitter-RoBERTa was the most accurate at a macro-F1 of 0.762, but only about one point above DistilBERT (0.755), and the gap sits close to the seed-to-seed range (two seeds, mean 0.764, range 0.004). Twitter-RoBERTa also costs roughly twice the training time and inference latency.


### 5.2.2 Class imbalance


The smallest class, `missing_or_found_people`, is under one percent of the data, so we tested class weighting and focal loss against plain fine-tuning. A pre-registered go/no-go rule was fixed before running: adopt an imbalance method as final only if it raised F1 on the three smallest classes without lowering overall macro-F1 by more than one point. Neither method met the bar, so plain fine-tuning is the final configuration and the comparison is reported as an honest negative result. The methods did raise minority-class recall (for example `requests_or_urgent_needs` recall rose from 0.54 to about 0.72) at a cost in precision, which is why F1 did not improve.


### 5.2.3 Calibration


A model can be accurate yet overconfident, reporting high probabilities that do not match how often it is right. We applied temperature scaling, fitting a single scalar T on the validation logits and never on test. On the seen test set, temperature scaling improved calibration for both models (Twitter-RoBERTa ECE fell from 0.093 to 0.035; DistilBERT from 0.046 to 0.026). Confidence is defined as the maximum calibrated class probability. Figure 1 shows the reliability diagram after scaling.


*Figure 1: Reliability diagram on the seen test set after temperature scaling (Twitter-RoBERTa).*


### 5.2.4 Selective prediction and human review


Calibrated confidence drives a review threshold tau, chosen on validation for a five percent target error on auto-accepted messages. Messages above tau are auto-sorted; the rest are flagged needs_review and sent to a human queue. At the operating point the model auto-accepts about 45 percent of seen-test messages at a 4.5 percent error rate, sending the remaining 55 percent to review. Figure 2 shows the coverage-risk trade-off that sets this operating point.


*Figure 2: Coverage-risk curve. As the review threshold rises, auto-accept coverage falls and the error rate of the auto-accepted set falls.*


### 5.2.5 Cross-event generalisation under distribution shift


The real test is a disaster the model has never seen. We retrained each encoder with one event, `cyclone_idai_2019`, fully removed and evaluated on it. Accuracy fell by a similar, modest amount for both models (Twitter-RoBERTa 0.762 to 0.718; DistilBERT 0.755 to 0.697). The more revealing finding is about confidence, and here the two models behave differently. Table 1 gives the per-class picture for the analysis model, and Table 2 contrasts calibration and selective prediction under shift.


Whether temperature scaling transfers under shift depends on how much rescaling it applies. Twitter-RoBERTa’s larger temperature (T = 1.35) over-corrects on the unseen event, where the model was not overconfident to begin with, so its ECE worsens from 0.041 to 0.061. DistilBERT’s gentler temperature (T = 1.10) still improves calibration on the unseen event (ECE 0.047 to 0.030). The lesson is that calibration cannot be assumed to transfer; it is model-dependent.


The selective-prediction layer inherits this difference. Twitter-RoBERTa becomes conservative under shift, auto-accepting only 37 percent of messages but at a very low 1 percent error. DistilBERT keeps a higher coverage of 58 percent, but its error on the auto-accepted set drifts to 5.3 percent, just above the 5 percent target. So the frozen threshold is a backstop, not a guarantee: under a new disaster the deployed model handles more messages automatically but with a thinner safety margin, which is why the human-review queue and periodic re-calibration matter.


*Table 1: Seen versus unseen (held-out cyclone_idai_2019) per-class F1, Twitter-RoBERTa. Positive drop means performance fell on the unseen event.*


*Table 2: Calibration and selective prediction under distribution shift, analysis model versus deployment model.*


### 5.2.6 Deployment choice


Because the app runs on limited free-tier resources, the deployed model is DistilBERT with its own fitted temperature (T = 1.10) and threshold (tau = 0.887); Twitter-RoBERTa is kept as the report's analysis model. DistilBERT loses about one macro-F1 point, is itself well calibrated, and roughly halves cost, which is the right trade for an interactive tool. The trade has a cost: under distribution shift DistilBERT’s auto-accepted error can drift just over the target (5.3 percent on the unseen event), so deployment should monitor the live error rate and re-calibrate the temperature and threshold as new events arrive.


## Challenges (Member 3 contributions)


Severe class imbalance. The smallest class is under one percent of the data. We pre-registered a go/no-go rule, tested class weighting and focal loss, and when neither improved minority-class F1 we kept plain fine-tuning and reported it as an honest negative result rather than tuning until a method looked favourable.


Calibration that breaks under distribution shift. A temperature fitted on seen data over-corrected on the unseen event and worsened calibration. Rather than trust calibration alone, we let the frozen selective-prediction threshold cap the auto-accepted error by routing more messages to human review.


Reproducibility across notebooks. Early figures were computed under different random seeds in different notebooks, which gave inconsistent headline numbers. We fixed a single seed-42 canonical set and recomputed every reported figure from the saved logits, with no retraining.


Cost versus accuracy for deployment. The most accurate model (Twitter-RoBERTa) is roughly twice the cost and does not fit comfortably on free-tier resources. We deploy DistilBERT with its own fitted temperature and threshold, accepting about a one-point macro-F1 loss for a well-calibrated, cheaper model.


No ideal unseen-event proxy in the available data. The 13-event subset used does not contain the intended flood proxy, so we held out `cyclone_idai_2019` as the closest available unseen event and flag single-event evaluation as a limitation.


## Ethical Considerations (Member 3 contributions)


CrisisLens is built to help responders prioritise humanitarian information more quickly, which speaks to the principle of human, societal and environmental wellbeing. It is designed around human-centred values: the model suggests how to sort a message and never decides a response action or replaces an emergency responder. This is enforced by a human-in-the-loop design, in which any message the model is unsure about is flagged `needs_review` and routed to a person who can override it. That routing is also the project's main answer to contestability, although an explicit user-facing way to challenge a decision is owned by M6.


Reliability and safety are the core of the contextual model's contribution. Confidence is calibrated, the review threshold is set to a target error rate, and the model is tested on a disaster it has never seen. Because calibration does not transfer under distribution shift, it is the frozen review threshold, rather than the confidence score alone, that keeps the auto-accepted error under target, by sending more messages to human review. For transparency and explainability, the application shows a confidence indicator and whether a message was auto-sorted or sent for review, and the methods, seeds, temperature and threshold are recorded in metadata.json. For accountability, every prediction carries a model version and fixed thresholds that give an audit trail, and `needs_review` being false means only that the model is relatively confident, never that a post has been verified as true. (Organisational accountability for acting on the outputs sits with the deploying body and is to be described by the team.)


Fairness is treated honestly rather than assumed. Because rare classes such as `missing_or_found_people` and `requests_or_urgent_needs` are the ones a responder can least afford to miss, we report per-class precision, recall and F1 instead of accuracy alone, and we tested class weighting and focal loss and found plainly that neither improved minority-class F1. Fairness across dialects and regions has not yet been evaluated and is a known limitation. On privacy protection and security, the classifier only predicts and never writes to the database, and the live disaster demo posts are illustrative and are not retained as a benchmark; wider data-collection and storage safeguards are shared with M1 and M4.


## Recommendations (Member 3 contributions)


- Distribution-shift evidence is from one held-out event; add a second event (for example srilanka_floods_2017) to confirm robustness.


- Monitor the auto-accepted error rate in deployment and re-fit the temperature and review threshold per new event, since the frozen threshold can drift over target under distribution shift.


- Explore per-class thresholds and calibration methods that are more robust to shift.
