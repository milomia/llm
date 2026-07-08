#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watsonx_ai.foundation_models.prompts import PromptTemplate
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes


class TestPromptTemplateE2E:
    check_value_error_message = "ERROR: Value it is NOT the same!"
    prompt_list_is_empty_message = "INFO: Prompt list is empty!"
    update_error_message = "ERROR: Name it is not updated!"
    nothing_to_unlock_message = "INFO: There is not any prompt to unlock!"
    lock_changed_error_message = "ERROR: Lock did not changed!"
    nothing_to_lock_message = "INFO: There is not any prompt to unlock!"
    prompt_list_is_not_empty_error_message = "ERROR: list it is not empty"
    prompt_name = "Testing Prompt - TG"

    def test_01_e2e_create_prompt_and_check_values(self, set_up_prompt_template_manager):
        instruction = "Write a summary"
        input_prefix = "Text"
        output_prefix = "Summary"
        input_text = "Bob has a dog"
        examples = [["Text1", "Summary1"]]

        prompt_template = PromptTemplate(name=self.prompt_name,
                                         model_id=ModelTypes.FLAN_UL2,
                                         input_text=input_text,
                                         instruction=instruction,
                                         input_prefix=input_prefix,
                                         output_prefix=output_prefix,
                                         examples=examples)

        set_up_prompt_template_manager.store_prompt(prompt_template)

        assert prompt_template.name == self.prompt_name, self.check_value_error_message
        assert prompt_template.instruction == instruction, self.check_value_error_message
        assert prompt_template.input_prefix == input_prefix, self.check_value_error_message
        assert prompt_template.input_text == input_text, self.check_value_error_message
        assert prompt_template.output_prefix == output_prefix, self.check_value_error_message
        assert prompt_template.examples == examples, self.check_value_error_message

    def test_02_e2e_edit_existing_prompt(self, set_up_prompt_template_manager):
        new_name = "New Test Template Name - TG"
        new_instruction = "Updated Write a summary"
        new_input_prefix = "Updated Text"
        new_output_prefix = "Updated Summary"
        new_input_text = "Updated Input Text"
        new_examples = [["Updated Text - 1", "Updated Summary - 1"],
                        ["Updated Text - 2", "Updated Summary - 2"]]
        first_id_element = set_up_prompt_template_manager.list()['ID'][0]
        list_of_prompts = set_up_prompt_template_manager.list()

        if len(list_of_prompts) == 0:
            raise Exception(self.prompt_list_is_empty_message)

        loaded_old_prompt = set_up_prompt_template_manager.load_prompt(first_id_element)
        loaded_old_prompt.name = new_name
        loaded_old_prompt.instruction = new_instruction
        loaded_old_prompt.input_prefix = new_input_prefix
        loaded_old_prompt.output_prefix = new_output_prefix
        loaded_old_prompt.input_text = new_input_text
        loaded_old_prompt.examples = new_examples

        set_up_prompt_template_manager.update_prompt(first_id_element, loaded_old_prompt)

        loaded_updated_prompt = set_up_prompt_template_manager.load_prompt(first_id_element)

        assert loaded_updated_prompt.name == new_name, self.update_error_message
        assert loaded_updated_prompt.instruction == new_instruction, self.update_error_message
        assert loaded_updated_prompt.input_prefix == new_input_prefix, self.update_error_message
        assert loaded_updated_prompt.output_prefix == new_output_prefix, self.update_error_message
        assert loaded_updated_prompt.input_text == new_input_text, self.update_error_message
        assert loaded_updated_prompt.examples == new_examples, self.update_error_message

    def test_03_e2e_unlock_prompts(self, set_up_prompt_template_manager):
        list_of_prompts = set_up_prompt_template_manager.list()
        index_of_prompt_in_list = 0

        if len(list_of_prompts) == 0:
            raise Exception(self.prompt_list_is_empty_message)

        for _ in range(len(list_of_prompts)):
            first_prompt_id = set_up_prompt_template_manager.list()['ID'][index_of_prompt_in_list]
            lock_state = set_up_prompt_template_manager.get_lock(first_prompt_id)
            index_of_prompt_in_list += 1

            if lock_state["locked"]:
                set_up_prompt_template_manager.unlock(first_prompt_id)
                lock_state = set_up_prompt_template_manager.get_lock(first_prompt_id)

                assert not lock_state["locked"], self.lock_changed_error_message
            else:
                print(self.nothing_to_unlock_message)

    def test_04_e2e_lock_prompts(self, set_up_prompt_template_manager):
        list_of_prompts = set_up_prompt_template_manager.list()
        index_of_prompt_in_list = 0

        if len(list_of_prompts) == 0:
            raise Exception(self.prompt_list_is_empty_message)

        for _ in range(len(list_of_prompts)):
            first_prompt_id = set_up_prompt_template_manager.list()['ID'][index_of_prompt_in_list]
            lock_state = set_up_prompt_template_manager.get_lock(first_prompt_id)
            index_of_prompt_in_list += 1

            if not lock_state["locked"]:
                set_up_prompt_template_manager.lock(first_prompt_id)
                lock_state = set_up_prompt_template_manager.get_lock(first_prompt_id)
                print(str(lock_state) + "  -  Prompt Locked")
                assert lock_state["locked"], self.lock_changed_error_message
            else:
                print(self.nothing_to_lock_message)

    def test_05_e2e_check_auto_locking_mechanism(self, set_up_prompt_template_manager):
        """
        How that mechanism should behave? On UI we are autolocking prompt
        after any interaction with it. In the Python Client we leave it as it is,
        and it is whole depend on user.
        """
        self.test_01_e2e_create_prompt_and_check_values(set_up_prompt_template_manager)
        first_id_element = set_up_prompt_template_manager.list()["ID"][0]

        set_up_prompt_template_manager.unlock(first_id_element)
        lock_state = set_up_prompt_template_manager.get_lock(first_id_element)
        print(lock_state)

        loaded_old_prompt = set_up_prompt_template_manager.load_prompt(first_id_element)
        loaded_old_prompt.name = "new_name"
        set_up_prompt_template_manager.update_prompt(first_id_element, loaded_old_prompt)

        new_first_id_element = set_up_prompt_template_manager.list()["ID"][0]

        lock_state = set_up_prompt_template_manager.get_lock(new_first_id_element)
        print(lock_state)

    def test_06_e2e_create_freeform_prompt_and_check_values(self, set_up_prompt_template_manager):
        input_text = "Bob has a {object}"

        prompt_template = PromptTemplate(name=self.prompt_name,
                                         input_text=input_text,
                                         input_variables=["object"],
                                         model_id=ModelTypes.FLAN_UL2)

        set_up_prompt_template_manager.store_prompt(prompt_template)

        assert prompt_template.name == self.prompt_name, self.check_value_error_message
        assert prompt_template.input_text == input_text, self.check_value_error_message

    def test_07_e2e_deleting_all_prompts_from_list(self, set_up_prompt_template_manager):
        list_of_prompts = set_up_prompt_template_manager.list()

        if len(list_of_prompts) == 0:
            raise Exception(self.prompt_list_is_empty_message)

        for _ in range(len(list_of_prompts)):
            if len(set_up_prompt_template_manager.list()) > 0:
                first_id_element = set_up_prompt_template_manager.list()['ID'][0]
                set_up_prompt_template_manager.delete_prompt(first_id_element, force=True)
                print(first_id_element + " - has been deleted")

                assert first_id_element not in list_of_prompts
            else:
                assert len(set_up_prompt_template_manager.list()) == 0, self.prompt_list_is_not_empty_error_message
