from unittest.mock import Mock

from dynamicprompts.generators import RandomPromptGenerator

from sd_dynamic_prompts.frozenprompt_generator import FrozenPromptGenerator

TEMPLATE = "{A|B|C|D|E|F|G|H|I|J|K}"


def test_repeats_correctly():
    """A single draw from the wrapped generator is repeated num_images times."""
    generator = FrozenPromptGenerator(
        RandomPromptGenerator(unlink_seed_from_prompt=True),
    )
    prompts = generator.generate(TEMPLATE, 40)

    assert len(prompts) == 40
    assert len(set(prompts)) == 1


def test_redraws_on_each_call():
    """Each generate() call draws afresh, so batches are not frozen to each other."""
    # The wrapped generator is mocked out: whether two *random* draws happen to
    # differ is a 1-in-11 coin flip, which is not what this test is about.
    inner = Mock()
    inner.generate.side_effect = [["first"], ["second"]]
    generator = FrozenPromptGenerator(inner)

    assert generator.generate(TEMPLATE, 40) == ["first"] * 40
    assert generator.generate(TEMPLATE, 40) == ["second"] * 40

    assert inner.generate.call_count == 2
    inner.generate.assert_called_with(TEMPLATE, 1)
