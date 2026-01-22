from __future__ import annotations

from flowbook.artifacts.keys import PLAN


def plan_from_two_numbers_op(inputs: dict, store_):
    # inputs["x"], inputs["y"] は artifact key（文字列）として受け取る
    x_key = inputs["x"]
    y_key = inputs["y"]

    # 「2つなら add」：規定のinspect/planner
    plan_config = {
        "steps": [
            {
                "name": "add",
                "op": "add",
                # inputs は書かない（Engineが注入）
                "outputs": ["sum"],
            }
        ]
    }

    store_.put(PLAN, plan_config)
    return {}  # control artifact 固定キーへ書くので outputs不要


def register(registry) -> None:
    registry.register("plan_from_two_numbers", plan_from_two_numbers_op)
