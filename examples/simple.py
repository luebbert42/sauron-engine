from typing import Tuple
from sauron.rule_engine import RuleEngine

engine = RuleEngine()


@engine.condition("First Condition")
def first_condition(session,lower_number: int = 10, greater_number: int = 20) -> Tuple:
    """
    Checks if first number is lower than the first
    - lower_number: Number expected to be low
    - higher_number: Number expected to be high
    """
    session["lower_number"] = lower_number
    session["greater_number"] = greater_number
    return lower_number < greater_number


@engine.condition()
def second_condition(session):
    """
    Takes no argument and always returns True
    """
    return True


@engine.action("The Action", requires_var=["lower_number","greater_number"])
def print_the_equation(session) -> None:
    """
    Prints a statement Asserting that the first number is lower than the second number
    - lower_number: Number expected to be low
    - higher_number: Number expected to be high
    """
    lower_number = session["lower_number"]
    greater_number = session["greater_number"]
    print(f"{lower_number} < {greater_number} = {lower_number < greater_number}")


rule = {
    "conditions": [
        {
            "name": "first_condition",
            "args": {"lower_number": 3, "greater_number": 10},
        }
    ],
    "actions": [
        {
            "name": "print_the_equation"
        }
    ],
}

rule2 = {
    "conditions": [
        {
            "name": "first_condition",
            "args": {"lower_number": 30, "greater_number": -20},
        }
    ],
    "actions": [
        {
            "name": "print_the_equation"
        }
    ],
}


engine.run(rule)
engine.run(rule2)
