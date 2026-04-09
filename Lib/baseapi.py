import os
import sys
from abc import ABC

from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate

from Lib.configs import DATA_DIR
from Lib.log import logger


class BaseAPI(ABC):

    def __init__(self):
        self.logger = logger

    class _TemplateWrapper:
        """ A template wrapper class hidden internally that does only one thing: provide .format()."""

        def __init__(self, content: str):
            self._content = content

        def format(self, **kwargs) -> str:
            """ Implement the .format() method you want. """
            return self._content.format(**kwargs)

    @staticmethod
    def _get_main_script_name():
        """
        Get the filename of the main execution script (without the extension).
        sys.argv[0] always points to the script that was originally started, regardless of which module the current code is running in.
        """
        try:
            # 1. Get the full path of the main execution script
            script_path = sys.argv[0]

            # 2. Extract the file name from the full path
            script_filename = os.path.basename(script_path)

            # 3. Separate the file name and extension
            script_name, _ = os.path.splitext(script_filename)

            return script_name
        except IndexError as e:
            raise RuntimeError("Unable to get the name of the main execution script, sys.argv[0] does not exist.") from e
        except Exception as e:
            raise RuntimeError(f"An error occurred while getting the name of the main execution script: {e}") from e

    @property
    def module_name(self):
        """Get the module loading path"""
        module_name = self.__module__.split(".")[-1]
        if module_name == "__main__":
            return self._get_main_script_name()
        else:
            return module_name

    def _get_data_dir_candidates(self):
        candidates = [os.path.join(DATA_DIR, self.module_name)]
        explicit_candidates = getattr(self, "DATA_DIR_CANDIDATES", None) or []
        for candidate in explicit_candidates:
            candidates.append(os.path.join(DATA_DIR, candidate))
        module_parts = self.__module__.split(".")
        if len(module_parts) >= 3 and module_parts[0] == "PLAYBOOKS":
            prefix = module_parts[1].title()
            candidates.append(os.path.join(DATA_DIR, f"{prefix}_{self.module_name}"))
        deduped = []
        for candidate in candidates:
            if candidate not in deduped:
                deduped.append(candidate)
        return deduped

    def _get_md_file_path(self, filename: str, lang=None) -> str:
        """
        Get the file path based on the workbook name.
        """

        if os.path.isfile(filename):  # "/root/asf/ES-Rule-21-Phishing_user_report_mail/senior_phishing_expert.md"
            template_path = filename
        else:
            if filename.endswith('.md'):  # "senior_phishing_expert.md"
                fname = filename
            else:
                if lang is not None:
                    fname = f"{filename}_{lang}.md"  # "senior_phishing_expert_en"
                else:
                    fname = f"{filename}.md"  # "senior_phishing_expert"

            if os.path.isfile(os.path.join(DATA_DIR, fname)):  # "ES-Rule-21-Phishing_user_report_mail/senior_phishing_expert.md"
                template_path = os.path.join(DATA_DIR, fname)
            else:
                template_path = None
                for candidate_dir in self._get_data_dir_candidates():
                    candidate_path = os.path.join(candidate_dir, fname)
                    if os.path.isfile(candidate_path):
                        template_path = candidate_path
                        break
                if template_path is None:
                    template_path = os.path.join(DATA_DIR, self.module_name, fname)

        return template_path

    def _get_file_path(self, filename: str):
        """
        Get the file path based on the workbook name.
        """

        if os.path.isfile(filename):  # "/root/asf/ES-Rule-21-Phishing_user_report_mail/senior_phishing_expert.md"
            return filename
        else:
            for candidate_dir in self._get_data_dir_candidates():
                template_path = os.path.join(candidate_dir, filename)
                if os.path.isfile(template_path):
                    return template_path
            raise Exception("File not exist")

    def load_markdown_template(self, filename: str) -> _TemplateWrapper:
        """
        Read the content according to the workbook name and return an object that supports .format().
        """

        template_path = self._get_md_file_path(filename)
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Return an instance of an inner nested class
                return self._TemplateWrapper(content)

        except Exception as e:
            logger.warning(f"Failed to load prompt template {template_path}: {str(e)}")
            raise e

    def load_system_prompt_template(self, filename, lang=None):
        """Load system prompt template"""
        template_path = self._get_md_file_path(filename, lang=lang)
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                system_prompt_template: SystemMessagePromptTemplate = SystemMessagePromptTemplate.from_template(f.read())
                logger.debug(f"Loaded system prompt template from: {template_path}")
                return system_prompt_template
        except Exception as e:
            logger.warning(f"Failed to load prompt template {template_path}: {str(e)}")
            raise e

    def load_human_prompt_template(self, filename, lang=None):
        template_path = self._get_md_file_path(filename, lang=lang)
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                human_prompt_template: HumanMessagePromptTemplate = HumanMessagePromptTemplate.from_template(f.read())
                logger.debug(f"Loaded human prompt template from: {template_path}")
                return human_prompt_template
        except Exception as e:
            logger.warning(f"Failed to load prompt template {template_path}: {str(e)}")
            raise e

    def run(self):
        raise NotImplementedError
