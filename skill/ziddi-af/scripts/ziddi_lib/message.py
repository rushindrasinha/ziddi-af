"""One short, plain message per chase. Answer first, one next action, one low-effort reply."""
import re


def build_message(item, max_words=60):
    title = re.sub(r"\s+", " ", item["title"]).strip()[:70]
    state = (item.get("msg_state") or re.sub(r"\s+", " ", item["state"]).split(". ")[0])[:160]
    nxt = item["steps"][0] if item.get("steps") else (item.get("recommendation") or "")
    lines = [f"[{item['mtype']}] {title}", f"State: {state}", f"Next: {nxt[:140]}"]
    if item.get("default_note"):
        lines.append(item["default_note"][:140])
    lines.append(f"Reply: {item['reply']}" if item.get("reply") else "No reply needed.")
    msg = "\n".join(lines)
    return msg


def lint(msg, max_words=60):
    probs = []
    words = len(msg.split())
    if words > max_words + 10:
        probs.append(f"{words} words (target about {max_words})")
    if "—" in msg or "–" in msg:
        probs.append("em/en dash")
    if "|" in msg:
        probs.append("table pipe")
    if re.search(r"just checking in|friendly reminder|any update|circling back|\bbump\b|touching base", msg, re.I):
        probs.append("bare-reminder language")
    return words, probs
