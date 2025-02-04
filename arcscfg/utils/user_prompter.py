from typing import Dict, List, Optional


class UserPrompter:
    def __init__(self, assume_yes: bool = False):
        """
        Initialize the UserPrompter.

        Args:
            assume_yes (bool): If True, automatically assume 'Yes' for all prompts.
        """
        self.assume_yes = assume_yes

    def prompt_yes_no(self, message: str, default: bool = False) -> bool:
        """
        Prompt the user with a yes/no question.

        Args:
            message (str): The question to present to the user.
            default (bool): The default value if the user provides no input.

        Returns:
            bool: True for 'Yes', False for 'No'.
        """
        if self.assume_yes:
            return True

        default_str = "Y/n" if default else "y/N"
        while True:
            choice = input(f"{message} [{default_str}]: ").strip().lower()
            if not choice:
                return default
            if choice in ["y", "yes"]:
                return True
            elif choice in ["n", "no"]:
                return False
            else:
                print("Please respond with 'y' or 'n'.")

    def prompt_selection(
        self, message: str, options: List[str], default: Optional[int] = None
    ) -> int:
        """
        Prompt the user to select an option from a list.

        Args:
            message (str): The prompt message.
            options (List[str]): A list of option strings.
            default (Optional[int]): The default option index (1-based).

        Returns:
            int: The index of the selected option (0-based).
        """
        if self.assume_yes:
            if default is not None:
                return default - 1
            else:
                return 0  # Default to first option

        print(message)
        for idx, option in enumerate(options, start=1):
            print(f"{idx}: {option}")

        if default is not None:
            prompt = f"Select an option [default: {default}]: "
        else:
            prompt = "Select an option: "

        while True:
            choice = input(prompt).strip()
            if not choice:
                if default is not None:
                    return default - 1
                else:
                    print("Please enter a number corresponding to the options.")
                    continue
            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(options):
                    return idx - 1
            print("Invalid selection. Please enter a valid number.")

    def prompt_input(
        self,
        message: str,
        default: Optional[str] = None,
        options: Optional[List[str]] = None,
    ) -> str:
        """
        Prompt the user for arbitrary input with optional partial matching.

        If options are provided, the user can input full or partial matches
        corresponding to the start of any option. The prompt will display
        short-form hints using unique starting characters.

        Args:
            message (str): The prompt message.
            default (Optional[str]): The default input if the user provides no input.
            options (Optional[List[str]]): A list of option strings for matching.

        Returns:
            str: The user's input or the default value.
        """
        if self.assume_yes and default is not None:
            return default

        if options:
            # Generate short-form hints
            shorthand_map = self._generate_shorthand_map(options)
            options_display = self._format_options_display(options, shorthand_map)
            prompt_message = f"{message} {options_display}: "
        else:
            if default:
                prompt_message = f"{message} [default: {default}]: "
            else:
                prompt_message = f"{message}: "

        while True:
            response = input(prompt_message).strip().lower()
            if not response:
                if default is not None:
                    return default
                else:
                    print("Input cannot be empty.")
                    continue

            if options:
                matched_option = self._match_option(response, options)
                if matched_option:
                    return matched_option

                print("Invalid input. Please choose a valid option.")
                continue

            return response

    def _generate_shorthand_map(self, options: List[str]) -> Dict[str, str]:
        """
        Generates a mapping from shorthand character to option.

        Each option's shorthand is its first unique character.

        Args:
            options (List[str]): List of option strings.

        Returns:
            Dict[str, str]: Mapping of shorthand to option.
        """
        shorthand_map = {}
        used_chars = set()

        for option in options:
            first_char = option[0].lower()
            if first_char not in used_chars:
                shorthand_map[first_char] = option
                used_chars.add(first_char)
            else:
                # Find the next unique character
                for char in option.lower():
                    if char not in used_chars:
                        shorthand_map[char] = option
                        used_chars.add(char)
                        break
                else:
                    # If no unique character, assign numeric shorthand
                    index = len(shorthand_map) + 1
                    shorthand_map[str(index)] = option

        return shorthand_map

    def _format_options_display(
        self, options: List[str], shorthand_map: Dict[str, str]
    ) -> str:
        """
        Formats the options with shorthand hints.

        Args:
            options (List[str]): List of option strings.
            shorthand_map (Dict[str, str]): Mapping of shorthand to option.

        Returns:
            str: Formatted string for prompt display.
        """
        display_parts = []
        for option in options:
            shorthand = None
            for key, value in shorthand_map.items():
                if value == option:
                    shorthand = key
                    break
            if shorthand:
                display_part = f"({shorthand}){option[len(shorthand):]}"
            else:
                display_part = option
            display_parts.append(display_part)
        return f"[{'/'.join(display_parts)}]"

    def _match_option(self, user_input: str, options: List[str]) -> Optional[str]:
        """
        Matches the user input against the list of options based on partial matching.

        Args:
            user_input (str): The input provided by the user.
            options (List[str]): The list of valid options.

        Returns:
            Optional[str]: The matched option or None if no match.
        """
        matches = [
            option for option in options if option.lower().startswith(user_input)
        ]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            print(
                f"Ambiguous input '{user_input}'. Possible matches: {', '.join(matches)}"
            )
            return None
        else:
            return None
