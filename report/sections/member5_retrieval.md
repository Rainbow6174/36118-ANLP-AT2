# Retrieval and Search (Member 5)

## Purpose

In this project, CrisisLens sorts each new message into one of ten humanitarian boards, while a board label alone gives the user little context about similar situations. The retrieval component adds this context through two functions, with similarity kept separate from classification and fact checking:

- **Related reports (`retrieve()`):** earlier reports describing the same type of need, damage or situation as a new message.
- **Keyword search (`search()`):** reports containing the words a user types, with filters for board, source, status, location and posting date.

Both functions group near-identical messages under one result, so that repeated messages do not fill the results.

## Text Preparation

One cleaning rule is applied to the 76,484 HumAID messages (Alam et al., 2021) before ranking and duplicate grouping, namely repairing broken emoji characters and HTML entities, lowercasing, removing retweet markers, links and @usernames, keeping hashtag words without the "#" and collapsing repeated spaces. The original text is kept separately for display. For the evaluation, the index holds only the training and validation messages (61,324), so that no test query is part of the messages it searches.

## Methods

**Related reports: TF-IDF and semantic retrieval**

- **TF-IDF:** weights each word by how rare it is, meaning that rare words shared with the query raise the similarity the most. Two settings were compared on 10 tuning queries, and the unigram setting was adopted, as adding two-word pairs increased the vocabulary more than five times (20,242 to 113,949 words) for a small gain in Precision@10 (0.63 to 0.65).
- **Semantic retrieval:** represents each message as a sentence embedding, meaning that messages with a similar meaning are placed close together even when they share few words (Reimers & Gurevych, 2019). The compact all-MiniLM-L6-v2 model (Wang et al., 2020) was adopted, as it encodes about five times more sentences per second than all-mpnet-base-v2 with an average benchmark score only 1.5 points lower (Sentence Transformers, n.d.), suiting an application that runs on a CPU.

**Keyword search: TF-IDF word matching**

`search()` is designed for keyword searching, where a user types a specific place, event or name and expects messages containing it. Therefore, TF-IDF word matching is adopted, as lexical methods find passages about rare names more reliably than dense sentence models (Sciavolino et al., 2021), and keyword lists remain a common way of collecting crisis messages (Olteanu et al., 2014). The search index keeps every word, meaning that a name appearing in only one message can still be found.

**Duplicate grouping**

A result is grouped under a higher-ranked result when their TF-IDF cosine similarity reaches 0.90, with the grouped messages listed under the result rather than removed.

## Evaluation Design

| Group | Queries | Source | Use |
| --- | --- | --- | --- |
| Tuning | 10 | Validation tweets, one per label | Selecting the TF-IDF setting |
| Final original | 20 | Test tweets, two per label | Comparing both methods for `retrieve()` |
| Final paraphrased | 10 | One rewording of an original query per label | Testing matching by meaning |
| Final search | 9 | Short keyword searches, three with a filter | Measuring the precision of `search()` |

- **Relevance judging:** a returned message was judged relevant when it describes the same type of need, damage or situation as the query, or, for a search, when it is about the searched topic. The top 20 results of both methods were judged together in random order without the method name, resulting in 1,427 judgements (163 for tuning and 1,264 for the final evaluation).
- **Measures:** Precision@5 is the main measure, as users are expected to read only the first few related reports, supported by Precision@10 and pooled Recall@5 and @10. The mean query time should remain within 200 ms. These measures were set before any final result was seen.

## Results

**Related reports: `retrieve()`**

| Method | Precision@5 | Precision@10 | Pooled Recall@5 | Pooled Recall@10 | Mean query time (ms) |
| --- | --- | --- | --- | --- | --- |
| TF-IDF (unigram) | 0.607 | 0.577 | 0.161 | 0.269 | 28.1 |
| Semantic | 0.800 | 0.773 | 0.191 | 0.354 | 34.0 |

Based on the table, semantic retrieval records a higher value on every measure, with Precision@5 rising from 0.607 to 0.800. The gap widens on the ten paraphrased queries (0.82 against 0.52), as TF-IDF depends on shared words. Semantic retrieval also records an equal or higher Precision@5 in nine of the ten categories, with the largest gain in requests or urgent needs (0.40 to 0.93). Therefore, semantic retrieval is selected for `retrieve()`, answering well within 200 ms (34.0 ms).

