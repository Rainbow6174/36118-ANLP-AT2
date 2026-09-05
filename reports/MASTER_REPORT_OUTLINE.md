# AT2 Report Outline

Each role supplies finished text, tables and references for its own section. The data and report coordination role joins the sections at the end and checks that names, numbers and terminology agree.

## 1. Executive Summary

Write this last. Briefly cover the user problem, approach, main verified result, practical value and most important limitation. Use only the locked evaluation results.

## 2. Project Objectives and Scope

- Primary user: customer and social-insights analysts working across Australian, Indian and British English markets
- Supported task: finding sentiment, sarcasm and uncertain cases that need human review
- Research questions and exclusions
- Minimum application and any optional features

## 3. Data Sources and Preparation

Start from `reports/eda/data_section.md`. Include one dataset-size figure and one label-rate figure, then remove any repeated detail if space is tight.

## 4. NLP Methods and Reasons

### 4.1 Sentiment modelling

Describe baselines, the final model, preprocessing, validation choices and enough settings to reproduce the result.

### 4.2 Sarcasm modelling

Describe baselines, the final model, class imbalance, threshold choice and the special handling of sparse Google-positive groups.

### 4.3 Variety modelling and variety-aware routing

Describe the variety classifier, the variety-agnostic control, source-shortcut checks, and the global/oracle/predicted/gated comparison.

## 5. Evaluation Design

Explain metrics, confidence intervals or seeds, per-class/per-variety/per-source checks, confidence, error sampling and the rules for groups with too few positive examples.

## 6. Application and User Interaction

Explain the target workflow, inputs and outputs, confidence and limited-evidence warnings, review queue, export, deployment, privacy and error handling.

## 7. Results and Findings

Use one shared results package. Separate overall results, variety and source results, routing or ablation results, confidence findings and qualitative errors. Do not copy preliminary notebook numbers here as final model results.

## 8. User Study and Revision

Describe participants, tasks, measures, findings, the observed usability problem and the change made afterwards. Keep user testing separate from benchmark model evaluation.

## 9. Outcomes and Value Added

Explain what the variety-aware comparison and analyst review workflow add beyond a generic classifier demo.

## 10. Challenges and Solutions

Each role contributes one specific challenge, the response and the evidence that the response worked. Avoid vague points such as “time was limited.”

## 11. Ethics, Limitations and Responsible Use

Cover dataset representation, source confounding, sparse and imbalanced groups, uncertainty, the ban on treating variety as nationality, privacy and human oversight.

## 12. Recommendations and Next Steps

Only include recommendations that follow from the reported evidence.

## 13. Contributions

Describe completed work using deliverable paths, commits or issues. Do not list planned work as completed.

## References

Each role supplies complete references. The final editor makes the citation style consistent and removes duplicates.

## Appendix

Add repository structure, configuration tables, extended metrics, extra error examples, the user-test instrument and clean-environment instructions if needed.

## Final assembly checks

1. Evaluation supplies the only approved final metrics and figures.
2. Every technical claim has a result, a reference or a clear “interpretation” label.
3. The report, application and poster use the same model names, split names and numbers.
4. Use `en-AU`, `en-IN`, `en-UK`, `validation` and `sarcastic` consistently.
5. Grammar and duplication can be edited during assembly, but technical meaning should not change without checking with the role that produced the result.
