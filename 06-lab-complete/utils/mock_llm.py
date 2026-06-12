"""Offline mock LLM used by the final lab."""
import random
import time

RESPONSES = [
    "Agent production đang hoạt động tốt.",
    "Deployment đưa ứng dụng lên hạ tầng để người dùng có thể truy cập.",
    "Docker đóng gói ứng dụng và dependencies thành một container nhất quán.",
]


def ask(question: str, delay: float = 0.1) -> str:
    time.sleep(delay)
    if "docker" in question.lower():
        return RESPONSES[2]
    if "deploy" in question.lower():
        return RESPONSES[1]
    return random.choice(RESPONSES)

