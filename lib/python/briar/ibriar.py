import sys
from prompt_toolkit import prompt
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory


class CLICommands:
    MODE = "MODE"
    COMMAND = "COMMAND"
    ARGS = "ARGS"
    CMD_SYNTAX = [MODE, COMMAND, ARGS]

    DETECT = {
        "detect":
            {
                "run": {"args": ["input", "output"],
                        "kwargs": ["kwarg1", "kwarg2", "asdf", "foo", "bar"]}

            }
    }

    EXTRACT = {
        "extract":
            {
                "run": {"args": ["input", "output"],
                        "kwargs": ["kwarg1", "kwarg2", "asdf", "foo", "bar"]}
            }
    }

    ENROLL = {
        "enroll":
            {
                "run": {"args": ["input", "output"],
                        "kwargs": ["kwarg1", "kwarg2", "asdf", "foo", "bar"]}
            }
    }

    CMD_SCHEMA = {**DETECT, **EXTRACT, **ENROLL}


class BriarCLI:
    _PROMPT_TXT = ">"

    def __init__(self):
        self._base_promppt_text = ">"
        self._prompt_hist_path = "interactive_cli_history.txt"
        self._completer = BriarCLICompleter()

    def _cmd_line(self):
        while True:
            try:
                user_input = prompt(self._PROMPT_TXT,
                                    history=FileHistory(self._prompt_hist_path),
                                    auto_suggest=AutoSuggestFromHistory(),
                                    completer=self._completer)
            except EOFError:
                return
            except KeyboardInterrupt:
                return


class BriarCLICompleter(Completer):
    def __init__(self):
        pass

    def _get_completions(self, document, complete_event, word, suggestions):
        return [Completion(sugg, -len(word))
                for sugg in suggestions
                if sugg.startswith(word)]

    # def _get_cmd_syntax(self, split_cmd):
    #     BASE_CMD = 0
    #     POSITIONAL = 1
    #     KWARG = 2
    #     ARG = 3
    #
    #     if split_cmd[0] in CLICommands.CMD_SCHEMA:
    #         base_cmd = split_cmd[0]
    #
    #     syntax = [BASE_CMD]
    #     expected_next_syntax = [POSITIONAL, KWARG]
    #     for cmd_part in split_cmd[1:]:
    #         if cmd_part in CLICommands.CMD_SCHEMA[base_cmd]:
    #             # is a kwarg
    #             syntax.append(KWARG)
    #             if CLICommands.CMD_SCHEMA[base_cmd][cmd_part] != None:
    #                 syntax.append()
    #
    #         else:
    #             syntax.append(KWARG)

    def _complete_from_schema(self, cmd_to_cmplt, split_cmds, d):

        base_cmd = ""
        for i, cmd in enumerate(split_cmds):
            if i == 0:
                base_cmd = cmd

        outer_dict = None
        inner_dict = d
        section = ""
        for i, cmd in enumerate(split_cmds):
            # skip the args/kwargs level of the schema
            section = cmd
            if i == 0 and "cmds" in inner_dict:
                inner_dict = inner_dict["cmds"]
                continue
            elif i + 1 < len(split_cmds):
                if cmd in inner_dict:
                    if isinstance(inner_dict[cmd], dict):
                        outer_dict = inner_dict
                        inner_dict = inner_dict[cmd]
                else:
                    return []

        def _get_cmd_args(self, word, base_cmd):

            if base_cmd in CLICommands.CMD_SCHEMA:
                arg_dict = CLICommands.CMD_SCHEMA[base_cmd]
                if not word.strip() == "":
                    return [Completion(sugg, -len(word))
                            for sugg in arg_dict.keys()]

                else:
                    return [Completion(sugg, -len(word))
                            for sugg in arg_dict.keys()
                            if sugg.startswith(word)]

        # sys.stdout.write("{}\r\n".rjust(25).format(inner_dict)[:125])
        print("\n", inner_dict)
        return [Completion(sugg, -len(txt))
                for sugg in inner_dict.keys()
                if sugg.startswith(txt)]

        return [[Completion(sugg, -len(in_txt[-1]))
                 for sugg in d.keys()]]

    def _complete_base_cmd(self, word_to_complate):
        return [Completion(sugg, -len(word_to_complate))
                for sugg in CLICommands.CMD_SCHEMA
                if sugg.startswith(word_to_complate)]

    def _suggest_cmds(self, base_cmd):
        if base_cmd in CLICommands.CMD_SCHEMA:
            return [Completion(sugg)
                    for sugg in CLICommands.CMD_SCHEMA[base_cmd]]
        else:
            return []

    def _complete_cmds(self, word_to_complate, base_cmd):
        if base_cmd in CLICommands.CMD_SCHEMA:
            return [Completion(sugg, -len(word_to_complate))
                    for sugg in CLICommands.CMD_SCHEMA[base_cmd]
                    if sugg.startswith(word_to_complate) or word_to_complate == ""]
        else:
            return []

    def _suggest_kwargs(self, base_cmd, sub_cmd):
        if base_cmd in CLICommands.CMD_SCHEMA \
                and sub_cmd in CLICommands.CMD_SCHEMA[base_cmd]:
            return [Completion(sugg)
                    for sugg
                    in CLICommands.CMD_SCHEMA[base_cmd][sub_cmd]["kwargs"]]
        else:
            return []

    def _complete_kwargs(self, word_to_complete, base_cmd, sub_cmd):
        if base_cmd in CLICommands.CMD_SCHEMA \
                and sub_cmd in CLICommands.CMD_SCHEMA[base_cmd]:
            return [Completion(sugg, -len(word_to_complete))
                    for sugg in CLICommands.CMD_SCHEMA[base_cmd][sub_cmd]["kwargs"]
                    if sugg.startswith(word_to_complete) or word_to_complete == ""]
        return []

    def get_completions(self, document, complete_event):
        text = document.text
        words = text.split()
        base_cmd = words[0]
        num_words = len(words)

        is_space = text.isspace()
        ends_in_space = text[-1].isspace()

        if num_words == 1 and not is_space:
            if not ends_in_space:
                completions = self._complete_base_cmd(base_cmd)
            else:
                completions = self._suggest_cmds(base_cmd)

        elif num_words == 1 and ends_in_space:
            completions = self._suggest_cmds(base_cmd)

        elif num_words == 2 and not ends_in_space:
            completions = self._complete_cmds(words[-1], base_cmd)

        elif num_words >= 2 and ends_in_space:
            completions = self._suggest_kwargs(base_cmd, words[1])

        elif num_words >= 2:
            completions = self._complete_kwargs(words[-1], base_cmd, words[1])

        else:
            completions = []

        return completions


DEFAULT_ARGS = {"in_path": str, "out_path": str, "": "", }

if __name__ == "__main__":
    bcl = BriarCLI()
    bcl._cmd_line()