**Keyword search: `search()`**

- **Keyword searches:** `search()` reaches a mean Precision@5 of 0.756 and Precision@10 of 0.733 on the nine searches. "clean water needed" and "missing child" record only 0.2, as TF-IDF also ranks messages sharing one common word, such as "needed".
- **Name searches:** TF-IDF returns every message containing the searched name (Name found@10 of 1.00 for names in 1 to over 100 messages), while semantic retrieval finds only 31% to 60% of them, supporting the choice of TF-IDF for keyword searching.

**Duplicates, filters and cost**

- **Duplicates:** all 90 test copies were caught at every threshold from 0.80 to 0.95, and grouping raised the distinct results in the top 10 from 7 to 10 for both methods. TF-IDF found existing copies in the top 5 for all 52 queries, against 94.2% for semantic retrieval.
- **Filters:** all 29 filter checks passed.
- **Cost:** the larger costs of semantic retrieval occur once rather than per query, with its index taking around 2 minutes to build (94.2 MB against 14.4 MB) and the model 8.1 seconds to load.

## Conclusion

Semantic retrieval with all-MiniLM-L6-v2 was selected for `retrieve()` (Precision@5 of 0.800 against 0.607), while `search()` adopts TF-IDF word matching (Precision@5 of 0.756) and returns every message containing a searched name.

Limitations and future work:

- **Small query set:** only three retrieval queries per category were judged, so category results are indicative, and queries from the user study could be added.
- **One general-purpose model:** only one compact model without crisis-specific training was tested, and the CrisisTransformers sentence encoders (Lamsal et al., 2024) could be compared under the same protocol.
- **Word matching in `search()`:** `search()` matches whole words only, and combining keyword and semantic scores (Bruch et al., 2023) could improve searches describing a topic.

The evaluation is in `notebooks/member5/retrieval_experiments.ipynb`, and the setup and usage are in `models/retrieval/README.md`.

## References

Alam, F., Qazi, U., Imran, M., & Ofli, F. (2021). HumAID: Human-annotated disaster incidents data from Twitter with deep learning benchmarks. *Proceedings of the International AAAI Conference on Web and Social Media, 15*(1), 933–942. https://doi.org/10.1609/icwsm.v15i1.18116

Bruch, S., Gai, S., & Ingber, A. (2023). An analysis of fusion functions for hybrid retrieval. *ACM Transactions on Information Systems, 42*(1), Article 20. https://doi.org/10.1145/3596512

Lamsal, R., Read, M. R., & Karunasekera, S. (2024). CrisisTransformers: Pre-trained language models and sentence encoders for crisis-related social media texts. *Knowledge-Based Systems, 296*, 111916. https://doi.org/10.1016/j.knosys.2024.111916

Olteanu, A., Castillo, C., Diaz, F., & Vieweg, S. (2014). CrisisLex: A lexicon for collecting and filtering microblogged communications in crises. *Proceedings of the International AAAI Conference on Web and Social Media, 8*(1), 376–385. https://doi.org/10.1609/icwsm.v8i1.14538

Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. In *Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing and the 9th International Joint Conference on Natural Language Processing* (pp. 3982–3992). Association for Computational Linguistics. https://doi.org/10.18653/v1/D19-1410

Sciavolino, C., Zhong, Z., Lee, J., & Chen, D. (2021). Simple entity-centric questions challenge dense retrievers. In *Proceedings of the 2021 Conference on Empirical Methods in Natural Language Processing* (pp. 6138–6148). Association for Computational Linguistics. https://doi.org/10.18653/v1/2021.emnlp-main.496

Sentence Transformers. (n.d.). *Pretrained models*. Retrieved October 3, 2026, from https://www.sbert.net/docs/sentence_transformer/pretrained_models.html

Wang, W., Wei, F., Dong, L., Bao, H., Yang, N., & Zhou, M. (2020). MiniLM: Deep self-attention distillation for task-agnostic compression of pre-trained transformers. *Advances in Neural Information Processing Systems, 33*, 5776–5788.
