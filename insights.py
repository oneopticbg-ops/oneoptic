"""Анализ: топ постове на профила ни + бенчмарк на конкурентни оптики чрез Business Discovery API."""
import os, json, requests
G = "https://graph.facebook.com/v26.0"
TOK, UID = os.environ["IG_TOKEN"], os.environ["IG_USER_ID"]
COMP = [c.strip() for c in os.environ.get(
    "COMPETITORS", "jimmyfairly,warbyparker,aceandtate,silhouetteeyewear,eyerim.eyewear").split(",") if c.strip()]

def get(path, **p):
    p["access_token"] = TOK
    return requests.get(f"{G}/{path}", params=p, timeout=60).json()

def own():
    me = get(UID, fields="followers_count")
    followers = max(me.get("followers_count", 1), 1)
    media = get(f"{UID}/media", fields="id,caption,media_type,permalink,timestamp,like_count,comments_count", limit=50).get("data", [])
    out = []
    for m in media:
        ins = get(f"{m['id']}/insights", metric="reach,saved,shares,total_interactions").get("data", [])
        v = {i["name"]: i["values"][0]["value"] for i in ins if i.get("values")}
        reach = v.get("reach") or 0
        inter = (m.get("like_count", 0) + 3 * m.get("comments_count", 0) + 4 * v.get("saved", 0) + 5 * v.get("shares", 0))
        m.update(v); m["score"] = round(inter / (reach or followers), 4)
        out.append(m)
    return sorted(out, key=lambda x: x["score"], reverse=True)

def competitors():
    res = []
    for u in COMP:
        f = f"business_discovery.username({u}){{followers_count,media.limit(30){{caption,like_count,comments_count,media_type,permalink,timestamp}}}}"
        d = get(UID, fields=f).get("business_discovery")
        if not d or not d.get("media", {}).get("data"):
            print("пропуснат (няма достъп/данни):", u); continue
        posts = d["media"]["data"]; fol = max(d["followers_count"], 1)
        for p in posts: p["er"] = round((p.get("like_count", 0) + p.get("comments_count", 0)) / fol, 5)
        er = sum(p["er"] for p in posts) / len(posts)
        res.append({"username": u, "followers": fol, "avg_er": round(er, 5),
                    "top_posts": sorted(posts, key=lambda p: p["er"], reverse=True)[:6]})
    return sorted(res, key=lambda x: x["avg_er"], reverse=True)

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    data = {"own_top": own()[:10], "competitors": competitors()}
    json.dump(data, open("data/insights.json", "w"), ensure_ascii=False, indent=1)
    lines = ["# Класация\n", "## Конкуренти по ангажираност (лайкове+коментари / последователи)"]
    lines += [f"- @{c['username']}: {c['avg_er']*100:.2f}% ({c['followers']} посл.)" for c in data["competitors"]]
    lines += ["\n## Най-добри наши постове"] + [f"- {p['score']} {p['media_type']} {p['permalink']}" for p in data["own_top"]]
    open("data/report.md", "w").write("\n".join(lines)); print("\n".join(lines))
