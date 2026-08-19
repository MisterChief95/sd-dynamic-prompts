from pathlib import Path

import pytest

from sd_dynamic_prompts.prompt_writer import PromptWriter


@pytest.fixture()
def prompt_writer() -> PromptWriter:
    return PromptWriter()


@pytest.fixture()
def populated_prompt_writer() -> PromptWriter:
    prompt_writer = PromptWriter()
    prompt_writer.set_data(
        positive_template="positive",
        negative_template="negative",
        positive_prompts=["positive1", "positive2"],
        negative_prompts=["negative1", "negative2"],
    )
    return prompt_writer


class TestPromptWriter:
    def _write_to_file(self, prompt_writer: PromptWriter, path: Path) -> None:
        # The file is pre-created so a skipped write leaves it empty rather than absent.
        path.touch()
        prompt_writer.write_prompts(path)

    def _checks_writes_empty_file(
        self,
        prompt_writer: PromptWriter,
        path: Path,
    ) -> bool:
        self._write_to_file(prompt_writer, path)
        return path.read_text(encoding="utf-8") == ""

    def test_default_disabled(self, prompt_writer: PromptWriter) -> None:
        assert prompt_writer.enabled is False

    def test_reset(self, prompt_writer: PromptWriter) -> None:
        prompt_writer._already_saved = True
        prompt_writer._positive_template = "positive"
        prompt_writer._negative_template = "negative"
        prompt_writer._positive_prompts = ["positive1", "positive2"]
        prompt_writer._negative_prompts = ["negative1", "negative2"]

        prompt_writer.reset()

        assert prompt_writer._already_saved is False
        assert prompt_writer._positive_template == ""
        assert prompt_writer._negative_template == ""
        assert prompt_writer._positive_prompts == []
        assert prompt_writer._negative_prompts == []

    def test_set_data(self, populated_prompt_writer: PromptWriter) -> None:
        assert populated_prompt_writer._positive_template == "positive"
        assert populated_prompt_writer._negative_template == "negative"
        assert populated_prompt_writer._positive_prompts == ["positive1", "positive2"]
        assert populated_prompt_writer._negative_prompts == ["negative1", "negative2"]

    def test_doesnt_write_when_disabled(
        self,
        populated_prompt_writer: PromptWriter,
        tmp_path: Path,
    ) -> None:
        populated_prompt_writer.enabled = False
        assert self._checks_writes_empty_file(
            populated_prompt_writer,
            tmp_path / "prompts.csv",
        )

    def test_write_prompts(
        self,
        populated_prompt_writer: PromptWriter,
        tmp_path: Path,
    ) -> None:
        populated_prompt_writer.enabled = True

        path = tmp_path / "prompts.csv"
        populated_prompt_writer.write_prompts(path)
        lines = path.read_text(encoding="utf-8").splitlines()

        assert lines == [
            "positive_prompt,negative_prompt",
            "positive,negative",
            "positive1,negative1",
            "positive2,negative2",
        ]

    def test_only_write_once(
        self,
        populated_prompt_writer: PromptWriter,
        tmp_path: Path,
    ) -> None:
        populated_prompt_writer.enabled = True

        self._write_to_file(populated_prompt_writer, tmp_path / "first.csv")
        assert self._checks_writes_empty_file(
            populated_prompt_writer,
            tmp_path / "second.csv",
        )

    def test_writes_after_reset(
        self,
        populated_prompt_writer: PromptWriter,
        tmp_path: Path,
    ) -> None:
        populated_prompt_writer.enabled = True
        self._write_to_file(populated_prompt_writer, tmp_path / "first.csv")

        populated_prompt_writer.reset()

        assert not self._checks_writes_empty_file(
            populated_prompt_writer,
            tmp_path / "second.csv",
        )
