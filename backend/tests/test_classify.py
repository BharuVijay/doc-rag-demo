from app.classify import is_comparative


def test_comparative_questions_detected():
    assert is_comparative("Quelle est la différence de franchise entre auto et habitation ?")
    assert is_comparative("Comparez le délai de déclaration pour l'auto et l'habitation.")


def test_single_fact_questions_not_flagged():
    assert not is_comparative("Quelle est la franchise dégât des eaux ?")
    assert not is_comparative("Quel est le délai pour déclarer un sinistre auto ?")
