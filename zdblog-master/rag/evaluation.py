def evaluate_cases(cases, retrieve, k):
    recall = hit_rate = reciprocal = positive = negative = negative_ok = 0
    details = []
    for case in cases:
        ids = list(dict.fromkeys(hit['article_id'] for hit in retrieve(case['q'], top_k=k)))[:k]
        expected = set(case.get('expect', []))
        if expected:
            positive += 1
            matched = expected.intersection(ids)
            recall += len(matched) / len(expected)
            hit_rate += bool(matched)
            rank = next((rank for rank, key in enumerate(ids, 1) if key in expected), None)
            reciprocal += 1 / rank if rank else 0
        else:
            negative += 1
            negative_ok += not ids
        details.append({'q': case['q'], 'retrieved': ids, 'expected': sorted(expected)})
    return {'k': k, 'positive_cases': positive, 'negative_cases': negative,
            'recall': recall / positive if positive else None,
            'hit_rate': hit_rate / positive if positive else None,
            'mrr': reciprocal / positive if positive else None,
            'negative_accuracy': negative_ok / negative if negative else None, 'details': details}
