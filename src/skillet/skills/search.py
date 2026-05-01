from fuzzywuzzy import fuzz


def search_skills(skills: list[dict], query: str, threshold: int = 60) -> list[dict]:
    """Fuzzy search skills by name or description."""
    q = query.lower()
    results = []

    for skill in skills:
        name_score = fuzz.partial_ratio(q, skill["name"].lower())
        desc_score = fuzz.partial_ratio(q, skill["description"].lower()) if skill["description"] else 0

        best_score = max(name_score, desc_score)

        if best_score >= threshold:
            results.append({
                **skill,
                "score": best_score,
            })

    return sorted(results, key=lambda s: s["score"], reverse=True)


def search_by_name(skills: list[dict], name: str) -> dict | None:
    """Exact or fuzzy match by skill name."""
    best_match = None
    best_score = 0

    for skill in skills:
        score = fuzz.ratio(name.lower(), skill["name"].lower())
        if score > best_score:
            best_score = score
            best_match = skill

    return best_match if best_score >= 80 else None
