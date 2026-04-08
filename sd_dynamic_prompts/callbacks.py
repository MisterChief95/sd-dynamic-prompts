from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from dynamicprompts.wildcards import WildcardManager
from modules import script_callbacks, shared
from modules.generation_parameters_copypaste import parse_generation_parameters
from modules.script_callbacks import ImageSaveParams

from sd_dynamic_prompts.pnginfo_saver import strip_template_info
from sd_dynamic_prompts.prompt_writer import PromptWriter
from sd_dynamic_prompts.settings import on_ui_settings
from sd_dynamic_prompts.wildcards_tab import initialize as initialize_wildcards_tab

logger = logging.getLogger(__name__)


_ESCAPE_MAP = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "\\": "\\",
}


def _unescape_prompt(text: str) -> str:
    """Decode common escape sequences (\\n, \\t, \\r, \\\\) in a prompt string.

    Only the sequences listed in _ESCAPE_MAP are expanded; all other backslash
    sequences are left untouched so that dynamic-prompts syntax (e.g. wildcard
    paths with backslashes) is not corrupted.
    """

    def replace(m: re.Match) -> str:
        return _ESCAPE_MAP.get(m.group(1), m.group(0))

    return re.sub(r"\\(.)", replace, text)


def register_prompt_writer(prompt_writer: PromptWriter) -> None:
    def on_save(image_save_params: ImageSaveParams) -> None:
        image_name = Path(image_save_params.filename)
        prompt_filename = image_name.with_suffix(".csv")
        prompt_writer.write_prompts(prompt_filename)

    script_callbacks.on_before_image_saved(on_save)


def register_on_infotext_pasted() -> None:
    def on_infotext_pasted(infotext: str, parameters: dict[str, Any]) -> None:
        new_parameters = {}
        if "Prompt" in parameters and "Template:" in parameters["Prompt"]:
            strip_template_info(parameters)
            new_parameters = parse_generation_parameters(parameters["Prompt"])
        elif (
            "Negative prompt" in parameters
            and "Template:" in parameters["Negative prompt"]
        ):
            strip_template_info(parameters)
            new_parameters = parse_generation_parameters(parameters["Negative prompt"])
            new_parameters["Negative prompt"] = new_parameters["Prompt"]
            new_parameters["Prompt"] = parameters["Prompt"]
        parameters.update(new_parameters)

        if getattr(shared.opts, "dp_paste_template_as_prompt", False):
            if "Template" in parameters and parameters["Template"]:
                parameters["Prompt"] = _unescape_prompt(parameters["Template"])
            if "Negative Template" in parameters and parameters["Negative Template"]:
                parameters["Negative prompt"] = _unescape_prompt(
                    parameters["Negative Template"]
                )

    script_callbacks.on_infotext_pasted(on_infotext_pasted)


def register_settings():
    script_callbacks.on_ui_settings(on_ui_settings)


def register_wildcards_tab(wildcard_manager: WildcardManager):
    initialize_wildcards_tab(wildcard_manager)
